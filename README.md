# REVO 銳沃 品牌網站

純靜態網站（HTML／CSS／JS），由 `build.py` 產生到 `public/`，部署在 Cloudflare Pages。

- 修改內容：編輯 `src/pages/`、`src/css/`、`src/js/`、`src/partials/`，再執行 `python3 build.py`，把 `public/` 一起 commit。
- Cloudflare Pages 設定：建置指令留空，輸出目錄 `public`。
- 開發慣例見 [CONVENTIONS.md](CONVENTIONS.md)。
