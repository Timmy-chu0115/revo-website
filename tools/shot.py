#!/usr/bin/env python3
"""截圖檢查：python3 tools/shot.py /works/ [/plans/ ...]
   會在 tools/shots/ 產生 <頁面>-desktop.png（1440 寬）與 <頁面>-mobile.png（390 寬）的整頁截圖。
   需要先 python3 build.py。"""
import asyncio, os, sys, threading, http.server, socketserver, functools
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'public'); OUTD = os.path.join(ROOT, 'tools', 'shots'); os.makedirs(OUTD, exist_ok=True)
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_error(self, code, message=None, explain=None):
        if code == 404 and os.path.exists(os.path.join(PUB, '404.html')):
            self.send_response(404); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(open(os.path.join(PUB, '404.html'), 'rb').read()); return
        super().send_error(code, message, explain)
Handler = functools.partial(H, directory=PUB)
class Q(socketserver.ThreadingTCPServer): allow_reuse_address = True; daemon_threads = True
def serve(port):
    with Q(('127.0.0.1', port), Handler) as httpd: httpd.serve_forever()
async def main(paths):
    import random
    port = random.randint(8100, 8999)
    threading.Thread(target=serve, args=(port,), daemon=True).start()
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for path in paths:
            name = path.strip('/').replace('/', '_') or 'home'
            for w, tag in ((1440, 'desktop'), (390, 'mobile')):
                pg = await b.new_page(viewport={'width': w, 'height': 900}, device_scale_factor=1)
                errs = []
                pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'fonts.g' not in m.text and 'ERR_TUNNEL' not in m.text else None)
                await pg.goto(f'http://127.0.0.1:{port}{path}', wait_until='load')
                await pg.wait_for_timeout(600)
                # 讓延遲載入的圖片全部載入；整頁截圖時固定元素改成不跟著捲動
                await pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager')")
                h = await pg.evaluate('document.body.scrollHeight')
                for y in range(0, h, 700):
                    await pg.evaluate(f'window.scrollTo(0,{y})'); await pg.wait_for_timeout(40)
                await pg.evaluate("Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; setTimeout(r, 4000); })))")
                await pg.evaluate('window.scrollTo(0,0)'); await pg.wait_for_timeout(300)
                await pg.add_style_tag(content='body:not(.header-overlay) .site-header{position:relative!important}.header-overlay .site-header{position:absolute!important}.bottombar{display:none!important}')
                sw = await pg.evaluate('document.documentElement.scrollWidth')
                out = os.path.join(OUTD, f'{name}-{tag}.png')
                # 先把視窗拉成整頁高度再截圖（直接 full_page 會讓部分圖片重新載入而變成空白）
                await pg.evaluate("document.querySelectorAll('.home-hero').forEach(e => e.style.height = e.offsetHeight + 'px')")  # 依視窗高度的區塊先固定
                full = await pg.evaluate('document.documentElement.scrollHeight')
                await pg.set_viewport_size({'width': w, 'height': min(full, 16000)}); await pg.wait_for_timeout(800)
                await pg.evaluate("Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; setTimeout(r, 4000); })))")
                await pg.screenshot(path=out)
                print(f'{out}  高度 {h}px  橫向溢出 {"有 (" + str(sw) + ")" if sw > w else "無"}  錯誤 {errs[:3] if errs else "無"}')
                await pg.close()
        await b.close()
asyncio.run(main(sys.argv[1:] or ['/']))
