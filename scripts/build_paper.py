"""Refresh manuscript numerical blocks from retained estimates; optionally export PDF."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TEX=ROOT/'paper/monetary_policy.tex'


def table_primary(primary):
    labels=[('beta_durable','Durable policy response'),('beta_nondurable','Non-durable policy response'),
            ('beta_m','Relative policy response'),('beta_c','Relative information response'),
            ('gamma','Recomposed-rate response'),('delta','Adjustment gap')]
    lines=[]
    for key,label in labels:
        lo,hi=('delta_product_low','delta_product_high') if key=='delta' else (key+'_low',key+'_high')
        basis='Conservative product' if key=='delta' else 'Pointwise normal'
        lines.append(f"{label} & ${float(primary[key]):.2f}$ & $[{float(primary[lo]):.2f},{float(primary[hi]):.2f}]$ & {basis} \\\\")
    return r'''\begin{table}[htbp]
\centering\small
\caption{Primary twelve-month projections}
\label{tab:primary}
\begin{tabular}{@{}lrrl@{}}
\toprule
Quantity & Estimate & 95\% interval & Basis \\
\midrule
'''+ '\n'.join(lines)+r'''
\bottomrule
\end{tabular}
\par\smallskip\begin{minipage}{.97\textwidth}\footnotesize
Origins: January 2000--August 2025, $n=308$. Responses are percentage log-change points per ten-basis-point normalised factor contribution. The full model has 74 columns; Bartlett bandwidth is 18. The gap uses the prespecified product interval. Other intervals are individual normal approximations and do not give simultaneous coverage. The underlying sector coefficients retain their joint covariance.
\end{minipage}
\end{table}'''


def table_variation(description):
    before = description['before_controls']['sd_basis_points']
    after = description['after_controls']['sd_basis_points']
    rows = [f"{label} & ${before[key]:.2f}$ & ${after[key]:.2f}$ \\\\" for key, label in
            [('m','Policy contribution'),('c','Information contribution'),('r','Recomposed factor')]]
    return r"""\begin{table}[htbp]
\centering\small
\caption{Monthly announcement variation on the primary origins}
\label{tab:variation}
\begin{tabular}{@{}lrr@{}}
\toprule
Contribution & Sample SD, basis points & Control-residual SD, basis points \\
\midrule
""" + '\n'.join(rows) + r"""
\bottomrule
\end{tabular}
\par\smallskip\begin{minipage}{.97\textwidth}\footnotesize
January 2000--August 2025, $n=308$, including 45 months without retained events. Both columns use divisor $n-1$. The right column removes the same 72 controls defined in Section~\ref{sec:design} from each current contribution, without removing the other current component. These are descriptive standard deviations in normalised factor units, not disturbance standard errors or actual policy-rate changes.
\end{minipage}
\end{table}"""


def path_figure(path):
    def coordinates(key):
        return ' '.join(f"({r['horizon']},{float(r[key]):.10g})" for r in path)
    plots=[]
    for key,name,colour in [('beta_m','policy','policyblue'),('gamma','rate','newsorange')]:
        plots += [f'\\addplot[name path={name}lo,draw=none,forget plot] coordinates {{{coordinates(key+"_low")}}};',
                  f'\\addplot[name path={name}hi,draw=none,forget plot] coordinates {{{coordinates(key+"_high")}}};',
                  f'\\addplot[{colour}!15,draw=none,forget plot] fill between[of={name}lo and {name}hi];',
                  f'\\addplot[{colour},very thick'+(',dashed' if key=='gamma' else '')+f'] coordinates {{{coordinates(key)}}};',
                  '\\addlegendentry{'+('Policy component' if key=='beta_m' else 'Recomposed surprise')+'}']
    return r'''\begin{figure}[htbp]
\centering
\begin{tikzpicture}
\begin{axis}[width=.96\textwidth,height=6.0cm,
 axis lines=left,xmin=0,xmax=24,xtick={0,6,12,18,24},
 xlabel={Months after the announcement month},ylabel={Percentage log points},
 tick label style={font=\small},label style={font=\small},
 legend style={at={(0,1.02)},anchor=south west,draw=none,font=\small},legend columns=2,
 clip=true]
'''+ '\n'.join(plots)+r'''
\addplot[gray,thin,forget plot] coordinates {(0,0)(24,0)};
\addplot[gray,densely dotted,forget plot] coordinates {(12,-7)(12,1.5)};
\end{axis}
\end{tikzpicture}
\caption{Matched response paths. Coefficients are percentage log-change points per ten-basis-point factor contribution. Shading gives 95 per cent pointwise normal HAC intervals, not simultaneous bands. All horizons use 296 common origins, January 2000--August 2024; the primary twelve-month estimate uses the longer 308-origin sample. Appendix Table~\ref{tab:sensitivities} reports the directly assessed primary gap; overlap of these individual response bands is not a test of that gap.}
\label{fig:path}
\end{figure}'''


def sensitivity_table(checks):
    labels=['Primary','Six lags, matched','Poor-man components','Pre-pandemic endpoints','Short bandwidth','Long bandwidth']
    lines=[]
    for label,row in zip(labels,checks):
        get=lambda k:float(row[k])
        lines.append(f"{label} & {row['n']} & ${get('beta_m'):.2f}$ & $[{get('beta_m_low'):.2f},{get('beta_m_high'):.2f}]$ & ${get('delta'):.2f}$ & $[{get('delta_product_low'):.2f},{get('delta_product_high'):.2f}]$ \\\\")
    return r'''\begin{table}[htbp]
\centering\small
\caption{Numerical sensitivity comparisons at twelve months}
\label{tab:sensitivities}
\begin{tabular}{@{}lrrrrr@{}}
\toprule
Specification & $n$ & $\widehat\beta_m$ & Normal 95\% interval & $\widehat\delta$ & Product 95\% bounds \\
\midrule
'''+ '\n'.join(lines)+r'''
\bottomrule
\end{tabular}
\par\smallskip\begin{minipage}{.97\textwidth}\footnotesize
All responses use the same ten-basis-point factor units. Six-lag and poor-man comparisons retain the primary origins. Pre-pandemic endpoints end by December 2019. Short and long bandwidths are 15 and 24, versus 18 in the primary regression, leaving its coefficients unchanged. Intervals are pointwise and retain the declared primary uncertainty target.
\end{minipage}
\end{table}'''


def followup_summary(followup):
    row=followup['cases'][0]
    return (f"The primary intersection-union test gives $p={row['p_IUT']:.3f}$, a nominal 5 per cent rejection of the zero-product restriction. "
            f"Its joint-ellipse product bounds are $[{row['ellipse95_low']:.2f},{row['ellipse95_high']:.2f}]$. "
            "Every joint-region interval includes zero. The poor-man and pre-pandemic tests do not reject, "
            f"with $p={followup['cases'][2]['p_IUT']:.3f}$ and $p={followup['cases'][3]['p_IUT']:.3f}$. "
            "Table~\\ref{tab:gap-followup} reports all six cases without selection.")


def followup_table(followup):
    labels=['Primary','Six lags','Poor-man components','Pre-pandemic endpoints','Short bandwidth','Long bandwidth']
    lines=[f"{label} & ${r['p_IUT']:.3f}$ & $[{r['ellipse95_low']:.2f},{r['ellipse95_high']:.2f}]$ \\\\" for label,r in zip(labels,followup['cases'])]
    return r"""\begin{table}[htbp]
\centering\small
\caption{Post-estimation twelve-month zero-gap assessment}
\label{tab:gap-followup}
\begin{tabular}{@{}lrl@{}}
\toprule
Specification & Intersection-union $p$ & Joint-ellipse product 95\% bounds \\
\midrule
"""+'\n'.join(lines)+r"""
\bottomrule
\end{tabular}
\par\smallskip\begin{minipage}{.97\textwidth}\footnotesize
The same six designs and ten-basis-point factor units are retained. Nominal levels require valid marginal or joint asymptotic inference. The procedures were recorded after primary inspection and preliminary diagnostic arithmetic; they do not replace the primary product bounds. No confidence claim across all six designs is made.
\end{minipage}
\end{table}"""



def stability_table(stability):
    rows=[row for row in stability['comparisons'] if row['common_hac_bandwidth']==18]
    labels=['Poor-man less median','Earlier period less full']
    lines=[]
    for label,row in zip(labels,rows):
        image=row['joint_ellipse95_image']
        lines.append(f"{label} & ${row['difference_right_minus_left']:.2f}$ & $[{image['low']:.2f},{image['high']:.2f}]$ & ${image['minimum_equivalence_margin_infimum']:.2f}$" + " " + chr(92)*2)
    return r"""\begin{table}[htbp]
\centering\small
\caption{Joint contrasts of the twelve-month adjustment gap}
\label{tab:joint-stability}
\begin{tabular}{@{}lrrr@{}}
\toprule
Comparison & Difference & Joint-set 95\% bounds & Margin infimum \\
\midrule
"""+'\n'.join(lines)+r"""
\bottomrule
\end{tabular}
\par\smallskip\begin{minipage}{.97\textwidth}\footnotesize
Units are percentage log-change points per ten-basis-point factor contribution. Each interval projects its own four-coordinate ellipsoid, with cross-model covariance and common calendar bandwidth 18; no coverage claim across both comparisons is made. The margin infimum is the smallest symmetric tolerance that could contain the interval, not a chosen equivalence margin.
\end{minipage}
\end{table}"""


def rotation_figure(rotation):
    import math
    import numpy as np
    endpoints=rotation['endpoint_limits']
    angles=np.linspace(endpoints[0]['angle_radians'],endpoints[1]['angle_radians'],61)
    d=np.array([rotation['basis'][k] for k in ['b_rate','b_orthogonal','gamma']])
    covariance=np.array(rotation['basis']['joint_coefficient_covariance'])
    critical=rotation['basis']['joint_critical']
    lines=[]
    for key,title in [('beta_m','Policy contrast'),('delta','Adjustment gap')]:
        values=[]
        for angle in angles:
            t=math.tan(angle)
            v=np.array([1.,-t,0.]) if key=='beta_m' else np.array([-1.,t,1.])
            point=float(v@d); width=critical*math.sqrt(float(v@covariance@v))
            values.append((math.degrees(angle),point,point-width,point+width))
        coords=lambda column:' '.join(f'({row[0]:.8g},{row[column]:.8g})' for row in values)
        lines += [r'\nextgroupplot[title={'+title+r'},ylabel={Percentage log points}]',
            r'\addplot[name path=lo,draw=none,forget plot] coordinates {'+coords(2)+'};',
            r'\addplot[name path=hi,draw=none,forget plot] coordinates {'+coords(3)+'};',
            r'\addplot[policyblue!15,draw=none,forget plot] fill between[of=lo and hi];',
            r'\addplot[policyblue,very thick] coordinates {'+coords(1)+'};',
            r'\addplot[gray,thin,forget plot] coordinates {(0,0)(80.8,0)};',
            r'\addplot[newsorange,only marks,mark=*,mark size=2pt,forget plot] coordinates {('+f"{rotation['source']['median_radians']*180/math.pi:.8g},{rotation['median'][key]:.8g}"+')};']
    return r"""\begin{figure}[htbp]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 1,horizontal sep=1.25cm},
 width=.46\textwidth,height=5.8cm,axis lines=left,xmin=0,xmax=80.8,
 xtick={0,20,40,60,80},xlabel={Rotation angle, degrees},
 tick label style={font=\small},label style={font=\small},title style={font=\small},clip=true]
"""+'\n'.join(lines)+r"""
\end{groupplot}
\end{tikzpicture}
\caption{Complete admissible rotation assessment. Curves are twelve-month point projections per ten-basis-point rate-factor contribution; orange points identify the author median. Shading projects one joint 95 per cent ellipsoid and simultaneously covers the retained-factor family under its regularity assumptions. The curves include continuous closure limits, not a fitted singular zero-angle model. Factor and sign-boundary estimation uncertainty is not covered.}
\label{fig:rotation}
\end{figure}"""


def refresh():
    summary=json.loads((ROOT/'results/summary.json').read_text())
    source=ROOT/'results/estimates.csv'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=summary['estimates_sha256']:
        raise ValueError('Retained numerical evidence checksum differs')
    with source.open(newline='') as f:
        rows=list(csv.DictReader(f))
    checks=[r for r in rows if not r['case'].startswith('path_')]
    path=[r for r in rows if r['case'].startswith('path_')]
    description=json.loads((ROOT/'results/sample_description.json').read_text())
    if description['source_sha256']['estimates']!=summary['estimates_sha256']:
        raise ValueError('Descriptive sample does not match retained estimates')
    followup=json.loads((ROOT/'results/gap_followup.json').read_text())
    if followup['estimates_sha256']!=summary['estimates_sha256']:
        raise ValueError('Follow-up does not match retained estimates')
    stability=json.loads((ROOT/'results/joint_stability.json').read_text())
    rotation=json.loads((ROOT/'results/rotation_sensitivity.json').read_text())
    blocks={'STABILITY_TABLE':stability_table(stability),'ROTATION_FIGURE':rotation_figure(rotation),'FOLLOWUP_SUMMARY':followup_summary(followup),'FOLLOWUP_TABLE':followup_table(followup),
            'VARIATION_TABLE':table_variation(description),
            'PRIMARY_TABLE':table_primary(checks[0]),'PATH_FIGURE':path_figure(path),
            'SENSITIVITY_TABLE':sensitivity_table(checks)}
    text=TEX.read_text()
    for key,value in blocks.items():
        pattern=rf'% BEGIN {key}\n.*?% END {key}'
        text,count=re.subn(pattern,lambda _:f'% BEGIN {key}\n{value}\n% END {key}',text,flags=re.S)
        if count!=1: raise ValueError(f'Expected one numerical block: {key}')
    TEX.write_text(text)


def compile_pdf():
    compiler=shutil.which('xelatex')
    if compiler is None:
        raise SystemExit('XeLaTeX is required for PDF export; the saved source remains usable in a LaTeX editor.')
    temporary=ROOT/'reports/paper_build'
    temporary.mkdir(parents=True,exist_ok=True)
    command=[compiler,'-interaction=nonstopmode','-halt-on-error','-file-line-error',
             '-output-directory',str(temporary),str(TEX)]
    logs=[]
    for _ in range(2):
        result=subprocess.run(command,cwd=TEX.parent,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        logs.append(result.stdout)
        if result.returncode: raise SystemExit(result.stdout[-7000:])
    pdf=temporary/'monetary_policy.pdf'
    final=ROOT/'paper/monetary_policy.pdf'
    shutil.copyfile(pdf,final)
    (temporary/'export_log.txt').write_text('\n'.join(logs))
    report={'source_sha256':hashlib.sha256(TEX.read_bytes()).hexdigest(),
            'pdf_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),
            'compiler':subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
            'source':TEX.relative_to(ROOT).as_posix(),'pdf':final.relative_to(ROOT).as_posix()}
    (ROOT/'reports/paper_export.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compile',action='store_true',help='Export a matching PDF with existing XeLaTeX')
    args=parser.parse_args()
    refresh()
    if args.compile: compile_pdf()
