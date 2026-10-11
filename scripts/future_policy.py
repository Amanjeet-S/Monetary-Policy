"""Declared German production responses to the retained future-policy proxy."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import norm

from ar_inference import ar_inverse_set
from local_projections import ols,calendar_hac

ROOT=Path(__file__).resolve().parents[1]
SPECIFICATION_SHA256='80eee7aabb4ef0103fa63ed1fe4d48bac5fe95b3beaab2906067760015971d88'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def month_number(s):
    y,m=map(int,s.split('-'));return y*12+m-1

def month_name(n):
    y,m=divmod(n,12);return f'{y:04d}-{m+1:02d}'

def panel_data(root):
    with (root/'data/processed/future_policy_panel.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    return {month_number(row['month']):{k:float(v) if v else np.nan for k,v in row.items() if k!='month'} for row in rows}

def design(panel,h=12,p=2):
    dates=np.arange(month_number('2005-01'),month_number('2016-01')+1,dtype=np.int64)
    at=lambda key,t:panel.get(int(t),{}).get(key,np.nan)
    def growth(t):return 100*np.log(at('manufacturing',t)/at('manufacturing',t-1))
    def inflation(t):return 100*np.log(at('hicp',t)/at('hicp',t-12))
    w=[];responses=[];financial=[];instrument=[]
    for t in dates:
        row=[1.,at('target',t)/.10,at('delphic',t)/.10]
        for lag in range(1,p+1):
            q=t-lag
            row += [growth(q),inflation(q),at('target',q)/.10,at('delphic',q)/.10,
                    at('odyssean',q)/.10,at('yield_1y_change_pp',q)/.10,at('yield_3m_change_pp',q)/.10]
        w.append(row);instrument.append(at('odyssean',t)/.10)
        financial.append([at('yield_1y_change_pp',t)/.10,at('yield_3m_change_pp',t)/.10])
        if h<0:
            endpoints=(t-1,t-13)
        else:endpoints=(t+h,t-1)
        future,past=endpoints
        m=100*np.log(at('manufacturing',future)/at('manufacturing',past))
        i=100*np.log(at('industrial',future)/at('industrial',past))
        d=100*np.log(at('durable',future)/at('durable',past))
        n=100*np.log(at('nondurable',future)/at('nondurable',past))
        responses.append([m,i,d-n])
    w=np.array(w);z=np.array(instrument);financial=np.array(financial);responses=np.array(responses)
    if not all(np.isfinite(a).all() for a in [w,z,financial,responses]):raise ValueError('Declared common sample has missing data')
    return dates,w,z,financial,responses

BENCHMARKS={'one_year':np.array([1.,0.]),'slope_1y_3m':np.array([1.,-1.]),
            'three_month':np.array([0.,1.]),'forward_3m_1y':np.array([4/3,-1/3])}
OUTCOMES=['manufacturing','industrial','durability_contrast']

def encode_set(result):
    record={'kind':result.kind,'intervals':[],
            'quadratic_coefficients':[float(v) for v in result.coefficients]}
    for item in result.intervals:
        record['intervals'].append({'lower':None if item.lower is None else float(item.lower),
                                    'upper':None if item.upper is None else float(item.upper)})
    if result.notes:record['regularity_diagnostics']=list(result.notes)
    record['contains_zero']=result.contains(0)
    return record

def fit_case(panel,h=12,p=2,bandwidth=None):
    dates,w,z,financial,responses=design(panel,h,p)
    x=np.column_stack([z,w]);n,k=x.shape
    if n!=133 or k!=4+7*p:raise ValueError('Declared dimensions differ')
    response_matrix=np.column_stack([responses,financial])
    coefficients=[];scores=[];residuals=[]
    for column in response_matrix.T:
        b,e,loading,leverage=ols(x,column)
        coefficients.append(float(b[0]));scores.append(loading[:,0]*e);residuals.append(e)
    coefficients=np.array(coefficients);scores=np.column_stack(scores)
    base=int(np.ceil(4*(n/100)**(2/9)))
    L=(11 if h<0 else h)+base if bandwidth is None else bandwidth
    V=calendar_hac(scores,dates,L,n/(n-k))
    if min(np.linalg.eigvalsh(V))<=0:raise ValueError('Nondegenerate joint score covariance required')
    family_critical=float(norm.ppf(1-.05/8)**2)
    individual_critical=float(norm.ppf(.975)**2)
    outcomes={}
    for j,name in enumerate(OUTCOMES):
        reduced=coefficients[j];vr=V[j,j]
        p_reduced=float(2*norm.sf(abs(reduced)/np.sqrt(vr)))
        benchmarks={}
        for key,weights in BENCHMARKS.items():
            first=float(weights@coefficients[3:]);vf=float(weights@V[3:,3:]@weights);cross=float(V[j,3:]@weights)
            family=ar_inverse_set(reduced,first,vr,vf,cross,critical_square=family_critical)
            individual=ar_inverse_set(reduced,first,vr,vf,cross,critical_square=individual_critical)
            point=float(reduced/first) if first else None
            delta_se=None
            if first:
                gradient=np.array([1/first,-reduced/first**2]);joint=np.array([[vr,cross],[cross,vf]])
                delta_se=float(np.sqrt(gradient@joint@gradient))
                if not family.contains(point):raise ValueError('Estimated ratio excluded by its AR set')
            # The same instrument and conditioning set make every zero-response AR test identical.
            if family.contains(0)!=(p_reduced>=.05/4):raise ValueError('Zero AR equivalence failed')
            benchmarks[key]={'first_stage':first,'first_stage_variance':vf,'reduced_first_covariance':cross,
                'ratio_point':point,'diagnostic_delta_se':delta_se,'family_AR95':encode_set(family),'individual_AR95':encode_set(individual)}
        outcomes[name]={'reduced_form':float(reduced),'reduced_form_se':float(np.sqrt(vr)),
                         'reduced_form_p':p_reduced,'benchmarks':benchmarks}
    primary_first=coefficients[3];primary_se=np.sqrt(V[3,3])
    reduced_w,_,_,_=ols(w,financial[:,0]);residual_x=financial[:,0]-w@reduced_w
    residual_z=z-w@ols(w,z)[0]
    partial_r2=float(np.corrcoef(residual_x,residual_z)[0,1]**2)
    return {'horizon':h,'lags':p,'n':n,'columns':k,'residual_df':n-k,'bandwidth':L,
        'first':'2005-01','last':'2016-01','coefficient_order':OUTCOMES+['yield_1y','yield_3m'],
        'coefficients':coefficients.tolist(),'joint_covariance':V.tolist(),
        'family_alpha_per_normalisation':.05/4,'family_critical_square':family_critical,
        'maximum_leverage':float(max(leverage)),
        'first_stage_1y':{'coefficient':float(primary_first),'se':float(primary_se),'hac_t_squared':float((primary_first/primary_se)**2),'partial_r_squared':partial_r2},
        'outcomes':outcomes}

def run(root,write=True):
    spec=root/'docs/future_policy_specification.json'
    if digest(spec)!=SPECIFICATION_SHA256:raise ValueError('Recorded specification changed')
    declaration=json.loads(spec.read_text())
    for name,wanted in declaration['original_evidence_preservation'].items():
        if digest(root/name)!=wanted:raise ValueError('Original evidence changed')
    if digest(root/declaration['snapshot']/'manifest.json')!=declaration['snapshot_manifest_sha256']:
        raise ValueError('Declared source manifest changed')
    panel=panel_data(root);primary=fit_case(panel);base=primary['bandwidth']-12
    profiles=[fit_case(panel,h) for h in declaration['horizon_profile']]
    sensitivity=[{'case':'three_lags','result':fit_case(panel,p=3)},
        {'case':'short_bandwidth','result':fit_case(panel,bandwidth=12+int(np.ceil(base/2)))},
        {'case':'long_bandwidth','result':fit_case(panel,bandwidth=12+2*base)}]
    placebo=fit_case(panel,h=-1)
    dates,w,z,financial,responses=design(panel)
    deletions=[]
    for index in range(len(dates)):
        keep=np.arange(len(dates))!=index;x=np.column_stack([z[keep],w[keep]])
        r=ols(x,responses[keep,0])[0][0];f=ols(x,financial[keep,0])[0][0]
        deletions.append({'deleted_origin':month_name(int(dates[index])),
                          'reduced_form':float(r),'first_stage':float(f),
                          'ratio':float(r/f) if f else None})
    report={'status':'declared_empirical_redesign','author':'Amanjeet Singh',
        'specification_sha256':digest(spec),'panel_sha256':digest(root/'data/processed/future_policy_panel.csv'),
        'primary':primary,'profiles':profiles,'sensitivity':sensitivity,'predetermined':placebo,
        'single_origin_deletions':deletions,
        'interpretation':'Conditional proxy-shock response scaled to its financial impact; not a causal intervention on sovereign yields or an isolated QE-free guidance effect',
        'coverage':'For each outcome and design, Bonferroni protects the four pre-enumerated financial normalisations; no simultaneous claim across outcomes, horizons or designs'}
    if write:(root/'results/future_policy_results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

def compare_values(actual,expected,path='root'):
    if isinstance(actual,dict):
        if set(actual)!=set(expected):raise ValueError(f'Fields differ:{path}')
        return sum(compare_values(actual[k],expected[k],path+'.'+k) for k in actual)
    if isinstance(actual,list):
        if len(actual)!=len(expected):raise ValueError(f'Lengths differ:{path}')
        return sum(compare_values(a,b,path+f'.{i}') for i,(a,b) in enumerate(zip(actual,expected)))
    if isinstance(actual,(float,int)) and not isinstance(actual,bool):
        if not np.isclose(actual,expected,rtol=1e-9,atol=1e-10):raise ValueError(f'Numeric difference:{path}')
        return 1
    if actual!=expected:raise ValueError(f'Value differs:{path}')
    return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    report=run(args.root,write=not args.check)
    if args.check:
        count=compare_values(report,json.loads((args.root/'results/future_policy_results.json').read_text()))
        print(json.dumps({'retained_results_verified':True,'numeric_comparisons':count}))
    else:
        print(json.dumps({'first_stage':report['primary']['first_stage_1y'],'primary_response':report['primary']['outcomes']['manufacturing']['benchmarks']['one_year'],
            'manufacturing_reduced_form_p':report['primary']['outcomes']['manufacturing']['reduced_form_p']},indent=2))
