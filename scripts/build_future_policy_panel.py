"""Construct the declared German future-policy panel from retained source bytes."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=ROOT/'data/raw/2026-10-11-future-policy'
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def month_number(s):
    y,m=map(int,s[:7].split('-'));return 12*y+m-1

def month_name(n):
    y,m=divmod(n,12);return f'{y:04d}-{m+1:02d}'

def eurostat_series(name,expected):
    d=json.loads((SNAPSHOT/name).read_text())
    for key,code in expected.items():
        if d['dimension'][key]['category']['index']!={code:0}:
            raise ValueError(f'Unexpected source dimension {name}:{key}')
    if d['id'][-1]!='time' or any(v!=1 for v in d['size'][:-1]):
        raise ValueError('Expected one fully filtered time series')
    dates={i:k for k,i in d['dimension']['time']['category']['index'].items()}
    values=d['value']
    if isinstance(values,list):values={str(i):v for i,v in enumerate(values) if v is not None}
    return {dates[int(i)]:float(v) for i,v in values.items() if v is not None}

def cached_factors():
    with ZipFile(SNAPSHOT/'AF_MP_surprises_.xlsx') as archive:
        doc=ET.fromstring(archive.read('xl/worksheets/sheet2.xml'))
    cells={c.attrib['r']:c.find('s:v',NS).text for c in doc.findall('.//s:c',NS)
           if c.find('s:v',NS) is not None}
    rows={};events=[];zeros=[]
    for i in range(3,141):
        y,m=int(cells[f'A{i}']),int(cells[f'B{i}']);month=f'{y:04d}-{m:02d}'
        day=cells.get(f'C{i}');values=[cells.get(f'{column}{i}') for column in 'GHI']
        if day is None:
            if any(v is not None for v in values):raise ValueError('Undated nonempty shock row')
            if month not in ['2015-02','2015-05','2015-08','2015-11']:
                raise ValueError('Unverified empty source month')
            values=[0.,0.,0.];zeros.append(month)
        elif any(v is None for v in values):raise ValueError('Partly missing source event')
        else:
            date=f'{month}-{int(day):02d}'
            events.append({'date':date,'month':month,**dict(zip(['target','delphic','odyssean'],map(float,values)))})
        if month in rows:raise ValueError('Duplicate source month')
        rows[month]=dict(zip(['target','delphic','odyssean'],map(float,values)))
    if len(events)!=134 or len(rows)!=138 or len(zeros)!=4:raise ValueError('Source coverage differs')
    return rows,events

def curve(name):
    with gzip.open(SNAPSHOT/name,'rt',newline='') as f:rows=list(csv.DictReader(f))
    dates=[r['TIME_PERIOD'] for r in rows]
    if dates!=sorted(set(dates)):raise ValueError('Nonunique or unordered curve dates')
    values={r['TIME_PERIOD']:float(r['OBS_VALUE']) for r in rows}
    if not all(math.isfinite(v) for v in values.values()):raise ValueError('Nonfinite curve')
    return values

def prepare():
    manifest=json.loads((SNAPSHOT/'manifest.json').read_text())
    for entry in manifest['sources']:
        b=(SNAPSHOT/entry['file']).read_bytes()
        if hashlib.sha256(b).hexdigest()!=entry['sha256']:raise ValueError('Source hash differs')
        if entry['file'].endswith('.gz') and hashlib.sha256(gzip.decompress(b)).hexdigest()!=entry['uncompressed_sha256']:
            raise ValueError('Compressed source differs from retrieval')
    manufacturing=eurostat_series('eurostat_DE_manufacturing.json',{'geo':'DE','nace_r2':'C','unit':'I21','s_adj':'SCA'})
    industrial=eurostat_series('eurostat_DE_industrial.json',{'geo':'DE','nace_r2':'B-D','unit':'I21','s_adj':'SCA'})
    hicp=eurostat_series('eurostat_DE_hicp_historical.json',{'geo':'DE','coicop':'CP00','unit':'I15'})
    factors,events=cached_factors();one=curve('ecb_yc_1Y.csv.gz');three=curve('ecb_yc_3M.csv.gz')
    if set(one)!=set(three):raise ValueError('Maturity dates differ')
    dates=sorted(one);position={d:i for i,d in enumerate(dates)};benchmarks={};excluded=[];event_rows=[]
    for e in events:
        date=e['date'];at=position.get(date)
        if at is None or at==0:
            excluded.append(date);continue
        prev=dates[at-1];a=one[date]-one[prev];b=three[date]-three[prev]
        benchmarks[e['month']]={'yield_1y_change_pp':a,'yield_3m_change_pp':b}
        event_rows.append({**e,'previous_close':prev,'yield_1y_change_pp':a,'yield_3m_change_pp':b})
    if excluded!=['2004-08-05','2004-09-02']:raise ValueError('Unexpected curve exclusions')
    for month in ['2015-02','2015-05','2015-08','2015-11']:
        benchmarks[month]={'yield_1y_change_pp':0.,'yield_3m_change_pp':0.}
    with (ROOT/'data/processed/monthly_panel.csv').open(newline='') as f:
        old={r['month']:r for r in csv.DictReader(f)}
    rows=[]
    for month in sorted(manufacturing):
        row={'month':month,'manufacturing':manufacturing[month],'industrial':industrial.get(month),'hicp':hicp.get(month),
             'durable':old[month]['durable_index'],'nondurable':old[month]['nondurable_index']}
        row.update({k:factors.get(month,{}).get(k) for k in ['target','delphic','odyssean']})
        row.update({k:benchmarks.get(month,{}).get(k) for k in ['yield_1y_change_pp','yield_3m_change_pp']})
        rows.append(row)
    output=ROOT/'data/processed/future_policy_panel.csv'
    with output.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    with (ROOT/'data/processed/future_policy_events.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(event_rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(event_rows)
    report={'panel_rows':len(rows),'source_events':len(events),'matched_events':len(event_rows),
            'excluded_curve_events':excluded,'verified_zero_months':['2015-02','2015-05','2015-08','2015-11'],
            'panel_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'snapshot_manifest_sha256':hashlib.sha256((SNAPSHOT/'manifest.json').read_bytes()).hexdigest(),
            'no_future_event_or_rate_imputation':True}
    (ROOT/'results/future_policy_panel_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':prepare()
