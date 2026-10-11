"""Compare typed independent R quantities with the retained US study."""
from pathlib import Path
import argparse,csv,json,math

FAMILIES=['primary','sensitivity','single_event_deletions']

def flatten(value,path):
    if isinstance(value,dict):
        result={}
        for key,item in value.items():result.update(flatten(item,path+'.'+key))
        return result
    if isinstance(value,list):
        result={}
        for index,item in enumerate(value):result.update(flatten(item,path+'.'+str(index)))
        return result
    if value is None:return {path:('null',None)}
    if isinstance(value,bool):return {path:('logical',value)}
    if isinstance(value,(int,float)):return {path:('number',value)}
    if isinstance(value,str):return {path:('string',value)}
    raise ValueError(f'Unsupported retained type:{path}')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('retained_json',type=Path);parser.add_argument('r_csv',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--diagnostics-json',type=Path);args=parser.parse_args()
    retained=json.loads(args.retained_json.read_text());expected={}
    for family in FAMILIES:expected.update(flatten(retained[family],family))
    diagnostic_path=args.diagnostics_json or args.retained_json.with_name('us_purchase_diagnostics.json')
    diagnostics=json.loads(diagnostic_path.read_text())
    for family in ['crossed_checks','sample_contrast']:
        expected.update(flatten(diagnostics[family],'diagnostics.'+family))
    with args.r_csv.open(newline='') as f:rows=list(csv.DictReader(f))
    actual={row['quantity']:row for row in rows}
    if len(actual)!=len(rows):raise ValueError('Repeated independent quantity')
    if set(actual)!=set(expected):
        raise ValueError(f'Independent quantity mismatch: missing {sorted(set(expected)-set(actual))[:15]}; extra {sorted(set(actual)-set(expected))[:15]}')
    count=0;maximum=0.;maximum_key=None
    for key,(kind,value) in expected.items():
        row=actual[key]
        if row['type']!=kind:raise ValueError(f'Independent type differs:{key}')
        if kind=='number':
            observed=float(row['value'])
            if not math.isfinite(observed) or not math.isclose(observed,value,rel_tol=1e-9,abs_tol=1e-10):raise ValueError(f'Independent numeric difference:{key}: {observed} != {value}')
            difference=abs(observed-value);count+=1
            if difference>maximum:maximum=difference;maximum_key=key
        elif kind=='logical':
            if row['value'] not in ['true','false'] or (row['value']=='true')!=value:raise ValueError(f'Independent membership differs:{key}')
        elif kind=='string':
            if row['value']!=value:raise ValueError(f'Independent string/topology differs:{key}')
        elif kind=='null' and row['value']!='':raise ValueError(f'Independent unbounded endpoint differs:{key}')
    source_file=Path(str(args.r_csv)+'.source_checks.csv')
    with source_file.open(newline='') as f:source={r['quantity']:float(r['value']) for r in csv.DictReader(f)}
    if source['source_purge_rank']!=19 or source['complete_source_events']!=263 or source['primary_events']!=238 or source['prehistory_guard']!=1:
        raise ValueError('Independent source/sample guard failed')
    if source['source_purge_replay_max_abs_error']>1e-10 or source['processed_innovation_max_abs_error']>1e-10:
        raise ValueError('Independent source purge differs')
    if (source['next_full_months_start'],source['next_full_months_end'])!=(1,36):raise ValueError('Independent outcome timing differs')
    report={'independent_language':'R','retained_status':retained['status'],
            'matched_quantities':len(expected),'numeric_comparisons':count,
            'max_absolute_difference':maximum,'max_difference_quantity':maximum_key,
            'all_topologies_and_memberships_match':True,'all_declared_cases_and_deletions_match':True,
            'recorded_crossed_checks_and_joint_contrast_match':True,
            'source_and_prehistory_checks':source,'passed':True}
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
