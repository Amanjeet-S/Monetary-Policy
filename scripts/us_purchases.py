"""Declared event projections for US cumulative household purchases."""
from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path
import numpy as np
from scipy.stats import norm
from linear_inference import ols, calendar_hac, verify_historical_evidence
from ar_inference import ar_inverse_set

ROOT=Path(__file__).resolve().parents[1]
CATEGORIES=['durable','nondurable','services']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def month_number(s):
    y,m=map(int,s[:7].split('-'));return y*12+m-1
def inputs(root):
    with (root/'data/processed/us_purchase_monthly.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    panel={month_number(r['month']):{k:float(v) if v else np.nan for k,v in r.items() if k!='month'} for r in rows}
    with (root/'data/processed/us_policy_events.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    events=[{k:v if k in ('date','month') else float(v) for k,v in r.items()} for r in rows]
    return panel,events
def build_design(root,policy_lags=12,exclude_reserves=False,start=1):
    spec=json.loads((root/'docs/us_purchase_specification.json').read_text());panel,source=inputs(root)
    events=[r for r in source if spec['sample']['first_event']<=r['date']<=spec['sample']['last_event']]
    if len(events)!=238:raise ValueError('Declared common event mask changed')
    if exclude_reserves:events=[r for r in events if not '1979-10'<=r['month']<='1982-10']
    at=lambda k,t:panel.get(int(t),{}).get(k,np.nan)
    histories=['durable','nondurable','services','real_disposable_income']
    w=[];y=[];z=[];raw=[];dates=[]
    for r in events:
        t=month_number(r['month']);dates.append(t)
        states=[100*np.log(at(k,t-1)/at(k,t-2)) for k in histories]
        states += [100*np.log(at(k,t-1)/at(k,t-13)) for k in histories]
        states += [100*np.log(at('pce_price',t-1)/at('pce_price',t-13)),at('funds_rate',t-1)]
        states += [at('raw_monthly_intention',t-j) for j in range(1,policy_lags+1)]
        w.append([r[k] for k in spec['conditioning']['source_forecasts']]+states)
        z.append(r['innovation']/.25);raw.append(r['raw_intention']/.25)
        outcomes=[100*(at(k,t+j)/at(k,t-1)-1) for k in CATEGORIES for j in range(start,start+36)]
        outcomes += [r['financial_change']]
        outcomes += [sum(at('durable',t-j)/at('durable',t-13) for j in range(1,13))-12]
        y.append(outcomes)
    w=np.array(w);y=np.array(y);z=np.array(z);raw=np.array(raw);dates=np.array(dates,dtype=np.int64)
    if not all(np.isfinite(a).all() for a in [w,y,z,raw]):raise ValueError('Unobserved required input; no imputation or silent deletion')
    if w.shape[1]!=29+policy_lags:raise ValueError('Declared conditioning count differs')
    return dates,w,z,raw,y,[r['date'] for r in events]
def clustered_hac(scores,dates,L,correction):
    distinct,groups=np.unique(dates,return_inverse=True)
    grouped=np.zeros((len(distinct),scores.shape[1]));np.add.at(grouped,groups,scores)
    return calendar_hac(grouped,distinct,L,correction)
def interval(value,variance,alpha=.05):
    se=float(np.sqrt(max(variance,0.)));q=norm.ppf(1-alpha/2)
    return {'estimate':float(value),'se':se,'lower':float(value-q*se),'upper':float(value+q*se),
            'p_two_sided':float(2*norm.sf(abs(value)/se)) if se else None}
def encode_set(s):
    return {'kind':s.kind,'intervals':[{'lower':None if v.lower is None else float(v.lower),
                                      'upper':None if v.upper is None else float(v.upper)} for v in s.intervals],
            'contains_zero':s.contains(0),'quadratic_coefficients':[float(v) for v in s.coefficients]}
def fit_case(root,policy_lags=12,L=41,leverage_adjusted=False,exclude_reserves=False,start=1):
    dates,w,z,raw,y,event_dates=build_design(root,policy_lags,exclude_reserves,start)
    x=np.column_stack([z,w]);n,k=x.shape
    b,e,loading,leverage=ols(x,y);coeff=b[0];scores=loading[:,0,None]*e
    if leverage_adjusted:scores=scores/(1-leverage[:,None])
    V=clustered_hac(scores,dates,L,n/(n-k))
    if min(np.diag(V))<=0:raise ValueError('Degenerate coefficient covariance')
    # Shared event rows and controls make these finite sums exact linear contrasts.
    contrasts=[];labels=[]
    for category,name in enumerate(CATEGORIES):
        for window,a,bound in [('first12',0,12),('later24',12,36),('full36',0,36)]:
            v=np.zeros(y.shape[1]);v[category*36+a:category*36+bound]=.01
            contrasts.append(v);labels.append(name+'_'+window)
    A=np.array(contrasts);cb=A@coeff;cv=A@V@A.T;cs=scores@A.T
    windows={label:{'pointwise95':interval(cb[j],cv[j,j]),'endpoint_family95':interval(cb[j],cv[j,j],.05/9)} for j,label in enumerate(labels)}
    fin=coeff[108];finv=V[108,108];primary_vector=A[2]
    cross=float(primary_vector@V[:,108]);c=cb[2];v=cv[2,2]
    ar=ar_inverse_set(c,fin/.25,v,finv/.25**2,cross/.25,critical_square=float(norm.ppf(.975)**2))
    if ar.contains(0)!=(windows['durable_full36']['pointwise95']['p_two_sided']>=.05):raise ValueError('AR zero equivalence failed')
    point=c*.25/fin if fin else None
    if point is not None and not ar.contains(point):raise ValueError('Ratio estimate excluded by its inverse set')
    profiles=[]
    for h in range(1,37):
        row={'months':h}
        for j,name in enumerate(CATEGORIES):
            v=np.zeros(y.shape[1]);v[j*36:j*36+h]=.01
            row[name]={'cumulative_pointwise95':interval(v@coeff,v@V@v),
                       'cumulative_profile_family95':interval(v@coeff,v@V@v,.05/36),
                       'flow_pointwise95':interval(coeff[j*36+h-1],V[j*36+h-1,j*36+h-1])}
        profiles.append(row)
    # Current source-purge coefficients cannot alter the matched partial regression.
    raw_b,raw_e,raw_loading,raw_hat=ols(np.column_stack([raw,w]),y)
    fwl={'coefficient_max_abs_error':float(np.max(abs(b[0]-raw_b[0]))),
         'residual_max_abs_error':float(np.max(abs(e-raw_e))),
         'coefficient_loading_max_abs_error':float(np.max(abs(loading[:,0]-raw_loading[:,0]))),
         'leverage_max_abs_error':float(np.max(abs(leverage-raw_hat)))}
    if max(fwl.values())>1e-8:raise ValueError('Source-purge invariance failed')
    identities={'coefficient_max_abs_error':float(max(abs(cb[3*j+2]-cb[3*j]-cb[3*j+1]) for j in range(3))),
                'score_max_abs_error':float(max(np.max(abs(cs[:,3*j+2]-cs[:,3*j]-cs[:,3*j+1])) for j in range(3)))}
    # Full36 category contrasts use their common covariance, not unrelated marginal intervals.
    comparisons={}
    for name,j in [('durable_minus_nondurable',5),('durable_minus_services',8)]:
        v=np.zeros(9);v[2]=1;v[j]=-1
        comparisons[name]=interval(v@cb,v@cv@v,.05/2)
    return {'n':n,'distinct_event_months':len(np.unique(dates)),'calendar_span_months':int(dates[-1]-dates[0]+1),
            'first_event':event_dates[0],'last_event':event_dates[-1],'columns':k,'residual_df':n-k,
            'policy_lags':policy_lags,'bandwidth':L,'leverage_adjusted':leverage_adjusted,
            'outcome_start_offset':start,'maximum_leverage':float(max(leverage)),
            'scaled_design_condition_number':float(np.linalg.cond(x/np.linalg.norm(x,axis=0))),
            'windows':windows,'window_order':labels,'window_covariance':cv.tolist(),
            'category_comparisons_family95':comparisons,'profiles':profiles,
            'financial':{'rate_response_pp':interval(fin,finv),'hac_t_squared':float(fin**2/finv),
                         'durable36_covariance':cross,'rate_normalised_ratio_per25bp':float(point) if point is not None else None,
                         'rate_normalised_AR95':encode_set(ar)},
            'predetermined_durable12':interval(coeff[109],V[109,109]),
            'purge_FWL_invariance':fwl,'window_identities':identities}
def run(root,check=False):
    spec=json.loads((root/'docs/us_purchase_specification.json').read_text())
    verify_historical_evidence(root,spec['original_evidence_preservation'])
    primary=fit_case(root)
    sensitivity={
       'six_policy_lags':fit_case(root,policy_lags=6),
       'twenty_four_policy_lags':fit_case(root,policy_lags=24),
       'short_bandwidth':fit_case(root,L=35),
       'long_bandwidth':fit_case(root,L=47),
       'leverage_adjusted_HAC':fit_case(root,leverage_adjusted=True),
       'exclude_reserves_targeting':fit_case(root,exclude_reserves=True),
       'event_month_start':fit_case(root,start=0)}
    dates,w,z,raw,y,event_dates=build_design(root);x=np.column_stack([z,w])
    b,e,loading,hat=ols(x,y[:,0:36].sum(axis=1)/100)
    deletions=[]
    for i,date in enumerate(event_dates):
        estim=b[0]-loading[i,0]*e[i]/(1-hat[i]) if hat[i]<1-1e-10 else None
        deletions.append({'deleted_event':date,'durable36_estimate':float(estim) if estim is not None else None})
    report={'author':'Amanjeet Singh','status':'Prospectively specified US household-purchase study',
            'specification_sha256':digest(root/'docs/us_purchase_specification.json'),
            'primary':primary,'sensitivity':sensitivity,'single_event_deletions':deletions,
            'interpretation':'Responses to forecast-controlled intended-policy innovations, conditional on source information sufficiency and dynamic restrictions; a financial ratio does not identify intervention on the observed rate'}
    path=root/'results/us_purchase_results.json'
    if check:
        from linear_inference import compare_values
        return {'retained_results_verified':True,'numeric_comparisons':compare_values(report,json.loads(path.read_text()))}
    path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return {'primary':primary['windows']['durable_full36'],'financial':primary['financial'],
            'sensitivity':{key:v['windows']['durable_full36']['pointwise95'] for key,v in sensitivity.items()}}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--check',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.root,a.check),indent=2))
