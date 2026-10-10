"""Matched local projections and joint calendar-HAC inference."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import norm


@dataclass
class Design:
    dates: list[str]
    calendar: np.ndarray
    z: np.ndarray
    m: np.ndarray
    c: np.ndarray
    y: np.ndarray
    durable: np.ndarray
    nondurable: np.ndarray
    horizon: int
    lags: int


def month_number(s: str) -> int:
    year, month = map(int, s.split('-'))
    if not 1 <= month <= 12:
        raise ValueError('Invalid calendar month')
    return 12 * year + month - 1


def load_panel(path: Path) -> dict:
    with path.open(newline='') as f:
        rows = list(csv.DictReader(f))
    dates = [r['month'] for r in rows]
    calendar = np.array([month_number(s) for s in dates])
    if not len(rows) or np.any(np.diff(calendar) != 1):
        raise ValueError('Panel must have unique consecutive calendar months')
    columns = {k: np.array([float(r[k]) if r[k] else np.nan for r in rows])
               for k in rows[0] if k != 'month'}
    for k in ['durable_index', 'nondurable_index', 'hicp_index']:
        x = columns[k]
        if np.any(np.isfinite(x) & (x <= 0)) or np.any(np.isinf(x)):
            raise ValueError(f'Invalid observed level: {k}')
    return {'dates': dates, 'calendar': calendar, **columns}


def log_change(x: np.ndarray, periods: int) -> np.ndarray:
    if periods < 1:
        raise ValueError('Change period must be positive')
    out = np.full(len(x), np.nan)
    out[periods:] = 100 * (np.log(x[periods:]) - np.log(x[:-periods]))
    return out


def build_design(panel: dict, h: int, p: int, first: str, last: str,
                 construction: str = 'median', scale: float = .10) -> Design:
    if (not isinstance(h, (int, np.integer)) or not isinstance(p, (int, np.integer))
            or h < 0 or p < 1 or not np.isfinite(scale) or scale <= 0
            or construction not in {'median', 'pm'}):
        raise ValueError('Unsupported projection specification')
    d, n = panel['durable_index'], panel['nondurable_index']
    m, c = (panel[f'shock_{k}_{construction}'] / scale for k in ['MP', 'CBI'])
    histories = [log_change(d, 1), log_change(n, 1),
                 log_change(panel['hicp_index'], 12), m, c]
    indices = np.flatnonzero((panel['calendar'] >= month_number(first)) &
                             (panel['calendar'] <= month_number(last)))
    expected = month_number(last) - month_number(first) + 1
    if len(indices) != expected or not len(indices):
        raise ValueError('Requested origin calendar is incomplete')
    z, yd, yn = [], [], []
    for i in indices:
        if i < p or i + h >= len(d):
            raise ValueError('Outcome endpoint or lag history is unavailable')
        month = int(panel['calendar'][i] % 12 + 1)
        z.append([1., *[float(month == j) for j in range(2, 13)],
                  *[x[i-lag] for lag in range(1, p+1) for x in histories]])
        yd.append(100 * (np.log(d[i+h]) - np.log(d[i-1])))
        yn.append(100 * (np.log(n[i+h]) - np.log(n[i-1])))
    z, yd, yn = np.asarray(z), np.asarray(yd), np.asarray(yn)
    if not all(np.isfinite(x).all() for x in [z, yd, yn, m[indices], c[indices]]):
        raise ValueError('Missing or invalid required input; no row imputation or silent deletion')
    return Design([panel['dates'][i] for i in indices], panel['calendar'][indices],
                  z, m[indices], c[indices], yd-yn, yd, yn, h, p)


def ols(x: np.ndarray, y: np.ndarray):
    if x.ndim != 2 or len(x) != len(y) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Invalid regression dimensions or nonfinite input')
    n, k = x.shape
    if n <= k or np.linalg.matrix_rank(x) != k:
        raise ValueError('Unique coefficients and positive residual degrees of freedom required')
    q, r = np.linalg.qr(x, mode='reduced')
    coefficients = np.linalg.solve(r, q.T @ y)
    residuals = y - x @ coefficients
    inverse_r = np.linalg.solve(r, np.eye(k))
    # Rows are coefficient contributions, not the n-scaled influence functions.
    linear_operator_transpose = q @ inverse_r.T
    return coefficients, residuals, linear_operator_transpose, np.sum(q*q, axis=1)


def calendar_hac(influences: np.ndarray, calendar: np.ndarray, bandwidth: int,
                 correction: float = 1.) -> np.ndarray:
    # The inputs already contain the OLS 1/n scaling; no extra n divisor follows.
    if (influences.ndim != 2 or calendar.ndim != 1
            or len(influences) != len(calendar) or len(calendar) == 0
            or not np.issubdtype(calendar.dtype, np.signedinteger)
            or np.any(np.diff(calendar) <= 0)
            or not isinstance(bandwidth, (int, np.integer)) or bandwidth < 0
            or not np.isfinite(correction) or correction <= 0
            or not np.isfinite(influences).all()):
        raise ValueError('Invalid influence scores or calendar')
    distance = calendar - calendar[0]
    embedded = np.zeros((int(distance[-1])+1, influences.shape[1]))
    embedded[distance] = influences
    covariance = embedded.T @ embedded
    for lag in range(1, min(bandwidth, len(embedded)-1)+1):
        cross = embedded[lag:].T @ embedded[:-lag]
        covariance += (1-lag/(bandwidth+1)) * (cross+cross.T)
    covariance = correction * (covariance + covariance.T) / 2
    if not np.isfinite(covariance).all():
        raise ValueError('Nonfinite HAC covariance')
    tolerance = 1e-9 * max(1., np.max(np.abs(covariance)))
    if np.min(np.linalg.eigvalsh(covariance)) < -tolerance:
        raise ValueError('HAC covariance failed positive-semidefiniteness check')
    return covariance


def product_interval(w: float, theta: float, se_w: float, se_theta: float,
                     alpha: float = .05) -> tuple[float, float]:
    if (not np.isfinite([w, theta, se_w, se_theta, alpha]).all()
            or not (0 < alpha < 1) or min(se_w, se_theta) <= 0):
        raise ValueError('Regular nondegenerate marginal inference required')
    critical = norm.ppf(1-alpha/4)
    wb = [w-critical*se_w, w+critical*se_w]
    tb = [theta-critical*se_theta, theta+critical*se_theta]
    if not wb[1] > wb[0] or not tb[1] > tb[0]:
        raise ValueError("Marginal confidence bounds are not representable")
    products = [a*b for a in wb for b in tb]
    if not np.isfinite(products).all():
        raise ValueError('Nonfinite product confidence bounds')
    return min(products), max(products)


def estimate(design: Design, case: str, bandwidth_kind: str = 'default'):
    z, m, c, y = design.z, design.m, design.c, design.y
    xf, xr = np.column_stack([m, c, z]), np.column_stack([m+c, z])
    bf, ef, lf, hf = ols(xf, np.column_stack([y, design.durable, design.nondurable]))
    br, er, lr, hr = ols(xr, y)
    bw, ew, _, _ = ols(xr, c)
    beta_m, beta_c, gamma, weight = bf[0,0], bf[1,0], br[0], bw[0]
    theta, delta = beta_c-beta_m, gamma-beta_m
    n, k = xf.shape
    b = int(np.ceil(4*(n/100)**(2/9)))
    choices = {'default': design.horizon+b, 'short': design.horizon+int(np.ceil(b/2)),
               'long': design.horizon+2*b}
    if bandwidth_kind not in choices:
        raise ValueError('Unsupported bandwidth convention')
    bandwidth = choices[bandwidth_kind]
    influences = np.column_stack([lf[:,0]*ef[:,0], lf[:,1]*ef[:,0],
                                   lr[:,0]*er, lr[:,0]*ew,
                                   lf[:,0]*ef[:,1], lf[:,0]*ef[:,2]])
    delta_if, theta_if = influences[:,2]-influences[:,0], influences[:,1]-influences[:,0]
    identity_error = float(np.max(np.abs(delta_if - weight*theta_if - theta*influences[:,3])))
    if not np.isclose(delta, weight*theta, atol=1e-9, rtol=1e-9) or identity_error > 1e-9:
        raise ValueError('Matched projection or joint influence identity failed')
    if not np.allclose(influences[:,0], influences[:,4]-influences[:,5], atol=1e-10, rtol=1e-8):
        raise ValueError('Sector-difference influence identity failed')
    covariance = calendar_hac(influences, design.calendar, bandwidth, n/(n-k))
    transforms = {'beta_m': [1,0,0,0,0,0], 'beta_c': [0,1,0,0,0,0],
                  'gamma': [0,0,1,0,0,0], 'weight': [0,0,0,1,0,0],
                  'theta': [-1,1,0,0,0,0], 'delta': [-1,0,1,0,0,0],
                  'beta_durable': [0,0,0,0,1,0], 'beta_nondurable': [0,0,0,0,0,1]}
    estimates = dict(zip(transforms, [beta_m,beta_c,gamma,weight,theta,delta,bf[0,1],bf[0,2]]))
    result = {'case':case, 'horizon':design.horizon, 'n':n, 'first':design.dates[0],
              'last':design.dates[-1], 'lags':design.lags, 'full_rank':k,
              'residual_df':n-k, 'bandwidth':bandwidth,
              'normal_interval_basis':'Asymptotic normal pointwise; the gap interval is a regularity-dependent diagnostic'}
    for name, value in estimates.items():
        vector = np.array(transforms[name])
        variance = float(vector @ covariance @ vector)
        if variance < -1e-10:
            raise ValueError('Negative contrast variance')
        se = np.sqrt(max(0.,variance))
        available = bool(se > 0)
        result.update({name:float(value), name+'_se':float(se),
                       name+'_normal_interval_available':available,
                       name+'_low':float(value-norm.ppf(.975)*se) if available else None,
                       name+'_high':float(value+norm.ppf(.975)*se) if available else None})
    low, high = product_interval(weight, theta, result['weight_se'], result['theta_se'])
    result.update(delta_product_low=float(low), delta_product_high=float(high),
                  covariance_beta_m_delta=float(covariance[0,2]-covariance[0,0]),
                  covariance_sectors=float(covariance[4,5]),
                  covariance_weight_theta=float(covariance[3,1]-covariance[3,0]))
    scaled_condition = np.linalg.cond(xf / np.linalg.norm(xf, axis=0))
    valid = (hf < 1-1e-10) & (hr < 1-1e-10)
    loo_m, loo_gamma = np.full(n, np.nan), np.full(n, np.nan)
    loo_m[valid] = beta_m - lf[valid,0]*ef[valid,0]/(1-hf[valid])
    loo_gamma[valid] = gamma - lr[valid,0]*er[valid]/(1-hr[valid])
    changes = loo_gamma-loo_m-delta
    top = sorted(np.flatnonzero(valid), key=lambda i: abs(changes[i]), reverse=True)[:5]
    qz, _ = np.linalg.qr(z, mode='reduced')
    shocks = np.column_stack([m, c, m+c])
    residual_shocks = shocks - qz @ (qz.T @ shocks)
    diagnostics = {'case':case, 'condition_columns_scaled_to_unit_norm':float(scaled_condition),
                   'rank_control':int(np.linalg.matrix_rank(z)),
                   'rank_reduced':int(np.linalg.matrix_rank(xr)),
                   'residual_shock_sums_of_squares':dict(zip(
                       ['policy','information','recomposed'],
                       map(float, np.sum(residual_shocks**2, axis=0)))),
                   'maximum_leverage_full':float(max(hf)),
                   'mixture_identity_error':float(abs(delta-weight*theta)),
                   'influence_identity_max_error':identity_error,
                   'sector_coefficient_identity_error':float(abs(beta_m-bf[0,1]+bf[0,2])),
                   'undefined_single_origin_deletions':int(np.sum(~valid)),
                   'largest_single_origin_gap_changes':[
                       {'month':design.dates[i], 'delta_without_origin':float(loo_gamma[i]-loo_m[i]),
                        'delta_change':float(changes[i]), 'policy_change':float(loo_m[i]-beta_m)} for i in top]}
    return result, diagnostics
