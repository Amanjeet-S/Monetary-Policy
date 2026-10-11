"""Describe the locked origin sample without fitting an outcome regression."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from local_projections import build_design, load_panel, log_change

ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / 'results/sample_description.json'


def describe() -> dict:
    spec_path = ROOT / 'docs/primary_specification.json'
    spec = json.loads(spec_path.read_text())
    summary = json.loads((ROOT / 'results/summary.json').read_text())
    panel_path = ROOT / 'data/processed/monthly_panel.csv'
    paths = {'specification': spec_path, 'panel': panel_path,
             'estimates': ROOT / 'results/estimates.csv'}
    hashes = {key: hashlib.sha256(path.read_bytes()).hexdigest()
              for key, path in paths.items()}
    for key, expected in [('specification', 'specification_sha256'),
                          ('panel', 'panel_sha256'), ('estimates', 'estimates_sha256')]:
        if hashes[key] != summary[expected]:
            raise ValueError(f'Retained {key} differs from the fixed analysis')
    panel = load_panel(panel_path)
    design = build_design(panel, spec['primary_horizon'], spec['primary_lag_order'],
                          spec['primary_sample_first'], spec['primary_sample_last'],
                          spec['shock_construction'], spec['shock_scale_pp'])
    n, q = design.z.shape
    if n != spec['expected_primary_rows'] or np.linalg.matrix_rank(design.z) != q:
        raise ValueError('Sample size or control rank differs')
    values = np.column_stack([design.m, design.c, design.m + design.c])
    basis, _ = np.linalg.qr(design.z, mode='reduced')
    residual = values - basis @ (basis.T @ values)

    def moments(x):
        return {'sd_basis_points': dict(zip(['m','c','r'], map(float, 10*np.std(x, axis=0, ddof=1)))),
                'correlation_m_c': float(np.corrcoef(x[:,0], x[:,1])[0,1])}

    weight = float(residual[:,2] @ residual[:,1] / (residual[:,2] @ residual[:,2]))
    error = abs(weight - summary['primary']['weight'])
    if error > 1e-12 or not np.allclose(design.z.T @ residual, 0, atol=1e-10):
        raise ValueError('Control residualisation or retained weight differs')
    indices = np.array([panel['dates'].index(date) for date in design.dates])
    events = panel['derived_event_count'][indices]
    if not np.isfinite(events).all() or np.any(events < 0) or np.any(events != np.floor(events)):
        raise ValueError('Invalid retained event counts')
    if not np.all(values[events == 0] == 0):
        raise ValueError('Empty-event months must retain their zero contributions')
    return {'purpose': 'Post-estimation descriptive moments; no outcome regression or new test',
            'source_sha256': hashes,
            'sample': {'n':n, 'first':design.dates[0], 'last':design.dates[-1],
                       'control_columns':q, 'sd_divisor':n-1},
            'units': 'SDs in basis points of the normalised factor contribution; not actual policy-rate changes',
            'residualisation': 'Each current contribution projected on Z only, without the other current component',
            'before_controls': moments(values), 'after_controls': moments(residual),
            'monthly_growth_sd_log_points': {
                key: float(np.std(log_change(panel[key + '_index'], 1)[indices], ddof=1))
                for key in ['durable', 'nondurable']},
            'event_counts': {'retained_rows':int(events.sum()),
                             'months_with_events':int(np.count_nonzero(events)),
                             'months_without_events':int(np.count_nonzero(events == 0))},
            'weight_check': {'from_residual_moments':weight, 'absolute_error':error}}


def check(actual, expected):
    if isinstance(actual, dict):
        if actual.keys() != expected.keys():
            raise ValueError('Description fields differ')
        for key in actual:
            check(actual[key], expected[key])
    elif isinstance(actual, float):
        if not np.isclose(actual, expected, rtol=1e-10, atol=1e-12):
            raise ValueError('Retained descriptive value differs')
    elif actual != expected:
        raise ValueError('Retained description differs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare with the retained summary without writing')
    args = parser.parse_args()
    result = describe()
    if args.check:
        check(result, json.loads(RETAINED.read_text()))
        print(f"Reproduced descriptive moments on {result['sample']['n']} locked origins.")
    else:
        RETAINED.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        print('Saved results/sample_description.json; outcome estimates unchanged.')
