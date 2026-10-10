"""Compare independently reconstructed base-R and Python selected estimates."""
import argparse
import csv
import json
from pathlib import Path
import subprocess

import numpy as np

CASES={'primary_h12':'primary','lag6_h12':'six_lags','poor_man_h12':'poor_man',
       'pre_covid_h12':'pre_pandemic','common_path_h0':'path_00',
       'common_path_h12':'path_12','common_path_h24':'path_24',
       'primary_short_h12':'short_bandwidth','primary_long_h12':'long_bandwidth'}
FIELDS={'n':'n','p':'lags','h':'horizon','k_F':'full_rank','L':'bandwidth',
        'w':'weight','se_w':'weight_se','cov_beta_m_delta':'covariance_beta_m_delta',
        'cov_w_theta':'covariance_weight_theta','product_gap_lo':'delta_product_low',
        'product_gap_hi':'delta_product_high','beta_D':'beta_durable',
        'beta_N':'beta_nondurable','se_beta_D':'beta_durable_se',
        'se_beta_N':'beta_nondurable_se','cov_beta_D_beta_N':'covariance_sectors',
        'se_relative_from_sector_cov':'beta_m_se'}
for field in ['beta_m','beta_c','gamma','theta','delta']:
    FIELDS.update({field:field,'se_'+field:field+'_se',field+'_lo':field+'_low',field+'_hi':field+'_high'})
FIELDS.update({'w_lo':'weight_low','w_hi':'weight_high'})


def compare(python_csv: Path, r_csv: Path) -> dict:
    with python_csv.open(newline='') as f:
        python_rows={r['case']:r for r in csv.DictReader(f)}
    with r_csv.open(newline='') as f:
        r_rows={r['case']:r for r in csv.DictReader(f)}
    if set(r_rows)!=set(CASES):
        raise ValueError('Independent R cases differ from declared selected checks')
    differences=[]
    for r_case,p_case in CASES.items():
        rr,pr=r_rows[r_case],python_rows[p_case]
        if any(rr[field]!=pr[field] for field in ['first','last']):
            raise ValueError('Independent sample boundaries disagree')
        for r_field,p_field in FIELDS.items():
            actual,expected=float(rr[r_field]),float(pr[p_field])
            if not np.isfinite([actual,expected]).all() or not np.isclose(actual,expected,atol=1e-8,rtol=1e-7):
                raise ValueError(f'{r_case}: independent {r_field} disagrees: R={actual}, Python={expected}')
            differences.append(abs(actual-expected))
    return {'status':'passed','selected_cases':len(CASES),'numeric_comparisons':len(differences),
            'maximum_absolute_difference':max(differences),
            'absolute_tolerance':1e-8,'relative_tolerance':1e-7,
            'scope':'Independent transformations, samples, QR estimates, joint calendar covariance and intervals; not causal identification'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('python_csv',type=Path)
    parser.add_argument('r_csv',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    report=compare(args.python_csv,args.r_csv)
    report['r_runtime']=subprocess.check_output(['Rscript','--version'],stderr=subprocess.STDOUT).decode().strip()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
