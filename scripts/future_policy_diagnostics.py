"""Bounded post-estimation state, leverage and horizon-family checks."""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np
from scipy.stats import norm

from future_policy import panel_data,design,BENCHMARKS,OUTCOMES,encode_set,compare_values
from ar_inference import ar_inverse_set
from local_projections import ols,calendar_hac

ROOT=Path(__file__).resolve().parents[1]

def assess(panel,h,kind):
    dates,w,z,financial,responses=design(panel,h)
    if kind=='annual_state':
        annual=np.array([[100*np.log(panel[int(t-lag)]['manufacturing']/panel[int(t-lag-12)]['manufacturing'])
                          for lag in [1,2]] for t in dates])
        w=np.column_stack([w,annual])
    x=np.column_stack([z,w]);n,k=x.shape
    matrix=np.column_stack([responses,financial]);coefs=[];scores=[]
    for y in matrix.T:
        b,e,loading,leverage=ols(x,y)
        coefs.append(float(b[0]))
        if kind=='leverage':e=e/(1-leverage)
        scores.append(loading[:,0]*e)
    coefs=np.array(coefs);L=h+int(np.ceil(4*(n/100)**(2/9)))
    V=calendar_hac(np.column_stack(scores),dates,L,n/(n-k))
    critical=float(norm.ppf(1-.05/8)**2)
    outcomes={}
    for j,name in enumerate(OUTCOMES):
        benchmarks={}
        for key,weights in BENCHMARKS.items():
            f=float(weights@coefs[3:]);vf=float(weights@V[3:,3:]@weights);cross=float(V[j,3:]@weights)
            confidence=ar_inverse_set(coefs[j],f,V[j,j],vf,cross,critical_square=critical)
            benchmarks[key]={'point':float(coefs[j]/f),'family_AR95':encode_set(confidence)}
        outcomes[name]={'reduced_form':float(coefs[j]),'reduced_form_se':float(np.sqrt(V[j,j])),
            'reduced_form_p':float(2*norm.sf(abs(coefs[j])/np.sqrt(V[j,j]))),'benchmarks':benchmarks}
    return {'kind':kind,'horizon':h,'columns':k,'n':n,'bandwidth':L,
            'maximum_leverage':float(max(leverage)),'coefficients':coefs.tolist(),
            'joint_covariance':V.tolist(),'first_stage_hac_t_squared':float(coefs[3]**2/V[3,3]),'outcomes':outcomes}

def run(write=True):
    spec=ROOT/'docs/future_policy_diagnostic_specification.json'
    d=json.loads(spec.read_text());panel=panel_data(ROOT)
    primary=json.loads((ROOT/'results/future_policy_results.json').read_text())
    checks=[assess(panel,h,kind) for kind in ['annual_state','leverage'] for h in [0,6,12,18,24]]
    profile=[];critical=float(norm.ppf(1-.05/40)**2)
    for case in primary['profiles']:
        y=case['outcomes']['manufacturing'];benchmarks={}
        for key,b in y['benchmarks'].items():
            confidence=ar_inverse_set(y['reduced_form'],b['first_stage'],y['reduced_form_se']**2,
                b['first_stage_variance'],b['reduced_first_covariance'],critical_square=critical)
            benchmarks[key]=encode_set(confidence)
        profile.append({'horizon':case['horizon'],'benchmarks':benchmarks})
    report={'status':'post_estimation_diagnostics','author':'Amanjeet Singh',
        'specification_sha256':hashlib.sha256(spec.read_bytes()).hexdigest(),
        'primary_results_sha256':hashlib.sha256((ROOT/'results/future_policy_results.json').read_bytes()).hexdigest(),
        'checks':checks,'manufacturing_profile_family_AR95':profile,
        'profile_family_critical_square':critical,
        'scope':'Annual-state and leverage checks are supplementary; initial primary retained. Twenty-response family is primary manufacturing profile over five declared horizons and four financial normalisations. No family claim across diagnostic designs or other outcomes.'}
    if write:(ROOT/'results/future_policy_diagnostics.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    for check in checks:
        if check['horizon'] in [12,18,24]:
            y=check['outcomes']['manufacturing'];print(check['kind'],check['horizon'],
                'point',round(y['benchmarks']['one_year']['point'],4),'p',round(y['reduced_form_p'],6),
                'AR',y['benchmarks']['one_year']['family_AR95']['kind'],y['benchmarks']['one_year']['family_AR95']['intervals'],
                'first_stage',round(check['first_stage_hac_t_squared'],3))
    for case in profile:print('simultaneous_profile',case['horizon'],case['benchmarks']['one_year']['intervals'])
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=run(write=not args.check)
    if args.check:
        count=compare_values(result,json.loads((ROOT/'results/future_policy_diagnostics.json').read_text()))
        print(json.dumps({'retained_diagnostics_verified':True,'numeric_comparisons':count}))
