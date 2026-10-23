#!/usr/bin/env python3
"""
REVO 住宅地圖產生器

    python3 tools/map/build_map.py

讀 tools/map/map-data.json（住宅範圍圈、地標、捷運線）與 tools/map/towns.json（行政區界，
資料來源：內政部，經 g0v twgeojson 簡化），產生：
  1. src/pages/homes.html 裡 <!-- MAP:START --> 到 <!-- MAP:END --> 之間的地圖區塊
  2. public/assets/map/<區域>-d.svg（桌機）與 <區域>-m.svg（手機），點進區域時才載入

注意：map-data.json 的圓心已經是「偏移過的大概位置」，不是房子的真實座標。
新增住宅時，請用 Google 地圖座標另外算好偏移（120–200 公尺）後再填入，真實座標不要放進這個專案。
跑完再執行 python3 build.py --only=homes。
"""
import html
import json
import math
import os
import re
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = json.load(open(os.path.join(HERE, 'map-data.json'), encoding='utf-8'))
TOWNS = json.load(open(os.path.join(HERE, 'towns.json'), encoding='utf-8'))
PAGE = os.path.join(ROOT, 'src', 'pages', 'homes.html')
OUT_SVG = os.path.join(ROOT, 'public', 'assets', 'map')

RED_C, ORANGE_C = '#B07A64', '#C9965E'
MRT = DATA['mrt_red']
ORANGE = DATA['mrt_orange']
AREAS = ['zuoying', 'qiaotou', 'wandan']
AREA_ZH = {k: v[1] for k, v in DATA['area_names'].items()}
SHORT = {k: v[0] for k, v in DATA['area_names'].items()}
ACTIVE = set(AREA_ZH.values())
RENT_NAMES = {h['name'] for h in DATA['homes'] if h['status'] == 'rent'}


class Proj:
    def __init__(self, clat, clng, half_w_km, W, H):
        self.clat, self.clng, self.W, self.H = clat, clng, W, H
        self.kx = 111.32 * math.cos(math.radians(clat))
        self.ky = 110.57
        self.s = W / (2 * half_w_km)  # px per km

    def xy(self, lat, lng):
        return ((lng - self.clng) * self.kx * self.s + self.W / 2,
                (self.clat - lat) * self.ky * self.s + self.H / 2)


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        x0, y0 = pts[i]
        dd = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / L
        if dd > dmax:
            dmax, idx = dd, i
    if dmax > eps:
        return rdp(pts[:idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def town_paths(P, active, eps):
    out = []
    for t in TOWNS:
        ds = []
        for ring in t['rings']:
            pts = [P.xy(lat, lng) for lng, lat in ring]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if max(xs) < -10 or min(xs) > P.W + 10 or max(ys) < -10 or min(ys) > P.H + 10:
                continue
            h = len(pts) // 2
            pts = rdp(pts[:h + 1], eps)[:-1] + rdp(pts[h:], eps)
            if len(pts) >= 4:
                ds.append('M' + 'L'.join(f'{x:.0f} {y:.0f}' for x, y in pts) + 'Z')
        if ds:
            on = t['name'] in active
            out.append(f'<path d="{"".join(ds)}" fill="{"#E8DCC8" if on else "#F3EEE5"}" '
                       f'stroke="{"#B8A587" if on else "#D9CFC0"}" stroke-width="{1.2 if on else 0.8}" stroke-linejoin="round"/>')
    return ''.join(out)


def text(x, y, s, size, fill='#3B4650', weight=400, anchor='start', serif=False, halo=True, ls=0):
    fam = 'var(--serif)' if serif else 'var(--sans)'
    h = ' stroke="#F7F3EC" stroke-width="3.2" stroke-linejoin="round" paint-order="stroke"' if halo else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" style="font-family:{fam}" font-size="{size:.1f}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}"{h}>{html.escape(s)}</text>')


def line_path(P, pts, color, w, op):
    xy = [P.xy(la, ln) for _, _, la, ln in pts]
    return ('<path d="M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in xy)
            + f'" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" opacity="{op}"/>')


def line_visible(P, pts):
    for a, b in zip(pts, pts[1:]):
        for t in range(11):
            x, y = P.xy(a[2] + (b[2] - a[2]) * t / 10, a[3] + (b[3] - a[3]) * t / 10)
            if 0 <= x <= P.W and 0 <= y <= P.H:
                return True
    return False


def rent_pill(lx, y, nm, fs, anchor, mid=False):
    w_name = len(nm) * fs * 1.18 / (2 if mid else 1)
    pw, ph = fs * 3.6, fs * 1.25
    x = lx + w_name + fs * 0.4 if anchor == 'start' else lx - w_name - fs * 0.4 - pw
    return (f'<rect x="{x:.1f}" y="{y - ph * 0.8:.1f}" width="{pw:.1f}" height="{ph:.1f}" rx="{ph / 2:.1f}" fill="#1F2A33"/>'
            + text(x + pw / 2, y - ph * 0.8 + ph * 0.72, '招租中', fs * 0.82, '#F5F0E8', 500, 'middle', halo=False))


def scalebar(P, W, H, fs, pad, left=False):
    for km in (0.5, 1, 2):
        if km * P.s > W * 0.12:
            break
    L = km * P.s
    x0, y0 = (pad if left else W - pad - L), H - pad
    lab = f'{int(km * 1000)} m' if km < 1 else f'{int(km)} km'
    return (f'<path d="M{x0:.1f} {y0 - 5:.1f}v5h{L:.1f}v-5" fill="none" stroke="#6E5640" stroke-width="1.2"/>'
            + text(x0 + L / 2, y0 - 9, lab, fs, '#6E5640', 400, 'middle'))


def north(x, y, fs):
    return (f'<path d="M{x:.1f} {y - 12:.1f}l5 12l-5 -3.5l-5 3.5z" fill="#6E5640"/>'
            + text(x, y - 16, 'N', fs, '#6E5640', 500, 'middle', halo=False))


AREA_LABELS = {
    'zuoying': [('左營區', 22.6935, 120.2860), ('鼓山區', 22.6560, 120.2780), ('楠梓區', 22.7030, 120.3170), ('三民區', 22.6600, 120.3200)],
    'qiaotou': [('橋頭區', 22.7545, 120.2985), ('楠梓區', 22.7300, 120.2950), ('燕巢區', 22.7610, 120.3290)],
    'wandan': [('萬丹鄉', 22.5960, 120.4700), ('屏東市', 22.6620, 120.4720)],
}


def area_svg(key, phone):
    if phone:
        W, fs = 390, 11
        clat, clng, hw, hh = DATA['areas_phone'][key]
        H = round(W * hh / hw)
    else:
        W, fs = 720, 13
        clat, clng, hw = DATA['areas_desktop'][key]
        H = W
    P = Proj(clat, clng, hw, W, H)
    zh = AREA_ZH[key]
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{zh} REVO 住宅的大概位置">',
             f'<rect width="{W}" height="{H}" fill="#E4DED3"/>', town_paths(P, {zh}, 0.6)]
    for pts, col in ((MRT, RED_C), (ORANGE, ORANGE_C)):
        if line_visible(P, pts):
            parts.append(line_path(P, pts, col, 2.4, 0.75))
    for n, la, ln in AREA_LABELS[key]:
        x, y = P.xy(la, ln)
        on = n == zh
        if not on:
            if (x < 150 and y < 60) or (x > W - 70 and y < 60) or (phone and key == 'qiaotou'):
                continue
            x = min(max(x, 30), W - 30)
        parts.append(text(x, y, n, fs * (1.25 if on else 1.05), '#6E5640' if on else '#A3967F', 600 if on else 400, 'middle', serif=True, ls=2))
    r = 0.35 * P.s
    labels = []
    for c in DATA['circles'][key]:
        names = c['names']
        x, y = P.xy(c['lat'], c['lng'])
        if c['status'] == 'rent':
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#1F2A33" fill-opacity="0.06" stroke="#1F2A33" stroke-width="1.6"/>')
        else:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#9A5B2E" fill-opacity="0.12" stroke="#8C6A4A" stroke-width="1.3" stroke-dasharray="4 3"/>')
        mode = DATA['circle_label_phone' if phone else 'circle_label'].get('|'.join(names), 'r')
        lh = fs * 1.35
        if mode in ('r', 'l'):
            side = 1 if mode == 'r' else -1
            lx, anchor = x + side * (r + 6), ('start' if side > 0 else 'end')
            top = y - (len(names) - 1) * lh / 2 + fs * 0.4
        else:
            lx, anchor = x, 'middle'
            top = y + r + fs * 1.3 if mode == 'b' else y - r - (len(names) - 1) * lh - fs * 0.5
        for i, nm in enumerate(names):
            yy = top + i * lh
            if nm in RENT_NAMES:
                tx = lx - fs * 2.0 if anchor == 'middle' else lx
                labels.append(text(tx, yy, nm, fs * 1.18, '#1F2A33', 600, anchor, serif=True))
                labels.append(rent_pill(tx, yy, nm, fs, 'start' if anchor != 'end' else 'end', mid=anchor == 'middle'))
            else:
                labels.append(text(lx, yy, nm, fs * 1.18, '#1F2A33', 600, anchor, serif=True))
    ir = fs * 0.62
    over = DATA['landmark_phone_override']
    for lm in DATA['landmarks'][key]:
        dx, dy, anchor = lm['dx'], lm['dy'], lm['anchor']
        if phone and lm['name'] in over:
            dx, dy, anchor = over[lm['name']]
        x, y = P.xy(lm['lat'], lm['lng'])
        st = lm['kind'] == 'station'
        if st:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{fs * 0.4:.1f}" fill="#F7F3EC" stroke="#3B4650" stroke-width="1.5"/>')
        else:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{fs * 0.26:.1f}" fill="#8A7560"/>')
        parts.append(text(x + dx * ir, y + dy * ir, lm['name'], fs * 0.92, '#3B4650' if st else '#6E5640', 400, anchor))
    parts += labels
    parts.append(scalebar(P, W, H, fs * 0.9, 18, left=(phone and key == 'qiaotou')))
    parts.append(north(W - 24, 40, fs * 0.85))
    parts.append('</svg>')
    return ''.join(parts)


OVER_LABELS = [('楠梓區', 22.7270, 120.2900), ('岡山區', 22.7900, 120.2950), ('燕巢區', 22.7820, 120.3700), ('仁武區', 22.7000, 120.3550),
               ('鼓山區', 22.6450, 120.2780), ('三民區', 22.6430, 120.3150), ('鳳山區', 22.6080, 120.3600), ('大樹區', 22.6950, 120.4300),
               ('大寮區', 22.5900, 120.4100), ('鳥松區', 22.6600, 120.3700), ('屏東市', 22.6750, 120.4850), ('高雄市', 22.5700, 120.3000), ('屏東縣', 22.5600, 120.5000)]
CHIP_AT = {'zuoying': (22.6760, 120.3200), 'qiaotou': (22.7470, 120.3260), 'wandan': (22.6150, 120.4750)}


def overview(phone):
    if phone:
        W, H, fs = 390, round(390 * 1.15), 11
        clat, clng, hw = 22.676, 120.383, 12.6
    else:
        W, H, fs = 720, 720, 13
        clat, clng, hw = DATA['overview']
    P = Proj(clat, clng, hw, W, H)
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="REVO 住宅分佈：左營、橋頭、萬丹">',
             f'<rect width="{W}" height="{H}" fill="#E4DED3"/>', town_paths(P, ACTIVE, 0.9),
             line_path(P, MRT, RED_C, 2, 0.75), line_path(P, ORANGE, ORANGE_C, 2, 0.85)]
    for pts, col, keep in ((MRT, RED_C, ('R3', 'R16', 'R23')), (ORANGE, ORANGE_C, ('O2', 'OT1'))):
        for code, nm, la, ln in pts:
            if code in keep:
                x, y = P.xy(la, ln)
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="#F7F3EC" stroke="{col}" stroke-width="1.3"/>')
    x, y = P.xy(22.631444, 120.301972)  # 美麗島（紅橘線交會）
    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#F7F3EC" stroke="#8C6A4A" stroke-width="1.6"/>')
    parts.append(text(x + 6, y + fs * 2.1, '美麗島站', fs * 0.85, '#6E5640', 400, 'start'))
    for n, la, ln in OVER_LABELS:
        x, y = P.xy(la, ln)
        if 10 < x < W - 10 and 10 < y < H - 10:
            big = n in ('高雄市', '屏東縣')
            parts.append(text(x, y, n, fs * (1.15 if big else 0.95), '#A3967F' if big else '#B3A792', 400, 'middle', serif=True, ls=2 if big else 1))
    for key in AREAS:
        for c in DATA['circles'][key]:
            x, y = P.xy(c['lat'], c['lng'])
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{"#1F2A33" if c["status"] == "rent" else "#8C6A4A"}" stroke="#F7F3EC" stroke-width="1.5"/>')
    parts.append('</svg>')
    # 疊在地圖上的按鈕：整個行政區的感應範圍 + 區域標籤
    btns = []
    for key in AREAS:
        t = [t for t in TOWNS if t['name'] == AREA_ZH[key]][0]
        xs, ys = [], []
        for ring in t['rings']:
            for lng, lat in ring:
                px, py = P.xy(lat, lng)
                xs.append(min(max(px, 0), W))
                ys.append(min(max(py, 0), H))
        btns.append(f'<button type="button" class="map-hit" data-map-go="{key}" tabindex="-1" aria-hidden="true" '
                    f'style="left:{min(xs) / W * 100:.1f}%;top:{min(ys) / H * 100:.1f}%;width:{(max(xs) - min(xs)) / W * 100:.1f}%;height:{(max(ys) - min(ys)) / H * 100:.1f}%"></button>')
    for key in AREAS:
        x, y = P.xy(*CHIP_AT[key])
        homes = [h for h in DATA['homes'] if h['area'] == key]
        rent = sum(1 for h in homes if h['status'] == 'rent')
        cls = 'map-pin is-left' if key == 'wandan' else 'map-pin'
        extra = f'<span class="map-pin-rent">{rent} 間招租中</span>' if rent else ''
        btns.append(f'<button type="button" class="{cls}" data-map-go="{key}" aria-controls="map-frame" '
                    f'style="left:{x / W * 100:.1f}%;top:{y / H * 100:.1f}%"><span class="map-pin-name">{SHORT[key]}</span>'
                    f'<span class="map-pin-n">{len(homes)} 間</span>{extra}</button>')
    return ''.join(parts) + '\n' + '\n'.join(btns)


def area_sub(key):
    homes = [h for h in DATA['homes'] if h['area'] == key]
    rent = sum(1 for h in homes if h['status'] == 'rent')
    return f'{len(homes)} 間・' + (f'{rent} 間招租中' if rent else '目前全部已入住')


def line_link(name):
    return 'https://line.me/R/oaMessage/%40re.vo/?' + urllib.parse.quote(f'您好，我想登記 REVO｜{name} 的空房通知')


ARROW = ('<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" '
         'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 8h10M9 4l4 4-4 4"/></svg>')


def home_item(h):
    place = AREA_ZH[h['area']]
    tag = ('<span class="map-tag is-rent">招租中</span>' if h['status'] == 'rent'
           else '<span class="map-tag">已入住</span>')
    if h['status'] == 'rent':
        act = f'<a class="btn btn-primary map-home-btn" href="{h["detail"]}">看房源</a>'
    else:
        act = (f'<div class="map-home-links"><a href="{h["works"]}">看作品</a>'
               f'<a class="is-sub" href="{html.escape(line_link(h["name"]))}" target="_blank" rel="noopener">加 LINE，有空房通知我</a></div>')
    return (f'<li class="map-home">\n'
            f'<x-img key="{h["img"]}" alt="REVO {h["name"]} 室內" sizes="96px" pos="{h["pos"]}" class="media map-home-img">\n'
            f'<div class="map-home-body">\n<div class="map-home-top"><h4 class="map-home-name">REVO｜{h["name"]}</h4>{tag}</div>\n'
            f'<div class="map-home-meta">{place}・{h["rooms"]}</div>\n{act}\n</div>\n</li>')


def section(version):
    total = len(DATA['homes'])
    chips = ['<button type="button" class="chip" data-map-go="all" aria-pressed="true" aria-controls="map-frame">全區</button>']
    for key in AREAS:
        n = sum(1 for h in DATA['homes'] if h['area'] == key)
        chips.append(f'<button type="button" class="chip" data-map-go="{key}" aria-pressed="false" aria-controls="map-frame">{SHORT[key]}<span class="map-chip-n">{n}</span></button>')
    views = [f'<div class="map-view" data-map-view="all">\n<div class="map-svg only-desktop">{overview(False)}</div>\n'
             f'<div class="map-svg only-mobile">{overview(True)}</div>\n</div>']
    for key in AREAS:
        views.append(f'<div class="map-view" data-map-view="{key}" hidden>\n'
                     f'<div class="map-svg only-desktop" data-map-src="/assets/map/{key}-d.svg?v={version}"></div>\n'
                     f'<div class="map-svg only-mobile" data-map-src="/assets/map/{key}-m.svg?v={version}"></div>\n</div>')
    cards = []
    for key in AREAS:
        names = '・'.join(h['name'] for h in DATA['homes'] if h['area'] == key)
        if key == 'wandan':
            names = '屏東縣・' + names
        cards.append(f'<div class="map-area-card">\n<div class="map-area-card-head"><h3 class="map-area-card-name">{AREA_ZH[key]}</h3>'
                     f'<span class="map-area-sub">{area_sub(key)}</span></div>\n<p>{names}</p>\n'
                     f'<button type="button" class="map-area-go" data-map-go="{key}" aria-controls="map-frame">看這一區的位置 →</button>\n</div>')
    panels = [f'<div class="map-panel" data-map-panel="all">\n<div class="map-side-eyebrow">三個區域・{total} 間住宅</div>\n' + '\n'.join(cards) + '\n</div>']
    for key in AREAS:
        items = '\n'.join(home_item(h) for h in DATA['homes'] if h['area'] == key)
        panels.append(f'<div class="map-panel" data-map-panel="{key}">\n'
                      f'<button type="button" class="map-side-back only-desktop" data-map-go="all">← 回到全區</button>\n'
                      f'<div class="map-area-head"><h3 class="map-area-name">{AREA_ZH[key]}</h3><span class="map-area-sub">{area_sub(key)}</span></div>\n'
                      f'<ul class="map-homes">\n{items}\n</ul>\n</div>')
    legend = ('<div class="map-legend">'
              '<span class="map-lg"><i class="lg-rent"></i>招租中</span>'
              '<span class="map-lg"><i class="lg-occ"></i>已入住</span>'
              '<span class="map-lg" data-legend="all zuoying qiaotou"><i class="lg-red"></i>捷運紅線</span>'
              '<span class="map-lg" data-legend="all"><i class="lg-orange"></i>捷運橘線</span>'
              '<span class="map-lg" data-legend="zuoying qiaotou wandan" hidden><i class="lg-station"></i>車站</span>'
              '<span class="map-lg" data-legend="zuoying qiaotou" hidden><i class="lg-poi"></i>地標</span>'
              '</div>')
    return f'''<!-- MAP:START（這一段由 tools/map/build_map.py 產生，請勿手動修改） -->
<section class="section map" id="map" data-map>
<div class="container">
<div class="stack map-intro" style="--gap: 16px;">
<div class="eyebrow">REVO 住宅分佈</div>
<h2 class="h2">REVO 經營的住宅，<br class="m-br">都在這裡</h2>
<p class="lead">目前 REVO 經營的住宅分佈在左營、橋頭與屏東萬丹。點選區域，看每一間的大概位置與附近的捷運、公園。</p>
</div>
<div class="chips scroll map-chips only-mobile" role="group" aria-label="選擇區域">
{chr(10).join(chips)}
</div>
<div class="map-layout">
<div class="map-col">
<div class="map-frame" id="map-frame">
{chr(10).join(views)}
<button type="button" class="map-back" data-map-go="all" hidden>← 回到全區</button>
</div>
{legend}
</div>
<div class="map-side" aria-live="polite">
{chr(10).join(panels)}
</div>
</div>
</div>
</section>
<!-- MAP:END -->'''


def main():
    import datetime
    version = datetime.datetime.now().strftime('%Y%m%d%H%M')
    os.makedirs(OUT_SVG, exist_ok=True)
    for key in AREAS:
        for phone, suf in ((False, 'd'), (True, 'm')):
            with open(os.path.join(OUT_SVG, f'{key}-{suf}.svg'), 'w', encoding='utf-8') as f:
                f.write(area_svg(key, phone))
    page = open(PAGE, encoding='utf-8').read()
    block = section(version)
    if '<!-- MAP:START' in page:
        page = re.sub(r'<!-- MAP:START.*?<!-- MAP:END -->', lambda m: block, page, flags=re.S)
    else:
        marker = '<section class="band-ink cta-band">'
        page = page.replace(marker, block + '\n\n' + marker, 1)
    open(PAGE, 'w', encoding='utf-8').write(page)
    sizes = {f: os.path.getsize(os.path.join(OUT_SVG, f)) for f in sorted(os.listdir(OUT_SVG))}
    print('地圖已更新：', len(block), 'bytes inline；', sizes)


if __name__ == '__main__':
    main()
