"""Render the public equipment snapshot into static HTML (no database access)."""
from pathlib import Path
import json
from html import escape
from PIL import Image
from collections import defaultdict
root = Path(__file__).resolve().parents[1]
data = json.loads((root / 'assets/equipment.json').read_text())
e = escape
items = data['items']
def photo(x):
    p = x.get('photo')
    if not p:
        return ''
    with Image.open(root / p['src']) as image:
        width, height = image.size
    caption = e(p.get('caption', '제품 참고 이미지'))
    source = f' <a href="{e(p["source"])}" target="_blank" rel="noopener noreferrer">출처 ↗</a>' if p.get('source') else ''
    return f'<figure class="equipment-photo"><a href="{e(p["src"])}" target="_blank" rel="noopener" aria-label="{e(x["name"])} 참고 이미지 크게 보기"><img src="{e(p["src"])}" alt="{e(x["name"])} 제품 참고 이미지" loading="lazy" decoding="async" width="{width}" height="{height}" /></a><figcaption>{caption}{source}</figcaption></figure>'
audio = [x for x in items if x['domain'] == 'audio']
video = [x for x in items if x['domain'] == 'video']
groups = defaultdict(list)
for x in audio:
    groups[x['category']].append(x)
order = ['콘솔', '메인 스피커', '서브우퍼', '모니터 스피커', '무선 시스템', '무선 인이어 모니터', '퍼스널 모니터', '마이크 스탠드']
assert set(order) == set(groups), 'Review new categories before publishing'
parts = ['''    <!-- equipment:start -->
    <section class="section equipment" id="equipment" aria-labelledby="equipmentTitle">
      <div class="section-head">
        <div class="section-kicker">05 / OUR EQUIPMENT</div>
        <h2 id="equipmentTitle">현장을 완성하는<br />보유 장비.</h2>
        <p>공연의 규모와 공간에 맞춰 음향 시스템과 LED 화면을 구성합니다.</p>
      </div>
      <div class="equipment-topline">
        <p>음향 <strong>35종</strong><span aria-hidden="true"> / </span>LED 영상 <strong>4종</strong></p>
        <a href="#contact">장비 구성 문의 <span aria-hidden="true">↗</span></a>
      </div>
      <div class="equipment-heading"><span>SOUND SYSTEM</span><h3>음향 장비</h3><p>분류를 열어 장비명과 보유 수량을 확인하세요.</p></div>
      <div class="equipment-audio">''']
for cat in order:
    parts.append(f'        <details class="equipment-group"{" open" if cat == "콘솔" else ""}><summary><span>{e(cat)}</span><small>{len(groups[cat])}종</small></summary><ul class="equipment-list">')
    for x in groups[cat]:
        parts.append(f'          <li class="equipment-item{' has-photo' if x.get('photo') else ''}">{photo(x)}<span>{e(x["name"])}</span><strong>{x["quantity"]}<small> EA</small></strong></li>')
    parts.append('        </ul></details>')
parts.append('''      </div>
      <div class="equipment-heading equipment-video-heading"><span>LED DISPLAY</span><h3>LED 영상 장비</h3><p>패널 규격과 해상도에 맞춘 화면 구성.</p></div>
      <div class="equipment-video">''')
for x in video:
    led = x['led']
    parts.append(f'''        <article class="equipment-led">
          {photo(x)}
          <span class="equipment-led-tag">{e(x['category'])}</span>
          <h4>{e(x['name'])}</h4>
          <p>{e(x['model'])}</p>
          <dl><div><dt>패널 크기</dt><dd>{led['widthMm']} × {led['heightMm']} mm</dd></div><div><dt>패널 해상도</dt><dd>{led['pixelsWide']} × {led['pixelsHigh']} px</dd></div><div><dt>보유 수량</dt><dd><strong>{x['quantity']}</strong> 장</dd></div></dl>
        </article>''')
parts.append(f'''      </div>
      <p class="equipment-note">{e(data['asOf'])} 보유목록 기준 · 표기 수량은 보유 수량이며, 행사일의 사용 가능 수량과 구성은 문의 시 안내드립니다.</p>
      <p class="equipment-note">사진은 제품·시리즈 참고 이미지이며 실제 보유품의 외관·세부 사양과 다를 수 있습니다. 사진을 누르면 크게 볼 수 있습니다.</p>
    </section>
    <!-- equipment:end -->''')
section = '\n'.join(parts).replace('<strong>35종</strong>', f'<strong>{len(audio)}종</strong>').replace('<strong>4종</strong>', f'<strong>{len(video)}종</strong>')
path = root / 'index.html'
html = path.read_text()
if '<!-- equipment:start -->' in html:
    start = html.index('    <!-- equipment:start -->')
    end = html.index('    <!-- equipment:end -->') + len('    <!-- equipment:end -->')
    html = html[:start] + section + html[end:]
else:
    html = html.replace('    <section class="section public-section">', section + '\n\n    <section class="section public-section">')
    html = html.replace('<a href="#production">PRODUCTION</a>', '<a href="#production">PRODUCTION</a>\n      <a href="#equipment">보유 장비</a>')
    html = html.replace('05 / PUBLIC EVENT CAPABILITY', '06 / PUBLIC EVENT CAPABILITY').replace('06 / CONTACT', '07 / CONTACT')
    html = html.replace('</head>', '  <link rel="stylesheet" href="assets/equipment.css" />\n</head>')
path.write_text(html)
print(f'Rendered {len(items)} equipment records')
