"""Compare standard-R reconstructions with the retained future-policy record."""
from pathlib import Path
import argparse,csv,json,math

FAMILIES=['primary','profiles','sensitivity','predetermined','single_origin_deletions']

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
    parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    retained=json.loads(args.retained_json.read_text());expected={}
    for family in FAMILIES:expected.update(flatten(retained[family],family))
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
        elif kind=='null':
            if row['value']!='':raise ValueError(f'Independent unbounded endpoint differs:{key}')
    report={'independent_language':'R','retained_status':retained['status'],
            'matched_quantities':len(expected),'numeric_comparisons':count,
            'max_absolute_difference':maximum,'max_difference_quantity':maximum_key,
            'all_topologies_and_memberships_match':True,'all_declared_cases_and_deletions_match':True,
            'passed':True}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
