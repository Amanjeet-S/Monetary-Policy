#!/usr/bin/env python3
"""Joint construction and sample-period contrasts of the twelve-month gap."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import brentq
from scipy.stats import chi2, norm


def quadratic_ball_minimum(q: np.ndarray, b: np.ndarray, constant: float) -> dict:
    """Globally minimise constant+b'u+u'Qu over ||u||<=1.

    The eigensystem solves the positive-semidefinite trust-region KKT system,
    including the hard case in which the linear term is orthogonal to the
    minimum eigenspace. No local optimiser or finite grid selects the bound.
    """
    q = (q + q.T) / 2
    eigenvalues, vectors = np.linalg.eigh(q)
    g = vectors.T @ b / 2
    scale = max(1., float(np.max(np.abs(eigenvalues))), float(np.linalg.norm(g)))
    tol = 128 * np.finfo(float).eps * scale
    lower = max(0., -float(eigenvalues[0]))
    denominators = eigenvalues + lower
    zero = np.abs(denominators) <= tol
    compatible = float(np.linalg.norm(g[zero])) <= tol
    particular = np.zeros_like(g)
    particular[~zero] = -g[~zero] / denominators[~zero]
    if compatible and np.linalg.norm(particular) <= 1. + 1e-12:
        coordinates = particular
        multiplier = lower
        if lower > tol:
            # Singular shifted Hessian: fill the remaining radius in its nullspace.
            coordinates[np.flatnonzero(zero)[0]] = np.sqrt(max(0., 1.-coordinates@coordinates))
    else:
        def secular(multiplier: float) -> float:
            d = eigenvalues + multiplier
            with np.errstate(over='ignore',divide='ignore'):
                return float(np.sum((g / d)**2) - 1.)

        left = lower
        if np.any(zero):
            left = np.nextafter(lower, np.inf)
        right = max(1., lower + scale)
        while secular(right) > 0:
            right = lower + 2 * (right-lower)
        multiplier = brentq(secular, left, right, xtol=1e-14, rtol=1e-14)
        coordinates = -g / (eigenvalues+multiplier)
    u = vectors @ coordinates
    value = float(constant + b@u + u@q@u)
    stationarity = float(np.linalg.norm((q+multiplier*np.eye(len(b)))@u+b/2))
    radius_error = max(0., float(np.linalg.norm(u)-1.))
    complementarity = abs(float(multiplier*(u@u-1.)))
    psd_minimum = float(np.linalg.eigvalsh(q+multiplier*np.eye(len(b)))[0])
    if max(stationarity, radius_error, complementarity, max(0., -psd_minimum)) > 1e-8*scale:
        raise ValueError('Quadratic confidence-set optimisation failed its KKT certificate')
    return {'value': value, 'point_on_unit_ball': u.tolist(),
            'multiplier': float(multiplier), 'stationarity_error': stationarity,
            'radius_error': radius_error, 'complementarity_error': complementarity,
            'shifted_hessian_smallest_eigenvalue': psd_minimum}


def quadratic_image(a: np.ndarray, covariance: np.ndarray, matrix: np.ndarray,
                    level: float) -> dict:
    if len(a) != len(covariance) or not 0 < level < 1:
        raise ValueError('Invalid confidence-set inputs')
    chol = np.linalg.cholesky(covariance)
    critical = float(chi2.ppf(level, len(a)))
    radius_matrix = np.sqrt(critical) * chol
    q = radius_matrix.T @ matrix @ radius_matrix
    b = 2 * radius_matrix.T @ matrix @ a
    constant = float(a@matrix@a)
    lower = quadratic_ball_minimum(q, b, constant)
    upper = quadratic_ball_minimum(-q, -b, -constant)
    return {'level': level, 'degrees_of_freedom': len(a),
            'critical_value': critical, 'low': lower['value'], 'high': -upper['value'],
            'minimum_equivalence_margin_infimum': max(abs(lower['value']), abs(upper['value'])),
            'zero_included': lower['value'] <= 0 <= -upper['value'],
            'optimisation_certificate': {'lower': lower, 'upper_negated_objective': upper}}


def coordinate_fit(design, ols) -> dict:
    z, m, c, y = design.z, design.m, design.c, design.y
    xf, xr = np.column_stack([m,c,z]), np.column_stack([m+c,z])
    bf, ef, lf, _ = ols(xf, y)
    br, er, lr, _ = ols(xr, y)
    bw, ew, _, _ = ols(xr, c)
    w, theta = float(bw[0]), float(bf[1]-bf[0])
    gap = float(br[0]-bf[0])
    influences = np.column_stack([lr[:,0]*ew, (lf[:,1]-lf[:,0])*ef])
    direct_influence = lr[:,0]*er-lf[:,0]*ef
    error = float(np.max(np.abs(direct_influence-influences@np.array([theta,w]))))
    if not np.isclose(gap,w*theta,atol=1e-9,rtol=1e-9) or error > 1e-9:
        raise ValueError('Matched gap identity failed')
    n,k = xf.shape
    return {'calendar': design.calendar, 'dates': design.dates,
            'coordinates': np.array([w,theta]), 'gap': gap,
            'influences': influences*np.sqrt(n/(n-k)),
            'direct_influence': direct_influence*np.sqrt(n/(n-k)),
            'n': n, 'columns': k, 'correction': n/(n-k), 'identity_error': error}


def joint_comparison(left: dict, right: dict, bandwidth: int, margins: list[float], calendar_hac) -> dict:
    calendar = np.union1d(left['calendar'],right['calendar'])
    influences = np.zeros((len(calendar),4))
    influences[np.searchsorted(calendar,left['calendar']),:2] = left['influences']
    influences[np.searchsorted(calendar,right['calendar']),2:] = right['influences']
    covariance = calendar_hac(influences,calendar,bandwidth,correction=1.)
    a = np.concatenate([left['coordinates'],right['coordinates']])
    matrix = np.zeros((4,4))
    matrix[0,1] = matrix[1,0] = -.5
    matrix[2,3] = matrix[3,2] = .5
    difference = right['gap']-left['gap']
    if not np.isclose(difference,a@matrix@a,atol=1e-9,rtol=1e-9):
        raise ValueError('Gap-difference identity failed')
    gradient = 2*matrix@a
    se = float(np.sqrt(gradient@covariance@gradient))
    embedded_direct = np.zeros(len(calendar))
    embedded_direct[np.searchsorted(calendar,left['calendar'])] -= left['direct_influence']
    embedded_direct[np.searchsorted(calendar,right['calendar'])] += right['direct_influence']
    if not np.allclose(embedded_direct,influences@gradient,atol=1e-9,rtol=1e-9):
        raise ValueError('Joint direct-difference influence identity failed')
    projected = quadratic_image(a,covariance,matrix,.95)
    critical = norm.ppf(1-.05/(2*4))
    bounds = np.column_stack([a-critical*np.sqrt(np.diag(covariance)),
                              a+critical*np.sqrt(np.diag(covariance))])
    left_products = [u*v for u in bounds[0] for v in bounds[1]]
    right_products = [u*v for u in bounds[2] for v in bounds[3]]
    rectangle_low = min(right_products)-max(left_products)
    rectangle_high = max(right_products)-min(left_products)
    return {'difference_right_minus_left': difference, 'common_hac_bandwidth': bandwidth,
            'left_n': left['n'], 'right_n': right['n'],
            'left_correction': left['correction'], 'right_correction': right['correction'],
            'coordinate_order': ['left_weight','left_theta','right_weight','right_theta'],
            'coordinates': a.tolist(), 'joint_coordinate_covariance': covariance.tolist(),
            'joint_covariance_smallest_eigenvalue': float(np.linalg.eigvalsh(covariance)[0]),
            'gap_covariance': float(np.array([a[1],a[0]])@covariance[:2,2:]@np.array([a[3],a[2]])),
            'regular_diagnostic': {'se': se, 'normal95_low': difference-norm.ppf(.975)*se,
                'normal95_high': difference+norm.ppf(.975)*se,
                'two_sided_equality_p': float(2*norm.sf(abs(difference/se))),
                'normal90_low': difference-norm.ppf(.95)*se,
                'normal90_high': difference+norm.ppf(.95)*se,
                'minimum_tost_margin_infimum': abs(difference)+norm.ppf(.95)*se,
                'equivalence_tost': [{'margin':margin,
                    'p_value':float(max(norm.sf((difference+margin)/se),
                                       norm.cdf((difference-margin)/se)))} for margin in margins]},
            'joint_ellipse95_image': projected,
            'joint_rectangle95_image': {'low':float(rectangle_low),'high':float(rectangle_high),
                'minimum_equivalence_margin_infimum':float(max(abs(rectangle_low),abs(rectangle_high)))},
            'conservative_equivalence': [{'margin':margin,
                'ellipse95_image_strictly_inside_margin':bool(projected['low']>-margin and projected['high']<margin),
                'rectangle95_image_strictly_inside_margin':bool(rectangle_low>-margin and rectangle_high<margin)}
                for margin in margins]}


def pooled_regime(design, bandwidth: int, ols, calendar_hac) -> dict:
    # The first block has origins through December 2018: all endpoints precede 2020.
    post = np.array([float(date>='2019-01') for date in design.dates])
    x = np.column_stack([design.m,design.c,post*design.m,post*design.c,post,design.z])
    coefficients,residuals,operator,leverage = ols(x,design.y)
    n,k=x.shape
    influences=operator*residuals[:,None]
    covariance=calendar_hac(influences,design.calendar,bandwidth,n/(n-k))
    interaction=coefficients[2:4]
    v=covariance[2:4,2:4]
    statistic=float(interaction@np.linalg.solve(v,interaction))
    return {'origins_first':design.dates[0],'origins_last':design.dates[-1],
            'break_origin':'2019-01','endpoint_regime':'Endpoints before January 2020 versus January 2020 onwards',
            'n':n,'pre_origins':int(sum(post==0)),'post_origins':int(sum(post==1)),
            'columns':k,'residual_df':n-k,'bandwidth':bandwidth,
            'restriction':'Common seasonal and twelve-lag dynamics; regime-specific intercept and current policy/information slopes',
            'policy_pre':float(coefficients[0]),'information_pre':float(coefficients[1]),
            'policy_post':float(coefficients[0]+coefficients[2]),
            'information_post':float(coefficients[1]+coefficients[3]),
            'post_minus_pre':interaction.tolist(),'interaction_covariance':v.tolist(),
            'joint_wald_chi2':statistic,'joint_wald_df':2,'joint_wald_p':float(chi2.sf(statistic,2)),
            'maximum_leverage':float(max(leverage)),
            'scaled_condition':float(np.linalg.cond(x/np.linalg.norm(x,axis=0))),
            'interpretation':'A conditional component-response stability test under common lag dynamics, not a causal regime effect or a scalar gap-decomposition test'}


def calculate(root: Path, margins: list[float]) -> dict:
    root=root.resolve()
    sys.path.insert(0,str(root/'scripts'))
    from local_projections import build_design, calendar_hac, load_panel, ols
    primary_path=root/'docs/primary_specification.json'
    estimates_path=root/'results/estimates.csv'
    plan_path=root/'docs/extension_specification.json'
    plan=json.loads(plan_path.read_text())
    if plan.get('status')!='declared_post_estimation_extension':
        raise ValueError('A recorded post-estimation extension is required')
    before={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [primary_path,estimates_path]}
    if (plan.get('primary_specification_sha256')!=before['docs/primary_specification.json']
        or plan.get('estimates_sha256')!=before['results/estimates.csv']):
        raise ValueError('Primary evidence differs from the recorded extension')
    panel=load_panel(root/'data/processed/monthly_panel.csv')
    definitions=[('median_full','2025-08','median'),('poor_man_full','2025-08','pm'),
                 ('median_pre','2018-12','median')]
    fits={}
    designs={}
    for name,last,construction in definitions:
        design=build_design(panel,12,12,'2000-01',last,construction,.10)
        designs[name]=design
        fits[name]=coordinate_fit(design,ols)
    with estimates_path.open(newline='') as handle:
        retained={r['case']:r for r in csv.DictReader(handle)}
    for name,case in [('median_full','primary'),('poor_man_full','poor_man'),('median_pre','pre_pandemic')]:
        fit=fits[name]
        for value,key in [(fit['gap'],'delta'),(fit['coordinates'][0],'weight'),(fit['coordinates'][1],'theta')]:
            if not np.isclose(value,float(retained[case][key]),atol=1e-10,rtol=1e-10):
                raise ValueError('Extension refit differs from locked retained coefficient')
    comparisons=[]
    for name,right in [('construction','poor_man_full'),('sample_period','median_pre')]:
        for bandwidth in [18,17]:
            result=joint_comparison(fits['median_full'],fits[right],bandwidth,margins,calendar_hac)
            result['comparison']=name
            result['bandwidth_role']='primary_extension' if bandwidth==18 else 'declared_sensitivity'
            comparisons.append(result)
    regimes=[pooled_regime(designs['median_full'],bandwidth,ols,calendar_hac)
             for bandwidth in [18,17]]
    after={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
           for path in [primary_path,estimates_path]}
    if before!=after:
        raise ValueError('Locked primary evidence changed')
    return {'status':'post_estimation_extension','horizon':12,'margins':margins,
            'extension_specification_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            'immutable_primary_hashes':before,'comparisons':comparisons,'pooled_regime_tests':regimes,
            'inference_scope':'Fixed dimension, jointly regular weight/theta coordinates and consistent calendar-HAC; nonlinear confidence-set projection does not require a nonzero product gradient. Separate equality non-rejection does not establish equivalence.',
            'equivalence_scope':'The 95 per cent joint-set containment rule is a conservative five per cent equivalence decision. The regular normal TOST is a separate diagnostic under a nondegenerate gap-difference limit.',
            'sample_period_scope':'The retained full and pre-period projections have different calendar-specific targets; the contrast is not a stand-alone post-period effect.'}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path)
    parser.add_argument('--margins',type=float,nargs='*',default=[])
    parser.add_argument('--check',action='store_true',help='Recalculate and compare retained output without writing')
    args=parser.parse_args()
    if any(not np.isfinite(margin) or margin<=0 for margin in args.margins):
        raise ValueError('Equivalence margins must be positive and fixed before the extension')
    result=calculate(args.root,args.margins)
    output=args.output or args.root/'results/joint_stability.json'
    if args.check:
        from gap_followup import compare_objects
        count=compare_objects(result,json.loads(output.read_text()))
        print(f'Retained joint stability matches: {count} numeric fields')
    else:
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'comparisons':[{'comparison':row['comparison'],
        'bandwidth':row['common_hac_bandwidth'],'difference':row['difference_right_minus_left'],
        'normal_se':row['regular_diagnostic']['se'],
        'normal_p':row['regular_diagnostic']['two_sided_equality_p'],
        'ellipse95_low':row['joint_ellipse95_image']['low'],
        'ellipse95_high':row['joint_ellipse95_image']['high']}
        for row in result['comparisons']],
        'pooled_regime_p':[row['joint_wald_p'] for row in result['pooled_regime_tests']]},indent=2))


if __name__=='__main__':
    main()
