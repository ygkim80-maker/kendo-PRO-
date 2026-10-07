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
    html = re.sub(r'· (?:선봉|2위|3위|중견|5위|부장|주장) [가-힣]+전', '', html)  # 단체전 오더 순서("3위 ○○전")는 입상 아님
    champ = len(re.findall(r'(?<!준)우승', html))
    runner = len(re.findall(r'준우승', html))
    third = len(re.findall(r'(?:공동\s*)?3위|4위', html))
    return champ, runner, third

# 해당 부(部) 기록만 집계: 하위 단계(초·중·고·대학 시절) 기록을 담은 칩은 제외 (차장님 지시: "대학부면 대학기록만")
_ELEM = r'초등|초[1-6](?![가-힣])'
_MID = _ELEM + r'|중학|남중|여중|중[1-3](?![가-힣])'
_HI = _MID + r'|고등|남고|여고|고[1-3](?![가-힣])|청소년'
LOWER = {'elem': None, 'mid': _ELEM, 'hi': _MID, 'univ': _HI, 'real': _HI + r'|대학'}

def drop_lower(tk_html, panel_id):
    pat = LOWER.get(panel_id)
    if not pat: return tk_html
    return re.sub(r'<span class="y[wtr]"[^>]*>(?:(?!</span>).)*?(?:%s)(?:(?!</span>).)*?</span>' % pat, '', tk_html)

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
            tk_html = drop_lower(''.join(c['html'] for c in r['cells'] if c['class']=='' and '"tk"' in c.get('html','')), panel_id)
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
        '📌 <strong style="color:var(--gold)">TOP7 산정 기준</strong> · 해당 부 기록만 누적 집계(대학부는 대학 기록만, 초·중·고 시절 기록 제외) · 우승·준우승·개인전 3위 횟수 합산(최근 성적만 보는 것 아님)<br/>'
        '· 학년별 부문(초등부 제외)·2부·동아리부 성적과 단체전 3위는 집계 제외<br/>'
        '· 동률일 경우 우승 → 준우승 횟수 순으로 세분류<br/>'
        '· 초등부는 기록 유무와 관계없이 현장 평가를 반영해 표기, 대학부 여자는 여대 국가대표상비군 명단 등 확인된 선수 기준<br/>'
        '⚠️ 대회 등급(전국대회 vs 지역대회)을 반영하지 않은 단순 횟수 기준입니다'
        '</div>')

full_html = full_html + note


# ===== 홈 추가 섹션: 관심선수 / 국대 유망주 =====
def cell_text(r): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', ' '.join(c['html'] for c in r['cells']))).strip()

def national_names():
    names = set()
    for si in range(3):  # 19WKC 남·여 국가대표, 2026 AOKC 대표팀
        for r in panels['natl']['sections'][si]['rows']:
            names.add(strip_tags(r['cells'][0]['html']).split()[0])
    return names

def tags_of(r):
    return [strip_tags(t) for t in re.findall(r'<span class="tag [^"]*">(.*?)</span>', r['cells'][0]['html'])]

def short_chip(s):
    s = re.sub(r' · (?:선봉|2위|3위|중견|5위|부장|주장) .*$', '', s)
    s = re.sub(r'\((?:[^()]*상대[^()]*|[^()]*다득점[^()]*)\)', '', s)
    return s.replace('전국대학검도대회 ', '').replace('남자1부 ', '').strip()

def simple_block(cls, title, items):
    rows = []
    for name, school, line in items:
        rows.append(
            '<div class="t3row">\n<div class="t3rank r3">★</div>\n<div class="t3body">\n'
            f'<div class="t3name">{name}</div>\n<div class="t3org">{fmt_school(school)}</div>\n'
            f'<div class="t3ev">{line}</div>\n</div>\n</div>')
    return f'<div class="t3block">\n<div class="t3head {cls}">{title} ({len(items)}명)</div>\n' + '\n'.join(rows) + '\n</div>'

ORDER = ['elem', 'mid', 'hi', 'univ', 'real']
def first_rows_by_name():
    """이름별 대표 행(tk 칩이 있는 non-natl 행 중 가장 앞 행)"""
    out = collections.OrderedDict()
    for pid in ORDER:
        for sec in panels[pid]['sections']:
            for r in sec.get('rows', []):
                if not any('"tk"' in c.get('html', '') for c in r['cells']): continue
                out.setdefault(r['name'], (pid, r))
    return out

rows_by_name = first_rows_by_name()

# 관심선수: 이름 셀에 '관심선수' 태그가 붙은 선수
fav_items = []
for name, (pid, r) in rows_by_name.items():
    tg = tags_of(r)
    if '관심선수' not in tg: continue
    tk_html = ''.join(c['html'] for c in r['cells'] if '"tk"' in c.get('html', ''))
    hl = [short_chip(x) for x in highlights(re.sub(r'<span class="y[wtr]" data-top="0">.*?</span>', '', tk_html), 2)]
    tagline = ' · '.join(t for t in tg if t != '관심선수')
    line = '<br/>'.join(x for x in ['<strong>' + ' · '.join(hl[:1]) + '</strong>' if hl else '', hl[1] if len(hl) > 1 else '', ('<span style="color:var(--text3)">' + tagline + '</span>') if tagline else ''] if x)
    fav_items.append((pid, name, r.get('school', ''), line or '기록 확인 중'))
fav_items.sort(key=lambda x: (ORDER.index(x[0]), x[1]))
fav_html = '<div class="t3grid">\n' + simple_block('t3-real', '⭐ 관심선수', [(n, sc, ln) for _, n, sc, ln in fav_items]) + '\n</div>'

# 국대 유망주: 국가대표 상비군(대학 10월 선발 / 2026 청소년대표 상비군) 중 아직 국가대표 명단에 없는 현역
nat = national_names()
prospects = {'univ': [], 'hi': []}
for name, (pid, r) in rows_by_name.items():
    if name in nat: continue
    txt = cell_text(r)
    tg = tags_of(r)
    if pid == 'univ' and '대학 국가대표 상비군' in tg:
        extra = [t for t in tg if t in ('상비군 2회 선발',) or t.startswith('중고 상비군')]
        sel = ' · '.join(extra) if extra else '2026.10 대학 국가대표 상비군 선발'
        prospects['univ'].append((name, r.get('school', ''), '2026.10 대학 국가대표 상비군' + ((' · ' + sel) if extra else '')))
    elif pid == 'hi' and re.search(r'2026[^가-힣]{0,3}(청소년대표|상비군)|2026 상비군|2026 청소년대표', txt):
        yrs = '2년 연속(2025·2026)' if re.search(r'2년\s?연속|2025·2026', txt) else '2026'
        prospects['hi'].append((name, r.get('school', ''), f'청소년대표 상비군 {yrs}'))
for k in prospects: prospects[k].sort(key=lambda x: ('2년' not in x[2], x[0]))
pro_html = '<div class="t3grid">\n' + '\n'.join(
    [simple_block('t3-univ', '🟥 대학 국가대표 상비군', prospects['univ']),
     simple_block('t3-hi', '🟩 고등 청소년대표 상비군', prospects['hi'])]) + '\n</div>' + (
    '<div style="margin-top:8px;padding:8px 12px;background:var(--bg2);border:1px solid var(--border);border-radius:3px;font-size:11px;color:var(--text2);line-height:1.8;">'
    '📌 <strong style="color:var(--gold)">국대 유망주 기준</strong> · 국가대표 상비군(대학 2026.10 선발, 고등 2026 청소년대표 상비군)에 선발됐으나 국가대표 명단(19WKC·AOKC)에는 아직 없는 현역 선수'
    '</div>')

d2 = json.load(open(PATH))
panels2 = {p['id']: p for p in d2['panels']}
panels2['ov']['sections'][0]['html'] = full_html
ov_secs = panels2['ov']['sections']
for i, (heading, html) in enumerate([('관심선수', fav_html), ('국대 유망주', pro_html)], start=1):
    sec = {'type': 'raw', 'badge_cls': None, 'badge_text': None, 'heading': heading, 'html': html}
    if len(ov_secs) > i: ov_secs[i] = sec
    else: ov_secs.append(sec)
with open(PATH, 'w') as f:
    json.dump(d2, f, ensure_ascii=False, indent=1)
    f.write('\n')
print('DONE. length:', len(full_html))
