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


def path_figure(path):
    def coordinates(key):
        return ' '.join(f"({r['horizon']},{float(r[key]):.10g})" for r in path)
    plots=[]
    for key,name,colour in [('beta_m','policy','policyblue'),('gamma','rate','newsorange')]:
        plots += [f'\\addplot[name path={name}lo,draw=none,forget plot] coordinates {{{coordinates(key+"_low")}}};',
                  f'\\addplot[name path={name}hi,draw=none,forget plot] coordinates {{{coordinates(key+"_high")}}};',
                  f'\\addplot[{colour}!15,draw=none,forget plot] fill between[of={name}lo and {name}hi];',
                  f'\\addplot[{colour},very thick] coordinates {{{coordinates(key)}}};',
                  '\\addlegendentry{'+('Policy component' if key=='beta_m' else 'Recomposed surprise')+'}']
    return r'''\begin{figure}[htbp]
\centering
\begin{tikzpicture}
\begin{axis}[width=.96\textwidth,height=7.1cm,
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
\caption{Matched response paths. Coefficients are percentage log-change points per ten-basis-point factor contribution. Shading gives 95 per cent pointwise normal HAC intervals, not simultaneous bands. All horizons use 296 common origins, January 2000--August 2024; the primary twelve-month estimate uses the longer 308-origin sample.}
\label{fig:path}
\end{figure}'''


def sensitivity_figure(checks):
    labels=['Primary','Six lags','Poor-man components','Pre-pandemic endpoints','Short bandwidth','Long bandwidth']
    plots=[]
    for i,row in enumerate(checks):
        lo,hi,point=(float(row[k]) for k in ['delta_product_low','delta_product_high','delta'])
        plots += [f'\\addplot[policyblue,thick,forget plot] coordinates {{({lo:.10g},{i})({hi:.10g},{i})}};',
                  f'\\addplot[policyblue,only marks,mark=*,mark size=2pt,forget plot] coordinates {{({point:.10g},{i})}};']
    return r'''\begin{figure}[htbp]
\centering
\begin{tikzpicture}
\begin{axis}[width=.85\textwidth,height=6.7cm,
 axis lines=left,y dir=reverse,ymin=-.4,ymax=5.4,ytick={0,1,2,3,4,5},
 yticklabels={'''+','.join(labels)+r'''},
 xlabel={Adjustment gap: percentage log points},
 tick label style={font=\small},label style={font=\small},clip=true]
'''+ '\n'.join(plots)+r'''
\addplot[gray,thin,forget plot] coordinates {(0,-.4)(0,5.4)};
\end{axis}
\end{tikzpicture}
\caption{Declared twelve-month adjustment-gap checks. Points show the recomposed-rate coefficient less the policy-component coefficient per ten-basis-point factor contribution. Lines are the conservative 95 per cent product intervals. All samples have 308 origins except the pre-pandemic check, with 228. Every interval includes zero.}
\label{fig:sensitivity}
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


def refresh():
    summary=json.loads((ROOT/'results/summary.json').read_text())
    source=ROOT/'results/estimates.csv'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=summary['estimates_sha256']:
        raise ValueError('Retained numerical evidence checksum differs')
    with source.open(newline='') as f:
        rows=list(csv.DictReader(f))
    checks=[r for r in rows if not r['case'].startswith('path_')]
    path=[r for r in rows if r['case'].startswith('path_')]
    blocks={'PRIMARY_TABLE':table_primary(checks[0]),'PATH_FIGURE':path_figure(path),
            'SENSITIVITY_FIGURE':sensitivity_figure(checks),'SENSITIVITY_TABLE':sensitivity_table(checks)}
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
