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

## 紹介動画

約 1 分の紹介動画（1920×1080・30fps）を、アプリ自身を 1/30 秒ずつ進めて 1 コマずつ書き出して作ります。音楽はツアーの楽譜の冒頭（到着の楽章の 0〜8 小節と、広場の楽章の 4 小節目から最後まで）を、アプリの音源でオフライン描画したもので、カットはその小節線（4 秒ごと）に合わせています。噴水と鐘の音も重ねます。

```bash
cd vatican/tools
node film.mjs scout OUTDIR [shot,shot]   # 各ショットの静止画 3 枚（構図の確認）
node film.mjs render OUTDIR              # 全コマ（JPEG）と音（music_full.wav・amb.wav・cut.json）
python film_mix.py OUTDIR                # 楽譜の切りつなぎ、環境音、-16 LUFS → OUTDIR/vaticano.mp4
```

ショットは `film_shots.mjs`（ツアーの区間 `seg` の局所時刻 a〜b、字幕、タイトル）。`film_page.js` がページ内で動き、`VAT.step` でコマを進め、作品の画像が読み込み終わるのを待ってから、描いた直後の WebGL の画素を `readPixels` で読みます（canvas の drawImage だと、ときどき空だけの画像になった）。音は `AUDIO.offline()`（OfflineAudioContext）。2026-10-06 の動画は `vatican-assets/film/`（`vaticano.mp4`、送付用の `vaticano_share.mp4`）。公開は `/vatican/film`（`public/film.html`、ギャラリーのカードの「紹介動画 · Film」）：動画は R2 から Worker の `/media/movies/vaticano-film/video.mp4` で配信し（静的ファイルはバイト範囲指定に応えず、Safari が再生しないため）、`public/movie/vaticano.mp4`（25 MiB 未満の送付用と同じもの）を予備にしています。動画ファイルは Git に入れません（`vatican/.gitignore`）。

## 素材と限界

地図のギャラリーの天井とクーポラ内側のモザイクは、Wikimedia Commons の CC0 写真を切り抜いて組み直しています。寸法はカルロ・フォンターナ『Templum Vaticanum』（1694）の実測図、OpenStreetMap、写真から推定しています。公式の測量モデルではありません。絵画は Wikimedia Commons のパブリックドメイン（一部 CC BY-SA）の画像、彫刻はデンマーク国立美術館（SMK）の石膏像スキャン（CC0）と Scan the World（CC BY-SA）です。自由に使えるスキャンがない彫刻（列柱上の聖人像、ペルセウスなど）は別の像で代用しています。全出典は作品内の「出典」に載せています。
