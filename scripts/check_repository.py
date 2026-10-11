"""Check documented targets, source checksums and the saved paper package."""
from __future__ import annotations
import hashlib,json,re,subprocess
from pathlib import Path
from urllib.parse import unquote,urlsplit
from pypdf import PdfReader
from linear_inference import verify_historical_evidence

ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    names=set(filter(None,subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')))
    targets=names|{p.as_posix() for n in names for p in Path(n).parents}
    failures=[];links=0
    for name in sorted(names):
        path=ROOT/name
        if not path.exists():failures.append('Tracked file missing:'+name);continue
        if path.suffix!='.md':continue
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text()):
            parsed=urlsplit(target.strip('<>'))
            if parsed.scheme or parsed.netloc or not parsed.path:continue
            destination=(path.parent/unquote(parsed.path)).resolve();links+=1
            if not destination.is_relative_to(ROOT) or not destination.exists() or destination.relative_to(ROOT).as_posix() not in targets:
                failures.append('Invalid documented target:'+name+':'+target)
    source_count=0
    for path in sorted((ROOT/'data/raw').glob('*/manifest.json')):
        for entry in json.loads(path.read_text())['sources']:
            source_count+=1
            if digest(path.parent/entry['file'])!=entry['sha256']:failures.append('Source checksum differs:'+entry['file'])
    spec=json.loads((ROOT/'docs/us_purchase_specification.json').read_text())
    verify_historical_evidence(ROOT,spec['original_evidence_preservation'])
    results=json.loads((ROOT/'results/us_purchase_results.json').read_text())
    if digest(ROOT/'docs/us_purchase_specification.json')!=results['specification_sha256']:failures.append('Prospective specification changed')
    follow=json.loads((ROOT/'docs/us_purchase_followup_specification.json').read_text())
    if digest(ROOT/'results/us_purchase_results.json')!=follow['initial_results_sha256']:failures.append('Initial retained results changed')
    verification=json.loads((ROOT/'results/us_purchase_verification.json').read_text())
    if not verification['passed']:failures.append('Independent reconstruction failed')
    manifest=json.loads((ROOT/'paper/manifest.json').read_text())
    for name,key in [('monetary_policy.tex','source_sha256'),('monetary_policy.pdf','pdf_sha256')]:
        if digest(ROOT/'paper'/name)!=manifest[key]:failures.append('Paper package checksum differs:'+name)
    reader=PdfReader(ROOT/'paper/monetary_policy.pdf');meta=reader.metadata
    if len(reader.pages)>20 or len(reader.pages)!=manifest['pages_including_appendices_and_references']:failures.append('Paper page count differs')
    if meta.author!='Amanjeet Singh' or meta.get('/Creator')!='Amanjeet Singh':failures.append('Paper authorship metadata differs')
    if meta.title!=manifest['title']:failures.append('Paper title metadata differs')
    if failures:raise SystemExit('\n'.join(failures))
    print(json.dumps({'documented_targets':links,'source_hashes':source_count,'historical_evidence_preserved':True,'matching_paper_pages':len(reader.pages),'authorship_metadata_verified':True}))
if __name__=='__main__':main()
