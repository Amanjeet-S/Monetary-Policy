"""Export the existing standalone manuscript without changing its source."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEX=ROOT/"paper/monetary_policy.tex"

def compile_pdf():
    compiler=shutil.which('xelatex')
    if compiler is None:
        raise SystemExit('XeLaTeX is required for PDF export; the saved source remains usable in a LaTeX editor.')
    temporary=ROOT/'reports/paper_build'
    temporary.mkdir(parents=True,exist_ok=True)
    command=[compiler,'-interaction=nonstopmode','-halt-on-error','-file-line-error',
             '-output-directory',str(temporary),str(TEX)]
    logs=[]
    for attempt in range(4):
        result=subprocess.run(command,cwd=TEX.parent,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        logs.append(result.stdout)
        if result.returncode: raise SystemExit(result.stdout[-7000:])
        pending = any(message in result.stdout for message in ['Rerun to get cross-references right', 'There were undefined references', 'Package natbib Warning: Citation'])
        if attempt >= 1 and not pending:
            break
    else:
        raise SystemExit('Cross-references did not stabilise after four compiler passes')
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
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compile',action='store_true',required=True,help='Export a matching PDF from the saved source')
    p.parse_args();compile_pdf()
