# VATICANO

ヴァチカン市国（サン・ピエトロ広場・大聖堂の内外・ヴァチカン美術館・システィーナ礼拝堂）を3Dで再構成し、約9分のドローン飛行で巡る作品です。自由飛行と場所ジャンプ、日本語・英語、合成ピアノ（場所ごとの20楽章）と噴水・鐘の音つき。

公開されるのは `public/` だけです（`demo.json` の `"serve": "public"`）。`tools/` は生成パイプライン、元素材は `/home/kazu/work/vatican-assets/`（リポジトリ外）にあります。

## 構成

| 場所 | 中身 |
|---|---|
| `public/index.html` | 画面（タイトル・字幕・作品カード・操作バー・出典） |
| `public/app.js` | `tools/web/*.js` を esbuild で束ねたもの（three.js を含む） |
| `public/data/*.json, *.N.bin` | ゾーンごとのメッシュ（meshopt 圧縮、20 MiB ごとに分割）。`city`・`core` は起動時、`basilica`・`sistine`・`room_*` は近づいたときに読む |
| `public/art/*.webp` | 絵画・天井画・地図などの画像と手続き生成テクスチャ。`index.json` に題名・作者・年 |
| `public/tex/` | 細部テクスチャのアトラスと空の HDR |
| `public/credits.html` | 出典とライセンス（`tools/credits.mjs` が生成） |

## 作り直す

```bash
cd vatican/tools
npm install                                   # three, meshoptimizer, sharp など（初回のみ）
blender -b --python build_exterior.py -- /home/kazu/work/vatican-assets/bake/ext --samples 256 only=ext,basilica,sistine,museums
./pack_all.sh core city basilica sistine rooms
node art_prep.mjs        # 画像 → public/art/*.webp（キーを並べればその分だけ）
node credits.mjs
node build_web.mjs       # --dev でソースマップ付き
```

- 建物は Python で手続き的に作り（`vb/geom.py`・`vb/arch.py`、`build_*.py`）、Blender Cycles（OptiX）で天空光と間接光を頂点に焼き込みます。太陽の直射は three.js の影（CSM）で描きます。
- 内部空間は他のゾーンを隠して焼きます（外の建物の塊が中庭の空を塞がないように）。面の向きは部屋ごとの視点から光線で判定して揃えます（`bake.orient_faces`）。
- `pack.mjs` は焼き込み後の三角形を、形（2 cm）と光の差が見えない範囲で間引きます。手前で見る彫刻（`statue_marble`）は間引きません。
- 確認：`node snap.mjs out.jpg "" shots.json`（実 GPU のヘッドレス Chrome）。`window.VAT.at(秒)` でツアーの任意の時刻、`VAT.look(x,y,z,tx,ty,tz)` で任意の視点、`?dbg=irr|nrm|alb` で焼き込み光・法線・色を表示します。

## 素材と限界

地図のギャラリーの天井とクーポラ内側のモザイクは、Wikimedia Commons の CC0 写真を切り抜いて組み直しています。寸法はカルロ・フォンターナ『Templum Vaticanum』（1694）の実測図、OpenStreetMap、写真から推定しています。公式の測量モデルではありません。絵画は Wikimedia Commons のパブリックドメイン（一部 CC BY-SA）の画像、彫刻はデンマーク国立美術館（SMK）の石膏像スキャン（CC0）と Scan the World（CC BY-SA）です。自由に使えるスキャンがない彫刻（列柱上の聖人像、ペルセウスなど）は別の像で代用しています。全出典は作品内の「出典」に載せています。
