"""중고연맹 상비군 기수별 명단(1992~2023, tools/data/junggo_sanggun_1992_2023.json)을 DB 선수와 대조해
apply_results.py 용 spec 을 만든다. 사용: python3 tools/match_sanggun.py spec.json  →  python3 tools/apply_results.py spec.json
매칭 기준: 이름 + 당시 학교(중·고)가 DB 행(비고 등)에 표기된 경우만(동명이인·나이 혼동 방지). 이름만 같은 경우는 제외."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
import json,re,collections
d=json.load(open(os.path.join(ROOT,'data.json')));P={p['id']:p for p in d['panels']}
recs=json.load(open(os.path.join(ROOT,'tools','data','junggo_sanggun_1992_2023.json')))
def stem(s): return re.sub(r'(상고|여고|여중|여상|예고|공고|농고|고|중)$','',s)
cands=collections.defaultdict(list)
for p in d['players_index']:
    if p['panel'] not in ('elem','mid','hi','univ','real'): continue
    r=P[p['panel']]['sections'][p['ref'][1]]['rows'][p['ref'][2]]
    if not any('"tk"' in c.get('html','') for c in r['cells']): continue
    txt=re.sub(r'<[^>]+>',' ',' '.join(c['html'] for c in r['cells']))
    cands[p['name']].append({'p':p,'txt':txt,'r':r})
people={}   # (name,school)->{'ref','recs','txt'}
order={'elem':0,'mid':1,'hi':2,'univ':3,'real':4}
for rc in recs:
    for c in cands.get(rc['name'],[]):
        sch=rc['school']; st=stem(rc['school'])
        ok = sch in c['txt'] or re.search(re.escape(st)+r'[가-힣]{0,2}(고|중)(?![가-힣])',c['txt'])
        # 팀명(…시청 등)의 일부만 겹치는 경우 제외: 학교 표기 자체가 있어야 함
        if not ok: continue
        key=(rc['name'],c['p']['school'])
        e=people.setdefault(key,{'ref':c['p']['ref'],'panel':c['p']['panel'],'recs':set(),'cnt':0})
        e['recs'].add((rc['year'],rc['kind'],rc['ki'],rc['school']))
# 같은 사람이 여러 행이면 첫 행만(이름 중복 키 정리)
byname=collections.defaultdict(list)
for (n,s),e in people.items(): byname[n].append((s,e))
final=[]
for n,lst in byname.items():
    lst.sort(key=lambda x:(order[x[1]['panel']],x[1]['ref'][1],x[1]['ref'][2]))
    s,e=lst[0]
    if len(lst)>1: print('중복행 → 첫 행만:',n,[(x[0],x[1]['panel'],x[1]['ref']) for x in lst])
    final.append((n,s,e))
ents=[]
for n,s,e in sorted(final):
    rs=sorted(e['recs'])
    k=len({(y,kd,ki) for y,kd,ki,_ in rs})
    txt='중고연맹 상비군 %d회 선발: '%k+' · '.join(f'{y}년도 {kd}{ki}기({sc})' for y,kd,ki,sc in rs)
    ents.append({'name':n,'school':s,'ref':e['ref'],'cls':'yt','no_event':True,'text':txt,'tag':f'중고 상비군 {k}회 선발'})
    print(n,s,e['panel'],k,[f'{y}{kd}{ki}' for y,kd,ki,_ in rs])
json.dump({'entries':ents},open(sys.argv[1] if len(sys.argv)>1 else os.path.join(ROOT,'sanggun_spec.json'),'w'),ensure_ascii=False)
print(len(ents))
