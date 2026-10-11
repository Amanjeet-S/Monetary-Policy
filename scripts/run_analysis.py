"""Replay the fixed comparison, declared sensitivities and pointwise response paths."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import scipy

from audit_germany_data import ROOT
from build_monthly_panel import build_panel, PANEL_PATH
from local_projections import build_design, estimate, load_panel

SPEC_PATH = ROOT / 'docs/primary_specification.json'


def read_specification() -> tuple[dict, str]:
    if subprocess.check_output(["git","rev-parse","--is-shallow-repository"],cwd=ROOT).strip() == b"true":
        raise ValueError("Full Git history is required to verify the pre-estimation specification revision")
    if subprocess.check_output(['git','status','--porcelain','--',str(SPEC_PATH)],cwd=ROOT).strip():
        raise ValueError('Primary specification must be committed and unchanged before estimation')
    commit = subprocess.check_output(['git','log','-1','--format=%H','--',str(SPEC_PATH)],cwd=ROOT).decode().strip()
    if not commit:
        raise ValueError('No pre-estimation specification commit found')
    spec = json.loads(SPEC_PATH.read_text())
    manifest = ROOT / spec['snapshot'] / 'manifest.json'
    if spec['status'] != 'locked_before_main_estimation' or spec['version'] != 1:
        raise ValueError('Unsupported or unlocked specification')
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != spec['manifest_sha256']:
        raise ValueError('Source manifest differs from fixed specification')
    if (spec['primary_horizon'] != 12 or spec['primary_lag_order'] != 12
            or spec['shock_scale_pp'] != .10 or spec['shock_construction'] != 'median'):
        raise ValueError('Implementation requires a recorded version change for different primary choices')
    return spec, commit


def run(output: Path, figures: bool = True) -> dict:
    spec, commit = read_specification()
    built = build_panel()
    if built['raw_manifest']['path'] != spec['snapshot'] + '/manifest.json':
        raise ValueError('Panel was built from another source vintage')
    panel = load_panel(PANEL_PATH)
    h, p = spec['primary_horizon'], spec['primary_lag_order']
    first, last = spec['primary_sample_first'], spec['primary_sample_last']
    rows, diagnostics = [], []
    definitions = [('primary',h,p,first,last,'median','default'),
                   ('six_lags',h,6,first,last,'median','default'),
                   ('poor_man',h,p,first,last,'pm','default'),
                   ('pre_pandemic',h,p,first,'2018-12','median','default'),
                   ('short_bandwidth',h,p,first,last,'median','short'),
                   ('long_bandwidth',h,p,first,last,'median','long')]
    definitions += [(f'path_{j:02d}',j,p,spec['path_sample_first'],spec['path_sample_last'],
                     'median','default') for j in spec['path_horizons']]
    for case, horizon, lags, start, stop, construction, bandwidth in definitions:
        design = build_design(panel,horizon,lags,start,stop,construction,spec['shock_scale_pp'])
        result, check = estimate(design,case,bandwidth)
        rows.append(result)
        diagnostics.append(check)
    if rows[0]['n'] != spec['expected_primary_rows'] or any(
            r['n'] != spec['expected_path_rows'] for r in rows if r['case'].startswith('path_')):
        raise ValueError('Declared sample size differs from realised complete sample')
    output.mkdir(parents=True,exist_ok=True)
    estimates_path = output / 'estimates.csv'
    with estimates_path.open('w',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    summary = {'specification_commit':commit,
               'specification_sha256':hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest(),
               'source_manifest_sha256':spec['manifest_sha256'],
               'panel_sha256':built['panel']['sha256'],
               'estimates_sha256':hashlib.sha256(estimates_path.read_bytes()).hexdigest(),
               'primary':rows[0], 'primary_diagnostics':diagnostics[0],
               'path_sample':{'first':spec['path_sample_first'],'last':spec['path_sample_last'],
                              'n':spec['expected_path_rows'],'intervals':'pointwise, not simultaneous'},
               'uncertainty_scope':spec['uncertainty_scope'],
               'reproduction_versions':{'python':platform.python_version(),
                                        'numpy':np.__version__,'scipy':scipy.__version__}}
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    report = ROOT/'reports/analysis_execution.json'
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps({'executed_utc':datetime.now(timezone.utc).isoformat(),
                                 'summary':summary,'diagnostics':diagnostics},indent=2,allow_nan=False)+'\n')
    if figures:
        draw_figures(rows,output/'figures')
    return summary


def draw_figures(rows: list[dict], directory: Path) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    directory.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'svg.fonttype':'none','savefig.dpi':180})
    path = [r for r in rows if r['case'].startswith('path_')]
    horizons = np.array([r['horizon'] for r in path])
    fig, ax = plt.subplots(figsize=(7.5,4.6),layout='constrained')
    for key, label, colour in [('beta_m','Policy component','#245d8f'),
                               ('gamma','Recomposed rate surprise','#ba5b21')]:
        ax.plot(horizons,[r[key] for r in path],label=label,color=colour,lw=1.8,
                linestyle='--' if key=='gamma' else '-')
        ax.fill_between(horizons,[r[key+'_low'] for r in path],
                         [r[key+'_high'] for r in path],color=colour,alpha=.14)
    ax.axhline(0,color='#666666',lw=.7)
    ax.axvline(12,color='#aaaaaa',ls=':',lw=.8)
    ax.set(xlabel='Months after the announcement month',
           ylabel='Durable minus non-durable cumulative log change\n(percentage log points, per 10 bp factor contribution)',
           xticks=[0,6,12,18,24],title='German consumer-goods production responses')
    ax.legend(loc='upper left',bbox_to_anchor=(0,1.18),frameon=False,ncol=2)
    fig.text(.5,-.03,'Common origins: Jan 2000–Aug 2024, n=296. Shading: 95% pointwise HAC intervals.',
             ha='center',fontsize=8)
    for extension in ['png','svg']:
        destination=directory/f'response_paths.{extension}'
        fig.savefig(destination,bbox_inches='tight')
        if extension=='svg':
            destination.write_text('\n'.join(line.rstrip() for line in destination.read_text().splitlines())+'\n')
    plt.close(fig)
    checks = [r for r in rows if not r['case'].startswith('path_')]
    labels = ['Primary comparison','Six lags, matched sample','Poor-man decomposition',
              'Pre-pandemic outcome window','Short HAC bandwidth','Long HAC bandwidth']
    fig,ax=plt.subplots(figsize=(7.5,4.6),layout='constrained')
    for i,row in enumerate(checks):
        lo,hi=row['delta_product_low'],row['delta_product_high']
        ax.plot([lo,hi],[i,i],color='#245d8f',lw=2.3 if i==0 else 1.4)
        ax.plot(row['delta'],i,'o',color='#245d8f',ms=6 if i==0 else 4)
    ax.axvline(0,color='#666666',lw=.7)
    ax.set(yticks=range(len(checks)),yticklabels=labels,
           xlabel='Recomposed-rate response minus policy-component response\n(per cent log points, per 10 bp factor contribution)',
           title='Information-adjustment gap at twelve months')
    ax.invert_yaxis()
    fig.text(.5,-.03,'95% conservative product intervals. All n=308 except pre-pandemic n=228.',
             ha='center',fontsize=8)
    for extension in ['png','svg']:
        destination=directory/f'primary_sensitivity.{extension}'
        fig.savefig(destination,bbox_inches='tight')
        if extension=='svg':
            destination.write_text('\n'.join(line.rstrip() for line in destination.read_text().splitlines())+'\n')
    plt.close(fig)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'results')
    parser.add_argument('--no-figures',action='store_true')
    args=parser.parse_args()
    result=run(args.output,not args.no_figures)
    print(json.dumps({'specification_commit':result['specification_commit'],
                      'primary':result['primary']},indent=2))
