#!/usr/bin/env python3
"""Compare independent R stability and rotation quantities with retained results."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def path_value(value, path: str):
    for key in path.split('.'):
        value = value[int(key)] if isinstance(value,list) else value[key]
    return value


def compare(root: Path, stability: Path|None, regime: Path|None, rotation: Path|None, causal: Path|None) -> dict:
    checks=[]
    def check(actual, expected, label):
        actual,expected=float(actual),float(expected)
        if not math.isfinite(actual) or not math.isfinite(expected):
            raise ValueError(f'Non-finite independent comparison: {label}')
        error=abs(actual-expected)
        if not math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-10):
            raise ValueError(f'Independent R mismatch: {label}: {actual} versus {expected}')
        checks.append({'label':label,'absolute_difference':error})
    def rows(path):
        with path.open(newline='') as stream:
            return list(csv.DictReader(stream))
    if stability or regime:
        retained=json.loads((root/'results/joint_stability.json').read_text())
    if stability:
        expected=retained['comparisons']; supplied=rows(stability)
        if len(supplied)!=len(expected):raise ValueError('Different number of independent contrasts')
        for row,target in zip(supplied,expected):
            label=f"{target['comparison']}.L{target['common_hac_bandwidth']}"
            if row['comparison']!=target['comparison']:raise ValueError('Contrast order differs')
            fields={'bandwidth':target['common_hac_bandwidth'],
                'difference':target['difference_right_minus_left'],
                'se':target['regular_diagnostic']['se'],
                'equality_p':target['regular_diagnostic']['two_sided_equality_p'],
                'ellipse_low':target['joint_ellipse95_image']['low'],
                'ellipse_high':target['joint_ellipse95_image']['high'],
                'ellipse_frontier':target['joint_ellipse95_image']['minimum_equivalence_margin_infimum'],
                'rectangle_low':target['joint_rectangle95_image']['low'],
                'rectangle_high':target['joint_rectangle95_image']['high'],
                'regular_frontier':target['regular_diagnostic']['minimum_tost_margin_infimum']}
            fields.update({f'a{i+1}':v for i,v in enumerate(target['coordinates'])})
            fields.update({f'V{i+1}{j+1}':v for i,vrow in enumerate(target['joint_coordinate_covariance'])
                           for j,v in enumerate(vrow)})
            if set(row)!=set(fields)|{'comparison'}:raise ValueError('Independent contrast fields differ')
            for key,value in fields.items():check(row[key],value,f'{label}.{key}')
    if regime:
        expected=retained['pooled_regime_tests']; supplied=rows(regime)
        if len(supplied)!=len(expected):raise ValueError('Different number of pooled regime checks')
        for row,target in zip(supplied,expected):
            label=f"pooled.L{target['bandwidth']}"
            fields={'bandwidth':target['bandwidth'],'n':target['n'],'k':target['columns'],
                'policy_interaction':target['post_minus_pre'][0],
                'information_interaction':target['post_minus_pre'][1],
                'V11':target['interaction_covariance'][0][0],
                'V12':target['interaction_covariance'][0][1],
                'V22':target['interaction_covariance'][1][1],
                'chi2':target['joint_wald_chi2'],'p':target['joint_wald_p']}
            if set(row)!=set(fields):raise ValueError('Independent regime fields differ')
            for key,value in fields.items():check(row[key],value,f'{label}.{key}')
    if rotation:
        retained=json.loads((root/'results/rotation_sensitivity.json').read_text())
        supplied=rows(rotation)
        if not supplied or any(set(row)!={'key','value'} for row in supplied):
            raise ValueError('Independent rotation table has invalid fields')
        if len({row['key'] for row in supplied})!=len(supplied):raise ValueError('Duplicate rotation quantity')
        for row in supplied:check(row['value'],path_value(retained,row['key']),f"rotation.{row['key']}")
    if causal:
        retained=json.loads((root/'results/causal_sensitivity.json').read_text())
        supplied=rows(causal)
        expected=dict(retained['primary_coefficients'])
        expected.update({f'primary_cov_{i+1}_{j+1}':v for i,row in enumerate(retained['primary_policy_information_covariance']) for j,v in enumerate(row)})
        for row in retained['loadings_benchmarks']:
            prefix=f"loading_{row['a']:g}_"
            expected.update({prefix+key:row[field] for key,field in [('response','conditional_policy_response'),('se','policy_response_se'),('ellipse_low','simultaneous_policy_95_low'),('ellipse_high','simultaneous_policy_95_high')]})
        for i,row in enumerate(retained['predetermined_outcome_results']):
            prefix=f'predetermined_{i+1}_'
            expected.update({prefix+key:row[field] for key,field in [('beta_m','coefficient_policy'),('beta_c','coefficient_information'),('wald','wald_two_degrees_freedom'),('p_value','p_value'),('bonferroni_p_value','bonferroni_three_outcomes_p_value')]})
            expected.update({prefix+f'cov_{j+1}_{k+1}':v for j,vrow in enumerate(row['covariance']) for k,v in enumerate(vrow)})
        if any(set(row)!={'quantity','value'} for row in supplied) or len(supplied)!=len(expected) or {row['quantity'] for row in supplied}!=set(expected):
            raise ValueError('Independent causal quantities differ')
        for row in supplied:check(row['value'],expected[row['quantity']],f"causal.{row['quantity']}")
    if not checks:raise ValueError('No independent numerical checks supplied')
    return {'status':'independent_R_verified','numeric_comparisons':len(checks),
            'maximum_absolute_difference':max(row['absolute_difference'] for row in checks),
            'relative_tolerance':1e-9,'absolute_tolerance':1e-10,'checks':checks}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--r-stability',type=Path)
    parser.add_argument('--r-regime',type=Path)
    parser.add_argument('--r-rotation',type=Path)
    parser.add_argument('--r-causal',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=compare(args.root,args.r_stability,args.r_regime,args.r_rotation,args.r_causal)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='checks'},indent=2))


if __name__=='__main__':main()
