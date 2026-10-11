"""Bounded recorded follow-up of cumulative US purchase estimates."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from us_purchases import ROOT,build_design,fit_case,clustered_hac,interval
from local_projections import ols
from future_policy import compare_values

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(root,check=False):
    p=root/'docs/us_purchase_followup_specification.json';spec=json.loads(p.read_text())
    for key,name in [('initial_results_sha256','results/us_purchase_results.json'),('primary_specification_sha256','docs/us_purchase_specification.json')]:
        if digest(root/name)!=spec[key]:raise ValueError('Retained preceding evidence changed')
    cases={}
    for name,lags,adj in [('outside_episode_leverage_adjusted',12,True),('outside_episode_twenty_four_policy_lags',24,False)]:
        fit=fit_case(root,policy_lags=lags,leverage_adjusted=adj,exclude_reserves=True)
        c=fit['windows']['durable_full36']['pointwise95']
        cases[name]={k:fit[k] for k in ['n','columns','policy_lags','bandwidth','maximum_leverage']}
        cases[name].update({'pointwise95':c,'diagnostic_family95':interval(c['estimate'],c['se']**2,.05/3),
                           'financial':fit['financial']})
    dates,w,z,raw,y,event_dates=build_design(root);x=np.column_stack([z,w]);n,k=x.shape
    outcome=y[:,:36].sum(axis=1)/100
    b,e,load,hat=ols(x,outcome)
    kept=np.array([not '1979-10'<=s[:7]<='1982-10' for s in event_dates])
    ns=int(kept.sum());bs,es,ls,hs=ols(x[kept],outcome[kept])
    joint=np.zeros((n,2));joint[:,0]=load[:,0]*e*np.sqrt(n/(n-k))
    joint[kept,1]=ls[:,0]*es*np.sqrt(ns/(ns-k))
    V=clustered_hac(joint,dates,41,1.);v=np.array([-1.,1.]);diff=float(bs[0]-b[0])
    original=json.loads((root/'results/us_purchase_results.json').read_text())
    expected=[original['primary']['windows']['durable_full36']['pointwise95']['se']**2,
              original['sensitivity']['exclude_reserves_targeting']['windows']['durable_full36']['pointwise95']['se']**2]
    if not np.allclose(np.diag(V),expected,rtol=1e-10,atol=1e-12):raise ValueError('Embedded score marginals differ')
    contrast={'subset_minus_primary':diff,'joint_covariance_order':['full','outside_episode'],
              'joint_covariance':V.tolist(),'pointwise95':interval(diff,v@V@v),
              'diagnostic_family95':interval(diff,v@V@v,.05/3),
              'source_event_count':n,'subset_event_count':ns}
    report={'author':'Amanjeet Singh','status':'Recorded informed diagnostic follow-up',
            'specification_sha256':digest(p),'preceding_results_sha256':spec['initial_results_sha256'],
            'crossed_checks':cases,'sample_contrast':contrast,
            'interpretation':'Secondary origin exclusions do not purify overlapping outcome or history periods; the full-sample primary remains unchanged'}
    out=root/'results/us_purchase_diagnostics.json'
    if check:return {'retained_diagnostics_verified':True,'numeric_comparisons':compare_values(report,json.loads(out.read_text()))}
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--check',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.root,a.check),indent=2))
