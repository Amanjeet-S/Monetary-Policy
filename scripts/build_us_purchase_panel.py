"""Retain observed US policy inputs and monthly household quantity measures."""
from __future__ import annotations
import argparse, csv, datetime, gzip, hashlib, io, json
from pathlib import Path
import numpy as np
import xlrd

ROOT=Path(__file__).resolve().parents[1]
SERIES={'durable':'DDURRA3M086SBEA','nondurable':'DNDGRA3M086SBEA',
        'services':'DSERRA3M086SBEA','real_disposable_income':'DSPIC96',
        'pce_price':'PCEPI','funds_rate':'FEDFUNDS','daily_funds_rate':'DFF'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def month_number(s):
    y,m=map(int,s[:7].split('-'));return 12*y+m-1
def month_name(n):
    y,m=divmod(n,12);return f'{y:04d}-{m+1:02d}'
def build(root):
    specification=json.loads((root/'docs/us_purchase_specification.json').read_text())
    raw=root/specification['source_snapshot']
    if digest(raw/'manifest.json')!=specification['snapshot_manifest_sha256']:raise ValueError('Source manifest changed')
    manifest=json.loads((raw/'manifest.json').read_text())
    for r in manifest['sources']:
        p=raw/r['file']
        if digest(p)!=r.get('compressed_sha256',r.get('sha256')):raise ValueError('Source bytes changed')
        if p.suffix=='.gz' and hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()!=r['original_sha256']:raise ValueError('Decompressed source bytes changed')
    series={}
    for name,ident in SERIES.items():
        rows=list(csv.DictReader(io.StringIO(gzip.decompress((raw/f'{ident}.csv.gz').read_bytes()).decode('utf-8-sig'))))
        lookup={r['observation_date']:float(r[ident]) if r[ident] not in ('','.','NA') else np.nan for r in rows}
        if len(lookup)!=len(rows):raise ValueError('Duplicate source dates')
        series[name]=lookup
    book=xlrd.open_workbook(raw/'rr_author_original.xls')
    s=book.sheet_by_name('DATA BY MEETING');headers=s.row_values(0)
    source=[];missing=[]
    for i in range(1,s.nrows):
        row=s.row_values(i)
        date=datetime.datetime.strptime(f'{int(row[0]):06d}','%m%d%y').date()
        if not all(isinstance(v,(float,int)) and np.isfinite(v) for v in row[1:21]):
            missing.append(date.isoformat());continue
        f=[1.]+row[2:20]
        daily=series['daily_funds_rate']
        before=[daily[(date-datetime.timedelta(days=j)).isoformat()] for j in range(1,8)]
        after=[daily[(date+datetime.timedelta(days=j)).isoformat()] for j in range(1,8)]
        if not np.isfinite(before+after).all():raise ValueError('Incomplete financial window')
        source.append({'date':date.isoformat(),'month':date.isoformat()[:7],
                       'raw_intention':row[1],'supplied_innovation':row[20],
                       'financial_change':float(np.mean(after)-np.mean(before)),
                       **dict(zip(['intercept']+headers[2:20],f))})
    f=np.array([[r[k] for k in specification['conditioning']['source_forecasts']] for r in source])
    t=np.array([r['raw_intention'] for r in source]);theta=np.linalg.lstsq(f,t,rcond=None)[0]
    z=t-f@theta
    replay=float(np.max(abs(z-np.array([r['supplied_innovation'] for r in source]))))
    if replay>1e-10 or len(source)!=263 or np.linalg.matrix_rank(f)!=19:raise ValueError('Original policy source replay failed')
    for r,v in zip(source,z):r['innovation']=float(v)
    m=book.sheet_by_name('DATA BY MONTH');col=m.row_values(0).index('DTARG')
    intentions={xlrd.xldate.xldate_as_datetime(m.cell_value(i,0),book.datemode).date().isoformat():float(m.cell_value(i,col)) for i in range(1,m.nrows)}
    # Only months covered by the original narrative record are observed intentions.
    intentions={k:v for k,v in intentions.items() if k>='1969-01-01'}
    months=sorted(series['durable'])
    panel=[]
    for d in months:
        panel.append({'month':d[:7],**{k:v.get(d,np.nan) for k,v in series.items() if k!='daily_funds_rate'},
                      'raw_monthly_intention':intentions.get(d,np.nan)})
    out=root/'data/processed';out.mkdir(exist_ok=True)
    def write(name,rows):
        with (out/name).open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader()
            for r in rows:writer.writerow({k:'' if isinstance(v,float) and not np.isfinite(v) else v for k,v in r.items()})
    write('us_purchase_monthly.csv',panel);write('us_policy_events.csv',source)
    report={'author':'Amanjeet Singh','complete_source_events':len(source),
            'undefined_source_dates':missing,'source_purge_rank':19,'source_purge_columns':specification['conditioning']['source_forecasts'],
            'source_purge_coefficients':theta.tolist(),'source_purge_replay_max_abs_error':replay,
            'monthly_quantity_rows':len(panel),'first_quantity_month':panel[0]['month'],'last_quantity_month':panel[-1]['month'],
            'first_observed_raw_intention_month':'1969-01','early_policy_placeholders_retained_as_observations':False,
            'specification_sha256':digest(root/'docs/us_purchase_specification.json'),
            'monthly_panel_sha256':digest(out/'us_purchase_monthly.csv'),'event_panel_sha256':digest(out/'us_policy_events.csv'),
            'spending_response_fits_performed':False}
    (root/'results/us_source_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    print(json.dumps(build(p.parse_args().root),indent=2))
