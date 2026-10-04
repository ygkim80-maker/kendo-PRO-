"""대회 결과를 data.json 에 반영하고 검증·TOP7 재생성까지 한 번에 처리.

사용:  python3 tools/apply_results.py spec.json [--dry-run]

spec.json 형식 (두 블록 모두 선택):
{
  "event": "제6회 대한검도회장기 전국대학검도대회 남자1부",     # 칩 문구 앞에 붙는 대회명(연도 포함 가능)
  "entries": [                                                 # 개별 기록
    {"name":"임동균","school":"제주","cls":"yw","text":"3학년부 개인전 우승 🏆","tag":"회장기 3학년부 우승",
     "replace":"기존 칩에 포함된 문구(있으면 그 칩을 교체)",
     "create":{"panel":"univ","section":0,"note":"신규 등록 시 비고"}}   # 선수 DB에 없을 때만 필요
  ],
  "teams": [                                                   # 단체전 결승 (칩 자동 생성)
    {"stage":"고학년부 단체전 결승", "tag":"회장기 단체전 우승", "replace":"고학년부 단체전 결승",
     "teams":[{"school":"대구대","result":"우승","summary":"2승 1무 2패·득점 4:3 다득점 우승"},
              {"school":"대전대","result":"준우승","summary":"득점 3:4 다득점 패"}],
     "bouts":[["선봉","오윤근","대전대",1,"원유제","대구대",0], ...]}   # [순서, A이름, A학교, A득점, B이름, B학교, B득점]
  ]
}
- school 은 부분일치(제주→제주대). 동명이인/중복 행이면 "ref":["panel",섹션,행] 으로 지정.
- cls: yw(입상·승) / yt(참가·중립) / yr(패).  동일 텍스트 칩은 중복 추가하지 않음.
- 선수를 못 찾고 create 도 없으면 아무것도 쓰지 않고 중단(오타 방지).
"""
import json, re, sys, subprocess, os, copy

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PATH = os.path.join(ROOT, 'data.json')
dry = '--dry-run' in sys.argv
spec = json.load(open(sys.argv[1]))
d = json.load(open(PATH))
panels = {p['id']: p for p in d['panels']}
log = {'added': 0, 'replaced': 0, 'skipped': 0, 'created': []}
errors = []

def get_row(ref):
    return panels[ref[0]]['sections'][ref[1]]['rows'][ref[2]]

def resolve(e):
    if e.get('ref'):
        return e['ref']
    hits = [p for p in d['players_index'] if p['name'] == e['name'] and (not e.get('school') or e['school'] in p['school'])]
    if len(hits) == 1:
        return hits[0]['ref']
    if len(hits) > 1:
        errors.append(f"중복: {e['name']} {[(h['school'], h['ref']) for h in hits]} → ref 지정 필요")
        return None
    c = e.get('create')
    if c:
        sec = panels[c['panel']]['sections'][c['section']]
        school = e.get('school_full', e.get('school', ''))
        row = {'name': e['name'], 'school': school, 'cells': [
            {'class': 'pn_', 'html': e['name']}, {'class': 'sch', 'html': school},
            {'class': '', 'html': '<div class="tk"></div>'}, {'class': 'note', 'html': c.get('note', '')}]}
        sec['rows'].append(row)
        label = next((p['section'] for p in d['players_index'] if p['ref'][:2] == [c['panel'], c['section']]), '')
        ref = [c['panel'], c['section'], len(sec['rows']) - 1]
        d['players_index'].append({'name': e['name'], 'school': school, 'panel': c['panel'], 'section': label, 'ref': ref})
        log['created'].append(f"{e['name']}({school})")
        return ref
    errors.append(f"선수 없음: {e['name']} / {e.get('school')} (신규면 create 지정)")
    return None

def apply_chip(e, text):
    ref = resolve(e)
    if ref is None: return
    r = get_row(ref)
    ci = next(i for i, c in enumerate(r['cells']) if '"tk"' in c.get('html', ''))
    html = r['cells'][ci]['html']
    chip = f'<span class="{e.get("cls","yw")}">{text}</span>'
    if chip in html:
        log['skipped'] += 1
    else:
        key = e.get('replace')
        pat = re.compile(r'<span class="y[wtr]">[^<]*' + re.escape(key) + r'[^<]*</span>') if key else None
        if pat and pat.search(html):
            html = pat.sub(lambda m: chip, html, count=1); log['replaced'] += 1
        else:
            html = html.replace('</div>', chip + '</div>', 1); log['added'] += 1
        r['cells'][ci]['html'] = html
    tag = e.get('tag')
    pn = r['cells'][0]
    if tag:
        t = f'<span class="tag tw_">{tag}</span>'
        if t not in pn['html']: pn['html'] += ' ' + t
    for rm in ([e['untag']] if e.get('untag') else []):
        pn['html'] = pn['html'].replace(f' <span class="tag tw_">{rm}</span>', '')

ev = spec.get('event', '')
for e in spec.get('entries', []):
    apply_chip(e, (ev + ' ' if ev and not e.get('no_event') else '') + e['text'])

for t in spec.get('teams', []):
    res = {x['school']: x for x in t['teams']}
    for pos, na, sa, pa, nb, sb, pb in t['bouts']:
        for me, sch, mp, op_name, op_sch, op in ((na, sa, pa, nb, sb, pb), (nb, sb, pb, na, sa, pa)):
            team = res[sch]
            vs = res[op_sch]['school']
            out = '무' if mp == op else ('승' if mp > op else '패')
            score = '' if out == '무' else f' {mp}:{op}'
            text = (f"{ev} {t['stage']} {team['result']}({vs} 상대" + (f", {team['summary']}" if team.get('summary') else '') +
                    f") · {pos} {op_name}전{score} {out}")
            e = {'name': me, 'school': sch, 'cls': 'yw', 'replace': t.get('replace', t['stage'])}
            if team['result'] == '우승' and t.get('tag'): e['tag'] = t['tag']
            else:
                if t.get('tag'): e['untag'] = t['tag']
            for k in ('create', 'ref'):
                pass
            apply_chip(e, text)

if errors:
    print('중단(저장 안 함):'); [print(' -', x) for x in errors]; sys.exit(1)

bad = sum(1 for p in d['players_index'] if get_row(p['ref'])['name'] != p['name'])
if bad:
    print(f'players_index 불일치 {bad}건 → 저장 안 함'); sys.exit(1)

def top7_names():
    h = [p for p in json.load(open(PATH))['panels'] if p['id'] == 'ov'][0]['sections'][0]['html']
    out, cur = {}, None
    for m in re.finditer(r'class="t3head[^"]*">([^<]+)<|class="t3name">([^<]+)<', h):
        if m.group(1): cur = m.group(1); out[cur] = []
        else: out[cur].append(m.group(2))
    return out

if dry:
    print('DRY-RUN', {k: v for k, v in log.items()}, '(저장 안 함)'); sys.exit(0)

before = top7_names()
json.dump(d, open(PATH, 'w'), ensure_ascii=False, indent=1); open(PATH, 'a').write('\n')
subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'build_top7.py'), PATH], check=True, stdout=subprocess.DEVNULL)
after = top7_names()
print(f"OK 추가 {log['added']} · 교체 {log['replaced']} · 중복생략 {log['skipped']} · 신규선수 {log['created'] or '없음'} · 선수 {len(d['players_index'])}명 · index 불일치 0")
for k in after:
    if before.get(k) != after[k]:
        inn = [n for n in after[k] if n not in before.get(k, [])]; out = [n for n in before.get(k, []) if n not in after[k]]
        print(f"TOP7 변동 [{k}] 진입 {inn or '-'} / 이탈 {out or '-'} (순위 변경 포함 시 {after[k]})")
