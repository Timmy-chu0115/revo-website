# REVO 網站｜開發慣例

給之後維護這個網站的人（或 AI）看。網站是純 HTML／CSS／JS，沒有框架。

## 指令

```
python3 build.py                 # 產生 public/
python3 build.py --only=works    # 只重產某幾頁（逗號分隔，用 src/pages 的檔名）
python3 build.py --images        # assets-src 有新圖或換圖時，重新產生圖片（約 1 分鐘）
python3 tools/shot.py /works/    # 桌機 1440、手機 390 整頁截圖到 tools/shots/
```

Cloudflare（Workers 靜態網站）：推到 GitHub main 會自動部署，設定在 `wrangler.jsonc`（發布 `public/`，找不到的網址顯示 404.html）。public 會一起 commit。

## 檔案

| 位置 | 內容 |
|---|---|
| `site.config.json` | 網址、LINE 連結、表單網址、Turnstile 網站金鑰 |
| `src/partials/` | `<head>`、頁首（含手機選單）、頁尾。**所有頁共用，改這裡全站一起變** |
| `src/pages/*.html` | 每頁內容。開頭註解是頁面設定（見下） |
| `src/css/00-base.css` `10-layout.css` | 共用樣式與元件 |
| `src/css/50-<頁>.css` | 該頁專用樣式，class 一律加頁面前綴（`home-`、`plans-`、`works-`、`homes-`、`about-`、`eval-`、`privacy-`） |
| `src/js/00-core.js` | 選單、頁首捲動、底部列、滑動圓點、分頁切換 |
| `src/js/50-<頁>.js` | 該頁專用互動，開頭先判斷元素存在，不存在就 return |
| `assets-src/` | 原始圖片（檔名＝圖片代號）與圖示 png/svg |

## 頁面設定（src/pages 檔案開頭）

```
<!--
title: 頁面標題｜REVO 銳沃
description: 搜尋結果與分享時顯示的一句話（80 字內）
path: /works/
nav: works            # 頁首哪個選項亮起：plans / works / homes / about，或留空
cta: owner            # 頁首右上按鈕：owner＝LINE 諮詢（屋主）；resident＝預約參觀（住戶）
bottombar: owner      # 手機底部列：owner＝免費出租評估＋LINE 聊聊；resident＝預約參觀；none＝不顯示
header: overlay       # 只有首頁用：頁首疊在大圖上
og: fushan-31         # 分享預覽圖（需在 site.config.json 的 og_images）
footnote: 地圖資料：內政部   # 選填：頁尾版權列旁的資料出處小字，只在這一頁出現
-->
```

頁面內容可以用 `{{LINE_OWNER}}`、`{{LINE_RESIDENT}}`、`{{FORM_ENDPOINT}}` 代入設定值。

## 斷點

只有一個：**寬度 ≥ 900px 是桌機版，以下是手機版**。CSS 先寫手機，再用 `@media (min-width: 900px)` 改桌機。
- `.only-desktop` / `.only-mobile` 只在某一種寬度顯示（必要時才用，優先用同一份 HTML 排兩種版面）。
- `<br class="m-br">` 只在手機換行，`<br class="d-br">` 只在桌機換行。

## 顏色與字（`:root` 變數）

`--cream` 主背景 · `--sand` 米色區塊 · `--sand-2` 圖片底 · `--card`/`--card-line` 卡片 · `--ink` 主文字與深色按鈕 · `--body` 內文 · `--muted` 次要 · `--label` 小標棕 · `--accent` 必填星號 · `--line`/`--line-2`/`--line-3` 細線 · `--night` 頁尾。
字：`--serif`（Noto Serif TC，標題）、`--sans`（Noto Sans TC，內文）。不要寫死其他顏色。

## 共用元件 class

- 版面：`.container`（最寬 1200）、`.container-narrow`（880）、`.section`（上下留白）、`.band-sand`、`.band-ink`、`.stack`（直向排列，`--gap` 調間距）
- 字：`.eyebrow` 小標、`.h1` `.h2` `.h3`、`.lead`、`.body`、`.small`、`.num`（01 02 編號）
- 按鈕：`.btn` + `.btn-primary` / `.btn-outline` / `.btn-light` / `.btn-outline-light`；`.btn-row`（加 `.m-stack` 手機直排滿版）；`.link-arrow`
- 選取：`.chip`（`aria-pressed="true"` 或 `aria-selected="true"` 為選中）、`.chips`、`.chips.scroll`
- 卡片：`.card`；分隔線清單：`.rule-list`
- 照片：`<x-img>`（見下）＋ `.tag` / `.tag.dark` 角標
- 手機橫滑：`<div class="swipe" data-swipe="x">…</div><div class="dots only-mobile" data-dots="x"></div>`
- 手風琴：`<details class="acc"><summary>…<svg class="acc-icon">…</svg></summary><div class="acc-body">…</div></details>`
- 分頁：外層 `data-tabs`，按鈕 `data-tab="a"`，內容 `data-panel="a"`（其餘加 `hidden`）
- 深色結尾區：`<section class="band-ink cta-band"><div class="container inner">…</div></section>`

## 照片

```html
<x-img key="fushan-card-desktop" m-key="fushan-card-phone" alt="REVO 福山公園：餐桌、客廳與落地窗"
       sizes="(min-width: 900px) 60vw, 80vw" pos="50% 55%" m-pos="40% 60%" class="media home-card-img">
```
- 會產生 `<picture class="media …">`，圖片 `object-fit: cover`。**尺寸請在 CSS 用 class 設定 picture 的寬高或 `aspect-ratio`**。
- `key` 是 `assets-src` 的檔名。可用的代號在 `tools/images.json`；設計稿裡 `/_blob/<id>` 對應的代號在 `tools/blob-keys.json`。
- 首屏大圖加 `eager`，其他都延遲載入。
- `alt` 寫照片內容，不寫「實拍」二字。

## 內容原則

- 文字一律照設計稿與文案，不自己加優點、數字或形容詞；不用最高級（最好、第一）。
- 不公開門牌、樓層、租金、押金。
- 屋主聯繫走 `{{LINE_OWNER}}`（個人 LINE，不能預帶文字）；住戶走 `{{LINE_RESIDENT}}`（官方帳號 @re.vo）。
  官方帳號預帶文字：`https://line.me/R/oaMessage/%40re.vo/?<網址編碼的文字>`（只在手機 LINE 有效）。
- 外部連結加 `target="_blank" rel="noopener"`。

## 住宅地圖（精選寓所頁）

`/homes/` 的「REVO 住宅分佈」地圖由 `python3 tools/map/build_map.py` 產生，**不要手改** `homes.html` 裡 `<!-- MAP:START -->` 到 `<!-- MAP:END -->` 那段。
- 資料：`tools/map/map-data.json`（住宅清單與狀態、範圍圈圓心、地標、捷運線）、`tools/map/towns.json`（行政區界，內政部資料）。
- 範圍圈圓心是**偏移 120–200 公尺後**的大概位置。新增住宅時先把 Google 地圖座標偏移再填入，真實座標不要放進專案（GitHub 是公開的）。
- 招租狀態改了（例如已入住 → 招租中）：改 `map-data.json` 的 `homes[].status` 與 `circles[].status`，再跑產生器。
- 產生器會寫出 `public/assets/map/<區域>-d.svg`／`-m.svg`（點進區域才載入）並更新 homes.html，接著 `python3 build.py --only=homes`。
- 互動在 `src/js/55-map.js`，樣式在 `src/css/55-map.css`。

## 網址

| 頁 | 路徑 | 檔案 |
|---|---|---|
| 首頁 | `/` | index.html |
| 屋主服務 | `/plans/` | plans.html |
| 作品案例 | `/works/`（各案錨點 `#fushan` `#senhuo` `#metro` `#liantan` `#danying`） | works.html |
| REVO 精選寓所 | `/homes/` | homes.html |
| 未來境 | `/homes/weilai-jing/` | homes-weilai-jing.html |
| 未來章 | `/homes/weilai-zhang/` | homes-weilai-zhang.html |
| 關於 REVO | `/about/` | about.html |
| 免費出租評估 | `/evaluate/` | evaluate.html |
| 隱私權政策 | `/privacy/` | privacy.html |
| 找不到頁面 | （404.html） | 404.html |

## 表單防機器人（Cloudflare Turnstile）

`site.config.json` 的 `turnstile_sitekey` 留空＝不啟用（只靠隱藏欄位 `website` 與後端「同一支手機 60 秒一筆」）。啟用步驟：

1. Cloudflare 後台 → Turnstile → 新增網站，主機名稱填 `revo-website.revolife-info.workers.dev`（之後換網域要再加），模式選「受管理」。拿到「網站金鑰」與「密鑰」。
2. 密鑰只放 Apps Script：專案設定 → 指令碼屬性，新增 `TURNSTILE_SECRET`。**不要放進這個 repo**（repo 是公開的）。
3. Apps Script 的 `doPost` 開頭加上驗證（前端送來的欄位名稱是 `turnstile`）：

   ```js
   function verifyTurnstile_(token) {
     var secret = PropertiesService.getScriptProperties().getProperty('TURNSTILE_SECRET');
     if (!secret) return true;                     // 還沒設定密鑰 → 不擋
     if (!token) return false;
     var res = UrlFetchApp.fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
       method: 'post', payload: { secret: secret, response: token }, muteHttpExceptions: true
     });
     try { return JSON.parse(res.getContentText()).success === true; } catch (e) { return false; }
   }
   // doPost(e) 裡：
   // if (!verifyTurnstile_(e.parameter.turnstile)) return json_({ ok: false, error: 'verify' });
   ```
   （`json_` 換成現有回傳 JSON 的寫法。）部署 → 管理部署作業 → 編輯 → 新版本，網址不變。
4. 網站金鑰填進 `site.config.json` 的 `turnstile_sitekey`，`python3 build.py`，commit 推上 main。
5. 實際送一筆測試，確認試算表有收到。

前端行為：有金鑰時表單送出鈕上方會出現驗證框；Turnstile 載不到（網路或擋廣告）不會卡住送出，交給後端判斷，驗證不過會顯示 LINE 備援。
