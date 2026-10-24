# TOKYO 2090 — 滑空する廃都

2090年、人類が消えて六十年の東京を、マントで滑空するフライトゲーム。渋谷・新宿・六本木の 7 km 四方を、
2020 年代の実データから作り、高いビルを乱数で崩し、六十年分のツタと苔と木を生やしています。

- `public/` — 配信物。`index.html` と `app.js`（`tools/web/*.js` を esbuild で束ねたもの）、`data/`（生成データ）。
- `tools/gen/` — データ生成（Python、`/home/kazu/work/kyoto-assets/.venv`）。順に
  `fetch_dem` → `fetch_plateau` → `plateau` → `osm_extract` → `osm` → `dem core far` → `ground` → `hero_src`（作り込み地区の素材）→ `city` →
  `hero_collide`（作り込み地区の衝突）→ `roofpack` → `foot`（歩行用の 1 m 足場マスクと瓦礫の山）、`places`（地名）、`rails`（鉄道）。
  生データと中間物は `/home/kazu/work/tokyo2090-assets/`。
- `tools/web/` — three.js のビューア。`main.js`（ループと UI）、`city.js`（タイルと外壁シェーダ）、`facade.js`（外壁アトラス
  8 様式と風化ディテール）、`terrain.js`、
  `flight.js`（飛行モデル・着地・登攀）、`walk.js`（歩行の足場と衝突）、`body.js`（一人称の腕とマント）、`saki.js`、`props.js`（車と木）、`story.js`（テレパシー）、
  `light.js`（太陽と影）、`clouds.js`、`music.js`。
- `tools/hero/` — 作り込み地区（渋谷スクランブル交差点〜109、都庁、六本木ヒルズ）を Blender で作るスクリプト。共通仕様は `BRIEF.md`、
  出力は `public/hero/<地区>/`（near / mid / far の glb、collide.obj、hero.json）。ビューアは `hero.js`、地名は `labels.js`、鉄道は `rails.js`。
- `tools/blender/saki.py` — サキのモデル（Blender → `public/models/saki.glb`、fly / sit / stand / walk / run）。
- `tools/build_web.mjs` — バンドル。`tools/snap.mjs out.jpg "" shots.json` — ヘッドレス Chrome で撮影・検証。
- `boards/` — Codex で作ったイメージボード。`docs/concept.md` — 設定。`NOTES.md` — 作業で学んだこと。

## 操作

Space で飛び降りる。W/S で下げ・上げ、A/D で傾ける、Shift で絞る（速く）、F で広げる（ブレーキ）。
クリックでマウス操作（手の向きで経路を変える）。見ている屋上や道が光ったら E で降りる。低く滑空して
地面や屋上にそっと触れても着地できる（速く落ちると墜落）。

地上と屋上では歩ける: W A S D で歩き（見ている方へ）、Shift で走る。壁の前で Space を押すと登り、
登っている途中の Space で壁を蹴って飛ぶ。屋上では Space で縁から飛び降りる。サキは横を歩いてついてくる。
スマホは左のスティックで歩く（大きく倒すと走る）、右側のドラッグで見回す、下の大きなボタンが「登る / 飛び降りる」。

有名なビルには遠くからでも名前の吹き出しが出て、公園や駅や線路は近くを通ると名前が出る（L で表示を切り替え）。
左上の「場所」（P）から、作り込んだ地区へ歩いて降り立てる。

## データと出典

- 建物: 国土交通省 Project PLATEAU「東京都 23 区 3D 都市モデル（2025）」LOD2 3D Tiles（CC BY 4.0）。
  約 105,000 棟。崩壊・植生は本作の創作で、現実の建物の状態ではありません。
- 道路・公園・水面・線路・樹木: © OpenStreetMap contributors（ODbL）。
- 地形: 国土地理院 標高タイル（5 m DEM、10 m DEM）。
- 音楽: エリック・サティ《ジムノペディ 第 1 番》（1888、パブリックドメイン）を Web Audio で合成。
- three.js（MIT）。
