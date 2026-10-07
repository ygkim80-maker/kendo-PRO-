"""TOP7 패널(ov) HTML 재생성. 사용: python3 tools/build_top7.py [data.json 경로]
집계: tk 칩의 우승/준우승/3·4위 언급 횟수(누적). 생활체육은 note에만 기재해 제외."""
import json, re, collections

import os, sys
PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data.json')
d = json.load(open(PATH))
panels = {p['id']: p for p in d['panels']}

def count_placements(html):
    if not html: return 0,0,0
    html = re.sub(r'<span class="y[wtr]" data-top="0">.*?</span>', '', html)  # 집계 제외 칩
    champ = len(re.findall(r'(?<!준)우승', html))
    runner = len(re.findall(r'준우승', html))
    third = len(re.findall(r'(?:공동\s*)?3위|4위', html))
    return champ, runner, third

def strip_tags(s):
    return re.sub(r'</?span[^>]*>', '', s).strip()

def highlights(tk_html, n=2):
    spans = re.findall(r'<span class="y[wtr]">(.*?)</span>', tk_html)
    spans = [strip_tags(s) for s in spans if s.strip()]
    champs = [s for s in spans if '우승' in s]
    others = [s for s in spans if '우승' not in s]
    ordered = champs + others
    return ordered[:n]

def fmt_school(school):
    m = re.match(r'^(.*?)\((.*?)\)$', school)
    if m:
        return m.group(1) + ' · ' + m.group(2)
    return school

def is_female(r):
    pn = ''.join(c['html'] for c in r['cells'] if c['class']=='pn_')
    tk = ''.join(c['html'] for c in r['cells'] if c['class']=='' and '"tk"' in c.get('html',''))
    note = ''.join(c['html'] for c in r['cells'] if c['class']=='note')
    text = pn + tk + note
    return '여대 국가대표상비군' in text or '여자' in text or r['name'] in ('조유빈','박나영')

def build(panel_id, section_idxs, exclude=(), only_female=None):
    rows = []
    for si in section_idxs:
        sec = panels[panel_id]['sections'][si]
        for r in sec['rows']:
            if r['name'] in exclude: continue
            if only_female is True and not is_female(r): continue
            if only_female is False and is_female(r): continue
            tk_html = ''.join(c['html'] for c in r['cells'] if c['class']=='' and '"tk"' in c.get('html',''))
            champ, runner, third = count_placements(tk_html)
            rows.append({'name': r['name'], 'school': r.get('school',''), 'champ':champ,'runner':runner,'third':third,'total':champ+runner+third,'tk':tk_html})
    agg = collections.OrderedDict()
    for r in rows:
        k = r['name']
        if k not in agg: agg[k]=dict(r)
        else:
            for f in ['champ','runner','third','total']: agg[k][f]+=r[f]
            agg[k]['tk'] += ' '+r['tk']
            agg[k]['school'] = r['school'] or agg[k]['school']
    return sorted(agg.values(), key=lambda x:(-x['total'],-x['champ'],-x['runner'],x['name']))

def rows_html(entries, fallback='기록 없음'):
    out = []
    for i, e in enumerate(entries):
        rank = i+1
        rcls = 'r1' if rank==1 else 'r2' if rank==2 else 'r3'
        hl = e['hl']
        if len(hl) >= 2:
            ev = f'<strong>{hl[0]}</strong><br/>{hl[1]}'
        elif len(hl) == 1:
            ev = f'<strong>{hl[0]}</strong>'
        else:
            ev = fallback
        out.append(
            f'<div class="t3row">\n<div class="t3rank {rcls}">{rank}</div>\n<div class="t3body">\n'
            f'<div class="t3name">{e["name"]}</div>\n<div class="t3org">{fmt_school(e["school"])}</div>\n'
            f'<div class="t3ev">{ev} <span style="color:var(--text3);font-size:10px;">(누적 우승{e["champ"]}·준우승{e["runner"]}·3위{e["third"]})</span></div>\n'
            f'</div>\n</div>'
        )
    return '\n'.join(out)

# 초등부 top7 (전원 표기 - 기록 유무 무관, 차장님 현장 평가 반영)
elem = build('elem', [0])[:7]
for e in elem: e['hl'] = highlights(e['tk'])

# 중학부 top7
mid = build('mid', [0,1,2])[:7]
for e in mid: e['hl'] = highlights(e['tk'])

# 고등부 top7
hi = build('hi', [0,1,2])[:7]
for e in hi: e['hl'] = highlights(e['tk'])

# 대학부 남자 top7 (2026.06.28 청송 대학 상비군 명단 기준 여자 제외)
univ_m = build('univ', [0,1,2,3,4], only_female=False)[:7]
for e in univ_m: e['hl'] = highlights(e['tk'])

# 대학부 여자 top7 (여대 국가대표상비군 명단 반영, 조유빈/박나영은 별도 서술형 자료 기반 수동 추가)
univ_f = build('univ', [0,1,2,3,4], only_female=True)
manual_f = [
    {'name':'조유빈','school':'용인대','champ':2,'runner':0,'third':0,'total':2,'hl':['2023 회장기 우승','2025 춘계 우승']},
    {'name':'박나영','school':'경북대','champ':1,'runner':0,'third':0,'total':1,'hl':['2023 대통령기 여자대학 우승']},
]
for e in univ_f: e['hl'] = highlights(e['tk'])
univ_f = manual_f + univ_f
univ_f.sort(key=lambda x: (-x['total'], -x['champ'], -x['runner']))
univ_f = univ_f[:7]

# 실업부 남자 top7
real_m = build('real', [0])[:7]
for e in real_m: e['hl'] = highlights(e['tk'])

# 실업부 여자 top7 (only 8 total)
real_f = build('real', [1])[:7]
for e in real_f: e['hl'] = highlights(e['tk'])

blocks = [
    ('t3-elem', '🟦 초등부', elem),
    ('t3-mid', '🟦 중학부', mid),
    ('t3-hi', '🟩 고등부', hi),
    ('t3-univ', '🟥 대학부 남자', univ_m),
    ('t3-univ', '🟥 대학부 여자', univ_f),
    ('t3-real', '🟪 실업부 남자', real_m),
    ('t3-real', '🟪 실업부 여자', real_f),
]

block_html = []
for cls, title, entries in blocks:
    block_html.append(f'<div class="t3block">\n<div class="t3head {cls}">{title}</div>\n{rows_html(entries)}\n</div>')

full_html = '\n'.join(block_html)
full_html = '<div class="t3grid">\n' + full_html + '\n</div>'

# wrap with note
note = ('<div style="margin-top:8px;padding:8px 12px;background:var(--bg2);border:1px solid var(--border);'
        'border-radius:3px;font-size:11px;color:var(--text2);line-height:1.8;">'
        '📌 <strong style="color:var(--gold)">TOP7 산정 기준</strong> · DB에 누적된 전체 대회 기록 중 우승·준우승·3위 언급 횟수를 합산해 순위화(단순 최근 성적 아님)<br/>'
        '· 동률일 경우 우승 → 준우승 횟수 순으로 세분류<br/>'
        '· 초등부는 기록 유무와 관계없이 현장 평가를 반영해 표기, 대학부 여자는 여대 국가대표상비군 명단 등 확인된 선수 기준<br/>'
        '⚠️ 대회 등급(전국대회 vs 지역대회)을 반영하지 않은 단순 횟수 기준입니다'
        '</div>')

full_html = full_html + note

d2 = json.load(open(PATH))
panels2 = {p['id']: p for p in d2['panels']}
panels2['ov']['sections'][0]['html'] = full_html
with open(PATH, 'w') as f:
    json.dump(d2, f, ensure_ascii=False, indent=1)
    f.write('\n')
print('DONE. length:', len(full_html))
