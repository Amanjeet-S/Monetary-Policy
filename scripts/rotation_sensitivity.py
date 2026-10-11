"""Sign-admissible event-factor sensitivity on unchanged German origins.

All rotations use the retained rounded policy factor and equity surprise.
The continuum calculation keeps unrounded rotated components, avoiding a
discontinuous numerical quantisation of an otherwise smooth rotation family.
The author-median construction is separately reproduced after eight-decimal
rounding. Confidence projections condition on the retained event-factor
construction; they do not include uncertainty from estimating that construction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.stats import chi2, norm

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
PRIMARY_SPECIFICATION_SHA256 = 'e08af0188332ae0dd04f334f321a73af21d87d7bfaa9e2cd7f9b3b2facbcec84'
PRIMARY_ESTIMATES_SHA256 = '2fdd836f59da36ba29f852ec489836b097d473fe5e547fdac883bdb9afb81c73'
EXTENSION_SPECIFICATION_SHA256 = '4f0daf3691cde3a4f5ad9e19a3c88c72bd656233f7f0264640fe7a90c317289e'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declaration_check(root):
    expected = {'docs/primary_specification.json': PRIMARY_SPECIFICATION_SHA256,
                'results/estimates.csv': PRIMARY_ESTIMATES_SHA256,
                'docs/extension_specification.json': EXTENSION_SPECIFICATION_SHA256}
    for relative, wanted in expected.items():
        if digest(root/relative) != wanted:
            raise ValueError(f'Immutable declaration or primary evidence changed: {relative}')
    return expected


def factor_setup(root):
    event_path = root / 'data/raw/2026-10-10/jk_ecb_events.csv'
    with event_path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    dates = [r['date'] for r in rows]
    matrix = np.array([[float(r['pc1']), float(r['STOXX50'])] for r in rows])
    q, r = np.linalg.qr(matrix, mode='reduced')
    sign = np.diag(np.sign(np.diag(r)))
    q, r = q @ sign, sign @ r
    if min(np.diag(r)) <= 0 or not np.isfinite(matrix).all():
        raise ValueError('Complete full-rank event matrix required')
    lower = math.atan(r[0, 1]/r[1, 1]) if r[0, 1] > 0 else 0.
    upper = math.pi/2 if r[0, 1] >= 0 else math.atan2(r[1, 1], -r[0, 1])
    angle = (lower + upper)/2
    cosine, sine = math.cos(angle), math.sin(angle)
    rotation = np.array([[cosine, sine], [-sine, cosine]])
    normalisation = np.diag([r[0, 0]*cosine, r[0, 0]*sine])
    median = q @ rotation @ normalisation
    supplied = np.array([[float(row['MP_median']), float(row['CBI_median'])]
                         for row in rows])
    rounded_error = float(np.max(np.abs(np.round(median, 8)-supplied)))
    if rounded_error != 0:
        raise ValueError('Author median did not reproduce exactly after rounding')
    v = q[:, 1]*r[0, 0]
    rate = matrix[:, 0]
    return {'dates': dates, 'rate': rate, 'v': v, 'R': r,
            'lower': lower, 'upper': upper, 'median': angle,
            'source': {'event_sha256': digest(event_path),
                       'event_rows': len(rows), 'qr_positive_diagonal': r.tolist(),
                       'angle_lower_radians': lower, 'angle_upper_radians': upper,
                       'angle_lower_degrees': math.degrees(lower),
                       'angle_upper_degrees': math.degrees(upper),
                       'median_radians': angle,
                       'rounded_median_max_abs_error': rounded_error,
                       'unrounded_median_max_abs_error': float(np.max(np.abs(median-supplied))),
                       'normalisation': 'Both shocks have unit impact on the retained one-year-scaled policy factor; regressors divided by 0.10 percentage points',
                       'strict_sign_set': 'Positive rate loadings for both components; policy equity loading strictly negative, information equity loading strictly positive',
                       'endpoint_conventions': 'Strict interior only. Report continuous one-sided limits for defined coefficient contrasts. A zero normalisation endpoint is rank-degenerate and is not fitted.',
                       'upstream_commit': 'f7ffc821b0ade71dd38539e4044e25368dfb4dc1',
                       'upstream_exclusions': ['2001-09-13', '2001-09-17', '2008-10-08']}}


def monthly_basis(factor, panel):
    first, last = factor['dates'][0][:7], factor['dates'][-1][:7]
    buckets = {month: [0., 0.] for month in panel['dates'] if first <= month <= last}
    for date, rate, v in zip(factor['dates'], factor['rate'], factor['v']):
        buckets[date[:7]][0] += rate
        buckets[date[:7]][1] += v
    r = np.array([buckets[d][0] if d in buckets else np.nan for d in panel['dates']])
    v = np.array([buckets[d][1] if d in buckets else np.nan for d in panel['dates']])
    return r, v


def estimate_rotation(root, factor, output_dir, grid_count=1001, write_outputs=True):
    sys.path.insert(0, str(root/'scripts'))
    from local_projections import build_design, load_panel, ols, calendar_hac, estimate
    panel = load_panel(root/'data/processed/monthly_panel.csv')
    r, v = monthly_basis(factor, panel)
    basis_panel = dict(panel)
    basis_panel['shock_MP_median'] = r
    basis_panel['shock_CBI_median'] = v
    design = build_design(basis_panel, 12, 12, '2000-01', '2025-08')
    z, rate, orthogonal, y = design.z, design.m, design.c, design.y
    xf = np.column_stack([rate, orthogonal, z])
    xr = np.column_stack([rate, z])
    bf, ef, lf, leverage = ols(xf, y)
    br, er, lr, _ = ols(xr, y)
    bk, ek, _, _ = ols(xr, orthogonal)
    scores = np.column_stack([lf[:, 0]*ef, lf[:, 1]*ef, lr[:, 0]*er,
                              lr[:, 0]*ek])
    n, k = xf.shape
    bandwidth = 12 + int(np.ceil(4*(n/100)**(2/9)))
    covariance = calendar_hac(scores, design.calendar, bandwidth, n/(n-k))
    basis_coefs = np.array([bf[0], bf[1], br[0]])
    kappa = float(bk[0])
    if not np.isclose(br[0]-bf[0], bf[1]*kappa, atol=1e-10):
        raise ValueError('Invariant basis mixture identity failed')
    coefficient_covariance = covariance[:3, :3]
    if min(np.linalg.eigvalsh(coefficient_covariance)) <= 0:
        raise ValueError('Nondegenerate three-coordinate covariance required for joint ellipsoid')
    critical_joint = float(np.sqrt(chi2.ppf(.95, 3)))
    critical_point = float(norm.ppf(.975))
    critical_product = float(norm.ppf(.9875))
    median_angle = factor['median']

    def evaluate(a, label='interior'):
        s, c, t = math.sin(a), math.cos(a), math.tan(a)
        vm = np.array([1., -t, 0.])
        vd = np.array([-1., t, 1.])
        beta_m = float(vm@basis_coefs)
        delta = float(vd@basis_coefs)
        m_se = float(np.sqrt(vm@coefficient_covariance@vm))
        d_se = float(np.sqrt(vd@coefficient_covariance@vd))
        result = {'angle_radians': a, 'angle_degrees': math.degrees(a),
                  'label': label, 'beta_m': beta_m, 'delta': delta,
                  'gamma': float(br[0]), 'beta_m_se': m_se, 'delta_se': d_se,
                  'beta_m_point_low': beta_m-critical_point*m_se,
                  'beta_m_point_high': beta_m+critical_point*m_se,
                  'delta_point_low': delta-critical_point*d_se,
                  'delta_point_high': delta+critical_point*d_se,
                  'beta_m_joint_low': beta_m-critical_joint*m_se,
                  'beta_m_joint_high': beta_m+critical_joint*m_se,
                  'delta_joint_low': delta-critical_joint*d_se,
                  'delta_joint_high': delta+critical_joint*d_se}
        if 0 < a < math.pi/2:
            theta = float(bf[1]/(s*c))
            theta_se = float(np.sqrt(covariance[1,1])/(s*c))
            weight = s*s+s*c*kappa
            weight_se = s*c*float(np.sqrt(covariance[3,3]))
            theta_p = float(2*norm.sf(abs(theta/theta_se)))
            weight_p = float(2*norm.sf(abs(weight/weight_se)))
            corners = [(weight+sx*critical_product*weight_se)*
                       (theta+sy*critical_product*theta_se)
                       for sx in [-1,1] for sy in [-1,1]]
            result.update(theta=theta, theta_se=theta_se, weight=weight,
                          weight_se=weight_se, theta_p=theta_p, weight_p=weight_p,
                          iut_p=max(theta_p, weight_p),
                          delta_product_low=min(corners), delta_product_high=max(corners),
                          identity_error=abs(delta-weight*theta))
        return result

    if factor['upper'] >= math.pi/2:
        raise ValueError('This retained analysis requires bounded policy/gap endpoint limits; handle an unbounded endpoint analytically instead')
    endpoints = [evaluate(factor['lower'], 'lower_one_sided_limit'),
                 evaluate(factor['upper'], 'upper_one_sided_limit')]
    fractions = np.linspace(1e-7, 1-1e-7, grid_count)
    angles = factor['lower']+(factor['upper']-factor['lower'])*fractions
    grid = [evaluate(float(a)) for a in angles]
    median_result = evaluate(median_angle, 'unrounded_author_median')
    validation = []
    for fraction in [.01, .25, .5, .75, .99]:
        a = factor['lower']+(factor['upper']-factor['lower'])*fraction
        cosine, sine = math.cos(a), math.sin(a)
        m = cosine*cosine*r-cosine*sine*v
        c = sine*sine*r+cosine*sine*v
        rotated = dict(panel, shock_MP_median=m, shock_CBI_median=c)
        direct, diagnostics = estimate(build_design(rotated, 12, 12, '2000-01', '2025-08'),
                                       f'rotation_{fraction}')
        algebraic = evaluate(a)
        fields = ['beta_m','gamma','delta','weight','theta','beta_m_se','delta_se',
                  'weight_se','theta_se','delta_product_low','delta_product_high']
        differences = {key: abs(direct[key]-algebraic[key]) for key in fields}
        if max(differences.values()) > 1e-8:
            raise ValueError(f'Direct rotation mismatch: {differences}')
        validation.append({'angle_fraction': fraction, 'max_difference': max(differences.values()),
                           'differences': differences,
                           'mixture_identity_error': diagnostics['mixture_identity_error']})
    supplied, _ = estimate(build_design(panel, 12, 12, '2000-01', '2025-08'), 'supplied_median')
    rounding_difference = {key: float(median_result[key]-supplied[key]) for key in
                           ['beta_m','gamma','delta','weight','theta','beta_m_se','delta_se']}
    if max(abs(x) for x in rounding_difference.values()) > 5e-6:
        raise ValueError('Median rounding bridge exceeded numerical tolerance')
    envelope = {}
    # Each upper objective is affine plus a norm, hence convex in tan(a),
    # and each lower objective is affine minus a norm, hence concave.
    # Global outer-envelope extrema therefore occur at a closure endpoint.
    for name in ['beta_m', 'delta']:
        envelope[name] = {'point_set_infimum': min(x[name] for x in endpoints),
                          'point_set_supremum': max(x[name] for x in endpoints),
                          'conditional_joint_envelope_low': min(x[name+'_joint_low'] for x in endpoints),
                          'conditional_joint_envelope_high': max(x[name+'_joint_high'] for x in endpoints),
                          'grid_min': min(x[name] for x in grid),
                          'grid_max': max(x[name] for x in grid)}
    primitive_critical = float(norm.ppf(1-.05/6))
    primitive_values = [float(bf[0]), float(bf[1]), kappa]
    primitive_indices = [0, 1, 3]
    primitive_bounds = [[value-primitive_critical*np.sqrt(covariance[index,index]),
                         value+primitive_critical*np.sqrt(covariance[index,index])]
                        for value, index in zip(primitive_values, primitive_indices)]
    if any(covariance[index,index] <= 0 for index in primitive_indices):
        raise ValueError('Nondegenerate primitive marginal variances required')
    tangent_bounds = [math.tan(factor['lower']), math.tan(factor['upper'])]
    policy_corners = [rate-tangent*orthogonal for rate in primitive_bounds[0]
                      for orthogonal in primitive_bounds[1] for tangent in tangent_bounds]
    gap_corners = [(tangent+mixture)*orthogonal for mixture in primitive_bounds[2]
                   for orthogonal in primitive_bounds[1] for tangent in tangent_bounds]
    primitive_rectangle = {
        'coordinates': ['b_rate', 'b_orthogonal', 'kappa'],
        'critical': primitive_critical,
        'bounds': primitive_bounds,
        'beta_m_envelope_low': min(policy_corners),
        'beta_m_envelope_high': max(policy_corners),
        'delta_envelope_low': min(gap_corners),
        'delta_envelope_high': max(gap_corners),
        'coverage_basis': 'A single Bonferroni 95 per cent rectangle for three regular nondegenerate marginal coordinates; its image simultaneously covers both complete coefficient families conditional on the retained factor, QR and sign set. Joint covariance may be singular and no product delta method is used.',
        'extrema_basis': 'Both mappings are affine separately in each primitive coordinate and tan(angle), so extrema over the rectangle and angle closure occur at corners.',
    }
    kappa_se = float(np.sqrt(covariance[3,3]))
    iut_limit_low = max(median_result['theta_p'], float(2*norm.sf(abs((math.tan(factor['lower'])+kappa)/kappa_se))))
    iut_limit_high = max(median_result['theta_p'], float(2*norm.sf(abs((math.tan(factor['upper'])+kappa)/kappa_se))))
    if kappa <= -math.tan(factor['lower']) and kappa >= -math.tan(factor['upper']):
        iut_supremum = 1.
    else:
        iut_supremum = max(iut_limit_low, iut_limit_high)
    report = {'status': 'post_estimation_extension',
              'declaration_and_primary_hashes': declaration_check(root), 'source': factor['source'],
              'sample': {'first': design.dates[0], 'last': design.dates[-1],
                         'n': n, 'lags': 12, 'full_columns': k, 'residual_df': n-k,
                         'bandwidth': bandwidth, 'maximum_leverage': float(max(leverage))},
              'basis': {'b_rate': float(bf[0]), 'b_orthogonal': float(bf[1]),
                        'gamma': float(br[0]), 'kappa': kappa,
                        'joint_coefficient_covariance': coefficient_covariance.tolist(),
                        'covariance_with_kappa': covariance.tolist(),
                        'joint_critical': critical_joint,
                        'joint_coefficient_covariance_eigenvalues': np.linalg.eigvalsh(coefficient_covariance).tolist()},
              'median': median_result, 'endpoint_limits': endpoints,
              'envelopes': envelope,
              'conservative_primitive_rectangle': primitive_rectangle,
              'theta_p_all_interior_rotations': median_result['theta_p'],
              'iut_p_range_on_dense_grid': [min(x['iut_p'] for x in grid), max(x['iut_p'] for x in grid)],
              'iut_p_supremum_on_strict_interval': iut_supremum,
              'iut_rejection_angle_lower_radians_at_5pc': math.atan(norm.ppf(.975)*kappa_se-kappa) if median_result['theta_p'] < .05 and kappa >= 0 else None,
              'zero_information_weight_angle': math.atan(-kappa) if kappa < 0 else None,
              'direct_refit_validation': validation,
              'retained_median_rounding_difference': rounding_difference,
              'grid_count': grid_count,
              'limits': [
                  'Sign restrictions are maintained assumptions, not evidence of event-shock exogeneity.',
                  'The interval endpoints are continuous limits for policy/gap contrasts; no singular lower-endpoint two-component regression is fitted.',
                  'The conditional joint envelope projects a three-coordinate regular Wald ellipsoid over every retained-factor rotation, rather than taking a nominal union of unrelated pointwise intervals.',
                  'The joint envelope requires a nondegenerate joint score limit and consistent covariance; it conditions on the supplied policy factor, empirical event QR and estimated admissible angle range.',
                  'The primitive rectangle companion needs regular nondegenerate marginal normal limits for b_rate, b_orthogonal and kappa, but accommodates singular joint covariance and the zero-product problem.',
                  'It does not supply unconditional identification-set confidence coverage accounting for generated factors, QR moments or the estimated sign-set boundary.',
                  'Both full and reduced controls contain both rotated histories, so their column span is invariant for nondegenerate rotations.',
                  'The dense grid is a numerical check; the policy/gap set endpoints and conditional joint envelope extrema follow analytically from affine/norm dependence on tan(angle).',
                  'The continuum keeps unrounded rotated components; separately reproducing the retained median gives the exact provider rounding bridge.',
              ]}
    if write_outputs:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir/'rotation_sensitivity.json').write_text(json.dumps(report, indent=2)+'\n')
        with (output_dir/'rotation_grid.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(grid[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(grid)
    return report, grid


def assert_retained_equal(observed, expected, prefix=''):
    if isinstance(observed, dict):
        if set(observed) != set(expected):
            raise ValueError(f'Retained keys changed: {prefix}')
        for key in observed:
            assert_retained_equal(observed[key], expected[key], f'{prefix}.{key}')
    elif isinstance(observed, list):
        if len(observed) != len(expected):
            raise ValueError(f'Retained list length changed: {prefix}')
        for i, (value, retained) in enumerate(zip(observed, expected)):
            assert_retained_equal(value, retained, f'{prefix}[{i}]')
    elif isinstance(observed, (float, np.floating)):
        if not math.isclose(observed, expected, rel_tol=1e-9, abs_tol=1e-10):
            raise ValueError(f'Retained numerical value changed: {prefix}')
    elif observed != expected:
        raise ValueError(f'Retained value changed: {prefix}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--factor-only', action='store_true')
    parser.add_argument('--grid-count', type=int, default=1001)
    parser.add_argument('--check', action='store_true', help='Recompute and compare retained results without writing them')
    args = parser.parse_args()
    output_dir = args.output_dir or args.root/'results'
    declaration_check(args.root)
    factor = factor_setup(args.root)
    if args.factor_only:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir/'rotation_factor_check.json').write_text(json.dumps(factor['source'], indent=2)+'\n')
        print(json.dumps(factor['source'], indent=2))
    else:
        report, grid = estimate_rotation(args.root, factor, output_dir, args.grid_count,
                                        write_outputs=not args.check)
        if args.check:
            retained = json.loads((output_dir/'rotation_sensitivity.json').read_text())
            assert_retained_equal(report, retained)
            with (output_dir/'rotation_grid.csv').open(newline='') as stream:
                retained_grid = list(csv.DictReader(stream))
            if len(grid) != len(retained_grid):
                raise ValueError('Retained rotation grid length changed')
            for index, (row, retained_row) in enumerate(zip(grid, retained_grid)):
                for key, value in row.items():
                    assert_retained_equal(value, float(retained_row[key]) if isinstance(value, float) else retained_row[key],
                                          f'grid[{index}].{key}')
        print(json.dumps({'envelopes': report['envelopes'], 'median': report['median'],
                          'theta_p': report['theta_p_all_interior_rotations'],
                          'iut_p_range': report['iut_p_range_on_dense_grid'],
                          'retained_results_verified': args.check}, indent=2))


if __name__ == '__main__':
    main()
