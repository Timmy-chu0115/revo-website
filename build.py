#!/usr/bin/env python3
"""
REVO 銳沃網站產生器（不需安裝任何框架）

    python3 build.py           # 產生 public/（網站成品）
    python3 build.py --images  # 圖片有新增或更換時，加這個參數重新產生圖片

結構：
    src/partials/   共用的 <head>、頁首、頁尾
    src/pages/      每一頁的內容（檔案開頭的註解寫頁面設定）
    src/css/        樣式，依檔名順序合併成 public/assets/site.css
    src/js/         互動，依檔名順序合併成 public/assets/site.js
    assets-src/     原始圖片與圖示（檔名就是圖片代號 key）
    public/         產出的網站（Cloudflare Pages 發布這個資料夾）

頁面裡放照片：
    <x-img key="fushan-31" alt="說明" sizes="100vw" pos="50% 60%"
           m-key="fushan-hero-phone" m-pos="50% 50%" class="media hero-img" eager>
    key   桌機用的圖片代號（assets-src 的檔名，不含副檔名）
    m-key 手機（寬度 < 900px）改用的圖片，可省略
    pos / m-pos  裁切時的焦點（CSS object-position）
    eager 首屏圖片不要延遲載入
"""
import datetime
import glob
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
OUT = os.path.join(ROOT, 'public')
ASSETS_SRC = os.path.join(ROOT, 'assets-src')
CONFIG = json.load(open(os.path.join(ROOT, 'site.config.json'), encoding='utf-8'))

WIDTHS = [480, 800, 1200, 1800]
MOBILE_BP = 899  # px，<= 這個寬度用手機版

HEADER_CTA = {
    'owner': '<a class="nav-cta" href="{LINE_OWNER}" target="_blank" rel="noopener">LINE 諮詢</a>',
    'resident': '<a class="nav-cta" href="{LINE_RESIDENT}" target="_blank" rel="noopener"><img src="/assets/icons/icon-line-ink-square.png" alt="" width="18" height="18">預約參觀</a>',
}
BOTTOMBAR = {
    'owner': '<div class="bottombar" data-bottombar aria-label="快速聯繫">'
             '<a class="btn btn-primary grow" href="/evaluate/">免費出租評估</a>'
             '<a class="btn btn-outline" href="{LINE_OWNER}" target="_blank" rel="noopener">'
             '<img src="/assets/icons/icon-line-ink-round.png" alt="" width="20" height="20">LINE 聊聊</a></div>',
    'resident': '<div class="bottombar" data-bottombar aria-label="快速聯繫">'
                '<a class="btn btn-primary grow" href="{LINE_RESIDENT}" target="_blank" rel="noopener">'
                '<img src="/assets/icons/icon-line-white-square.png" alt="" width="20" height="20">預約參觀</a></div>',
    'none': '',
}


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


# ---------------------------------------------------------------- images
def image_info():
    """key -> {'w','h','widths','kind'}；由 assets-src 產生或讀 manifest"""
    man_path = os.path.join(ROOT, 'tools', 'images.json')
    return json.load(open(man_path, encoding='utf-8')) if os.path.exists(man_path) else {}


def build_images():
    from PIL import Image, ImageOps
    out_img = os.path.join(OUT, 'assets', 'img')
    out_icon = os.path.join(OUT, 'assets', 'icons')
    shutil.rmtree(out_img, ignore_errors=True)
    os.makedirs(out_img, exist_ok=True)
    os.makedirs(out_icon, exist_ok=True)
    manifest = {}
    for path in sorted(glob.glob(os.path.join(ASSETS_SRC, '*'))):
        key, ext = os.path.splitext(os.path.basename(path))
        ext = ext.lower()
        if ext in ('.png', '.svg', '.webp'):
            shutil.copy(path, os.path.join(out_icon, key + ext))
            continue
        im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
        w, h = im.size
        widths = [x for x in WIDTHS if x < w] + [min(w, WIDTHS[-1])]
        widths = sorted(set(widths))
        for x in widths:
            r = im.resize((x, round(h * x / w)), Image.LANCZOS)
            r.save(os.path.join(out_img, f'{key}-{x}.webp'), 'WEBP', quality=78, method=6)
        fb = min(1200, w)
        im.resize((fb, round(h * fb / w)), Image.LANCZOS).save(
            os.path.join(out_img, f'{key}-{fb}.jpg'), 'JPEG', quality=80, optimize=True, progressive=True)
        manifest[key] = {'w': w, 'h': h, 'widths': widths, 'fallback': fb}
    write(os.path.join(ROOT, 'tools', 'images.json'), json.dumps(manifest, indent=1, sort_keys=True))
    # 分享預覽圖（1200×630）
    og_dir = os.path.join(OUT, 'assets', 'og')
    os.makedirs(og_dir, exist_ok=True)
    for key in CONFIG.get('og_images', []):
        src = os.path.join(ASSETS_SRC, key + '.jpg')
        im = ImageOps.fit(ImageOps.exif_transpose(Image.open(src)).convert('RGB'), (1200, 630), Image.LANCZOS)
        im.save(os.path.join(og_dir, key + '.jpg'), 'JPEG', quality=82, optimize=True)
    # favicon
    logo = Image.open(os.path.join(ASSETS_SRC, 'logo.png')).convert('RGBA')
    mark = logo.crop((0, 0, logo.height, logo.height))  # 左側 R 字標
    for name, size, bg in (('favicon.png', 64, None), ('apple-touch-icon.png', 180, (245, 240, 232, 255))):
        canvas = Image.new('RGBA', (size, size), bg or (0, 0, 0, 0))
        m = mark.copy()
        m.thumbnail((int(size * .78), int(size * .78)), Image.LANCZOS)
        canvas.paste(m, ((size - m.width) // 2, (size - m.height) // 2), m)
        canvas.save(os.path.join(out_icon, name))
    return manifest


def srcset(key, info):
    return ', '.join(f'/assets/img/{key}-{w}.webp {w}w' for w in info['widths'])


def picture(attrs, images):
    key = attrs['key']
    if key not in images:
        print(f'⚠ 找不到圖片代號：{key}')
        return f'<div class="{attrs.get("class", "media")}" data-missing-image="{html.escape(key)}"></div>'
    info = images[key]
    alt = attrs.get('alt', '')
    sizes = attrs.get('sizes', '100vw')
    cls = attrs.get('class', 'media')
    style = []
    if attrs.get('pos'):
        style.append(f"--pos:{attrs['pos']}")
    if attrs.get('m-pos'):
        style.append(f"--pos-m:{attrs['m-pos']}")
    if attrs.get('style'):
        style.append(attrs['style'])
    sources = []
    mkey = attrs.get('m-key')
    if mkey:
        if mkey not in images:
            print(f'⚠ 找不到圖片代號：{mkey}')
            mkey = None
    if mkey:
        msizes = attrs.get('m-sizes', '100vw')
        sources.append(f'<source media="(max-width: {MOBILE_BP}px)" type="image/webp" srcset="{srcset(mkey, images[mkey])}" sizes="{msizes}">')
    sources.append(f'<source type="image/webp" srcset="{srcset(key, info)}" sizes="{sizes}">')
    loading = 'eager" fetchpriority="high' if 'eager' in attrs else 'lazy'
    extra = ''.join(f' {k}="{html.escape(v)}"' for k, v in attrs.items() if k.startswith('data-'))
    return (f'<picture class="{cls}"' + (f' style="{";".join(style)}"' if style else '') + extra + '>'
            + ''.join(sources)
            + f'<img src="/assets/img/{key}-{info["fallback"]}.jpg" alt="{html.escape(alt)}" width="{info["w"]}" height="{info["h"]}" loading="{loading}" decoding="async">'
            + '</picture>')


ATTR_RE = re.compile(r'([a-zA-Z][\w-]*)(?:="([^"]*)")?')


def expand_images(text, images):
    def rep(m):
        attrs = {k: (v if v is not None else '') for k, v in ATTR_RE.findall(m.group(1))}
        return picture(attrs, images)
    return re.sub(r'<x-img\s+([^>]*?)\s*/?>', rep, text)


# ---------------------------------------------------------------- pages
def parse_page(path):
    text = read(path)
    m = re.match(r'\s*<!--(.*?)-->\s*', text, re.S)
    meta = {}
    if m:
        for line in m.group(1).strip().splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, text


def fill(text, values):
    for k, v in values.items():
        text = text.replace('{{' + k + '}}', v)
    return text


def build_pages(images):
    head = read(os.path.join(SRC, 'partials', 'head.html'))
    header = read(os.path.join(SRC, 'partials', 'header.html'))
    footer = read(os.path.join(SRC, 'partials', 'footer.html'))
    version = datetime.datetime.now().strftime('%Y%m%d%H%M')
    common = {
        'SITE_URL': CONFIG['site_url'].rstrip('/'),
        'LINE_OWNER': CONFIG['line_owner'],
        'LINE_RESIDENT': CONFIG['line_resident'],
        'FORM_ENDPOINT': CONFIG['form_endpoint'],
        'TURNSTILE_SITEKEY': CONFIG.get('turnstile_sitekey', ''),
        'YEAR': str(datetime.date.today().year),
        'VERSION': version,
    }
    sitemap = []
    only = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--only=')]
    for path in sorted(glob.glob(os.path.join(SRC, 'pages', '*.html'))):
        if only and os.path.splitext(os.path.basename(path))[0] not in only[0].split(','):
            continue
        meta, body = parse_page(path)
        route = meta.get('path', '/')
        nav = meta.get('nav', '')
        values = dict(common)
        values.update({
            'TITLE': html.escape(meta.get('title', 'REVO 銳沃')),
            'DESCRIPTION': html.escape(meta.get('description', '')),
            'PATH': route,
            'OG_IMAGE': meta.get('og', CONFIG['og_images'][0]),
            'HEAD_EXTRA': meta.get('head', ''),
            'FOOTNOTE': (f'<span class="footnote">{html.escape(meta["footnote"])}</span>' if meta.get('footnote') else ''),
            'HEADER_CTA': fill(HEADER_CTA.get(meta.get('cta', 'owner'), ''), {}).replace('{LINE_OWNER}', common['LINE_OWNER']).replace('{LINE_RESIDENT}', common['LINE_RESIDENT']),
        })
        for n in ('plans', 'works', 'homes', 'about'):
            values['NAV_' + n] = ' aria-current="page"' if n == nav else ''
        bar_key = meta.get('bottombar', 'owner')
        bar = BOTTOMBAR[bar_key].replace('{LINE_OWNER}', common['LINE_OWNER']).replace('{LINE_RESIDENT}', common['LINE_RESIDENT'])
        body_cls = []
        if meta.get('header') == 'overlay':
            body_cls.append('header-overlay')
        if bar:
            body_cls.append('has-bottombar')
        page = (fill(head, values)
                + f'<body class="{" ".join(body_cls)}" data-page="{os.path.splitext(os.path.basename(path))[0]}">\n'
                + fill(header, values)
                + '<main id="main">\n' + fill(expand_images(body, images), values) + '\n</main>\n'
                + fill(footer, values) + bar
                + f'\n<script src="/assets/site.js?v={version}" defer></script>\n</body>\n</html>\n')
        if route == '/404':
            write(os.path.join(OUT, '404.html'), page)
            continue
        write(os.path.join(OUT, route.strip('/'), 'index.html'), page)
        if meta.get('sitemap', 'yes') != 'no':
            sitemap.append(route)
    return sitemap, common


def build_bundles(common):
    css = '\n'.join(read(p) for p in sorted(glob.glob(os.path.join(SRC, 'css', '*.css'))))
    js = '\n'.join(read(p) for p in sorted(glob.glob(os.path.join(SRC, 'js', '*.js'))))
    js = fill(js, common)
    write(os.path.join(OUT, 'assets', 'site.css'), css)
    write(os.path.join(OUT, 'assets', 'site.js'), js)


def build_meta(sitemap, common):
    base = common['SITE_URL']
    today = datetime.date.today().isoformat()
    urls = ''.join(f'<url><loc>{base}{r}</loc><lastmod>{today}</lastmod></url>' for r in sitemap)
    write(os.path.join(OUT, 'sitemap.xml'),
          f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    write(os.path.join(OUT, 'robots.txt'), f'User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n')
    write(os.path.join(OUT, '_headers'),
          '/assets/*\n  Cache-Control: public, max-age=2592000\n'
          '/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n'
          '  Permissions-Policy: camera=(), microphone=(), geolocation=()\n'
          '  X-Frame-Options: DENY\n  Content-Security-Policy: frame-ancestors \'none\'\n')


def main():
    if '--images' in sys.argv or not os.path.exists(os.path.join(ROOT, 'tools', 'images.json')):
        images = build_images()
    else:
        images = image_info()
    if not any(a.startswith('--only=') for a in sys.argv):
        for p in glob.glob(os.path.join(OUT, '**', 'index.html'), recursive=True):
            os.remove(p)
    sitemap, common = build_pages(images)
    build_bundles(common)
    if not any(a.startswith('--only=') for a in sys.argv):
        build_meta(sitemap, common)
    print(f'完成：{len(sitemap)} 頁 → public/')


if __name__ == '__main__':
    main()
