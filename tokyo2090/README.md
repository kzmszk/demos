# TOKYO 2090 — 滑空する廃都

2090年、人類が消えて六十年の東京を、マントで滑空するフライトゲーム。渋谷・新宿・六本木の 7 km 四方を、
2020 年代の実データから作り、高いビルを乱数で崩し、六十年分のツタと苔と木を生やしています。

- `public/` — 配信物。`index.html` と `app.js`（`tools/web/*.js` を esbuild で束ねたもの）、`data/`（生成データ）。
- `tools/gen/` — データ生成（Python、`/home/kazu/work/kyoto-assets/.venv`）。順に
  `fetch_dem` → `fetch_plateau` → `plateau` → `osm_extract` → `osm` → `dem core far` → `ground` → `city` → `roofpack`。
  生データと中間物は `/home/kazu/work/tokyo2090-assets/`。
- `tools/web/` — three.js のビューア。`main.js`（ループと UI）、`city.js`（タイルと外壁シェーダ）、`facade.js`（外壁アトラス
  8 様式と風化ディテール）、`terrain.js`、
  `flight.js`（飛行モデル）、`body.js`（一人称の腕とマント）、`saki.js`、`props.js`（車と木）、`story.js`（テレパシー）、
  `light.js`（太陽と影）、`clouds.js`、`music.js`。
- `tools/blender/saki.py` — サキのモデル（Blender → `public/models/saki.glb`、fly / sit / stand）。
- `tools/build_web.mjs` — バンドル。`tools/snap.mjs out.jpg "" shots.json` — ヘッドレス Chrome で撮影・検証。
- `boards/` — Codex で作ったイメージボード。`docs/concept.md` — 設定。`NOTES.md` — 作業で学んだこと。

## 操作

Space で飛び降りる。W/S で下げ・上げ、A/D で傾ける、Shift で絞る（速く）、F で広げる（ブレーキ）。
クリックでマウス操作（手の向きで経路を変える）。見ている屋上が光ったら E で降りる。

## データと出典

- 建物: 国土交通省 Project PLATEAU「東京都 23 区 3D 都市モデル（2025）」LOD2 3D Tiles（CC BY 4.0）。
  約 105,000 棟。崩壊・植生は本作の創作で、現実の建物の状態ではありません。
- 道路・公園・水面・線路・樹木: © OpenStreetMap contributors（ODbL）。
- 地形: 国土地理院 標高タイル（5 m DEM、10 m DEM）。
- 音楽: エリック・サティ《ジムノペディ 第 1 番》（1888、パブリックドメイン）を Web Audio で合成。
- three.js（MIT）。
