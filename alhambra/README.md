# ALHAMBRA

アルハンブラ宮殿を歩く・飛ぶ・上空から眺める静的3Dアプリ。既存の京都・ベニス・バチカンと同じ `demo.json` / `public/` 構成で、既存の Cloudflare Worker に `/alhambra/` として組み込みます。

## 動かす / Cloudflare Workers

リポジトリのルートで：

```bash
npm run build
npm run dev
# http://127.0.0.1:8787/alhambra/

npm run deploy
# 既存の Worker と同じ公開先の /alhambra/
```

`public/app.js` はビルド済みファイルを管理します。通常のギャラリービルドやデプロイにはBlender、Python、Three.jsの追加インストールは不要です。ブラウザーで実行し、WorkerのCPU・メモリで3Dシーンを生成しません。API、外部CDN、R2、データベース、新しいシークレットは不要。配信ファイルは個別に25 MiB未満です。

作品だけを確認する場合：

```bash
python3 -m http.server 8421 --directory .
# http://127.0.0.1:8421/alhambra/public/
```

## 操作

- WASD / 矢印：移動。Shift：速く移動。風景をドラッグ：見回す。
- 徒歩は壁・柱・水盤を避け、床と階段に沿って移動。飛行は自由移動、Q/Eで下降・上昇。
- 全景ではドラッグで回転、ホイールで距離を変更。
- 下部ナビの「見どころ」（徒歩・飛行の右）で場所リストを開く。15地点。全景は「15 アルハンブラ全景」から。URLの `?place=sisters#ja` などで直接到着。
- 画面下の場所タイトル（「実際の写真」）をクリックすると、その場所の参考写真を表示。全15地点・28枚。複数枚ある場所では左右のボタン／矢印キーで切り替え、Esc・×・背景クリックで閉じる。同じ3D視点から見学を続けられる。
- 自動案内は全15地点を各4秒、約1分で巡って終了する。各地点では専用の移動経路に沿って約2.7〜10m前進・横移動・回り込みを行い、同時に見上げる対象を変える。全景は旋回しながら接近する（動きを減らす設定時は固定）。経路は徒歩と同じ衝突判定で検証する。徒歩操作・ドラッグ・Escで停止。
- M：地図拡大、H：UIの表示切替。午後／夕暮れ、音声オン／オフ、日本語／英語。
- タッチ端末は左下のスティックで移動、画面スワイプで視点。`?q=low` は軽量プロファイル。

## 実装

| ファイル | 内容 |
| --- | --- |
| `tools/web/palaces.js` | ナスル朝宮殿、ムカルナス、ライオンの噴水、庭園、カルロス5世宮殿 |
| `tools/web/exterior.js` | 城壁、アルカサバ、歩ける階段、市街の外形、地形・植栽 |
| `tools/web/materials.js` | タイル、漆喰、組紐、文字帯などのテクスチャとノーマルマップ |
| `tools/web/geometry.js` | 柱・アーチ・壁などの建築部品、インスタンシングと結合 |
| `tools/web/navigation.js` | 床、階段、壁・水盤の衝突。移動を小刻みに分けて壁抜けを防止 |
| `tools/web/main.js` | Three.js、影、水面反射、徒歩・飛行・全景、案内、地図、UI |
| `tools/web/references.js` | タイトルから開く参考写真、前後切替、撮影者・ライセンス表示 |
| `tools/prepare_context.py` | ダウンロードしたOSMデータをローカル座標へ変換 |
| `public/data/context.json` | 城壁と周辺1,662棟の外形、ODbLの派生データベース |
| `public/credits.html` | 復元範囲、精度上の制限、全資料、ライセンス |
| `public/data/references.json` | 15地点の参考写真、日英の説明、撮影者、出典、画像ごとのライセンス |
| `public/photos/`, `public/photo-credits.html` | 同梱の実写写真23枚（WebP）と全写真のクレジット |

アプリのソースを変更した場合：

```bash
npm --prefix alhambra/tools install   # 初回。Three.js 0.186.1 / esbuild 0.28.1
node alhambra/tools/build_web.mjs
node --test alhambra/tools/navigation.test.mjs
node alhambra/tools/snap.mjs /tmp/alhambra.jpg --verify
npm run build
```

この作業環境では既存の `vatican/tools/node_modules/three` とルートの esbuild をビルド時の代替として使えます。実行時の別作品への依存はありません。`snap.mjs` は既存作品と同様にローカルのGoogle Chromeで実GPUの描画を検証します。`--verify` は実際の3Dシーンの見学地点と徒歩経路を検証し、失敗時は非0終了します。W/H環境変数で撮影サイズを指定できます。

検証済み：ナビゲーションの5テスト、14か所の徒歩開始位置、12本の実シーン内の徒歩経路（ナスル朝宮殿内・ベラの塔の上り下り・ヘネラリフェからパルタル）、390 × 844のタッチエミュレーション、既存ギャラリーのテストと全体ビルド、`wrangler deploy --dry-run`。実機のスマートフォン性能までは測定していません。参考写真のWebPはタイトルを開いた時に読み込みます。詳細2室の材質に使うJPEG6点は初期ロード時に読み込みます。

参考写真ビューアーは、当初の15地点・23枚の読み込み、日英の説明と出典、前後切替、Esc・背景クリック、フォーカス復帰、表示中の移動防止、自動案内の停止を確認済みです。1600 × 900と390 × 844のタッチエミュレーションで表示を確認しています。写真を開いている間は3D描画を一時停止します。

## 図面と精度

基本資料は [Torres Balbásのライオンの中庭1:100平面図（P-000158）](https://www.alhambra-patronato.es/ria/handle/10514/3669)、[Goury / Jonesの実測図集（1842–1845）](https://www.alhambra-patronato.es/ria/handle/10514/6005)、[公式の全体図](https://www.alhambra-patronato.es/wp-content/uploads/2020/10/Plano_General.pdf)、公式の各室解説、OpenStreetMapです。[資料の対応表](tools/research/README.md)に図版と参照箇所を記録しています。

現在の外観を対象とした**解釈復元**です。測量済みCADやスキャンではありません。ライオンの中庭の寸法と部屋の関係を縮尺図から参照し、柱廊に124本の柱を配置しています。ムカルナスは小さな凹型ニッチを重ねた近似構成で、実物の全ピースの転記ではありません。彫像、装飾パターン、補助室、兵営跡、階段、地形、植栽、建物高さにも推定が含まれます。コマレス浴場全体と諸王の間の天井画は未収録です。

研究用に取得した図面PDF・JPEGは `tools/research/` に保存し、Gitと配信から除外します。公式のデジタル資料画像をテクスチャとして再配布しません。さらに精度を高める際は、現代の断面測量・点群・利用許諾を確認したスキャンで、個々の部屋や装飾を差し替えられる構成です。

## 大使の間・二姉妹の間の精細化

`tools/web/detail-rooms.js` と `detail-materials.js` に専用の形状と材質を分離しています。低画質でも同じ装飾素材・天井形状を使います。大使の間は9つの窓アルコーブ、各面5つの高窓、段階的に傾斜する木天井、赤褐色の床。二姉妹の間は八角形の窓列16窓、正方形から八角形への移行部、凹型の装飾を重ねた天井です。室内の間接光を抑え、窓からの補助光と局所的な静的シャドウを加えています。

写真由来の材質6点の配信用JPEGと機械可読の帰属情報は `public/textures/`、表示用の出典は `public/texture-credits.html`。各CC BY-SA派生材質は元のライセンスを維持します。5点は対象室の装飾写真、汎用漆喰1点はライオンの中庭のCC0写真であり、位置まで一致する複製ではありません。写真に残る陰影、投影歪み、反復模様の継ぎ目、推定形状の限界があります。天井の全ピースや碑文の全文は未転記で、写真測量モデル相当の精度とは区別しています。

追加素材はCommonsの1920ピクセル版JPEGを同梱し、6点合計約6.1 MBに抑えています。追加素材のための外部リクエストは実行時に発生しません。

### Evening and extended palace details

The default is now evening (low warm sunlight, cool sky fill, long architectural and foliage shadows); the existing light button still switches to afternoon. This is an artistic light setup, not a date-specific solar simulation. Low quality retains detailed ornaments and one nearby 512 px water reflection; high quality uses 1024 px. Only the nearest of the Myrtles, Partal and Generalife pools reflects the scene at a time.

`extended-materials.js` reuses locally bundled reference images for Mexuar tilework, Lindaraja tiles/glazing, carved timber and the central Kings painting. Generic Nasrid stucco and inscriptions use the previously documented photo materials as analogues, not exact transcriptions. `landscape-detail.js` adds instanced foliage, exposed portico joists, pavilion timber, and Charles V gallery cornices/railings. Abencerrajes now has its own eight-point star drum and concave muqarnas reconstruction. Source licences and limitations are recorded in `public/texture-credits.html` and `public/textures/extended-credits.json`. No new runtime service or installation is required; all assets remain local static Worker assets.

### Real terrain, the city and trees (2026-10-23)

The ground, the city and the trees are generated offline by `tools/gen/` (Python 3 with numpy, scipy, shapely 2, pyproj and Pillow; the environment variable `ALHAMBRA_ASSETS` points to the raw data folder, by default `/home/kazu/work/alhambra-assets`):

| Step | Input | Output |
| --- | --- | --- |
| `dem.py` | IGN MDT05/MDT25/MDT200 tiles from the WCS `servicios.idee.es/wcs-inspire/mdt` (CC BY 4.0) in `dem/near5`, `dem/mid25`, `dem/far200` | sampler in the local frame (cached `cache/dem.npz`) |
| `osm.py` | Overpass extract `osm/granada.json` (ODbL) | parsed geometry (cached `cache/osm.pkl`) |
| `terrain.py` | DEM + OSM landcover | `public/data/terrain.bin` (4 nested grids: 5 m, 20 m, 120 m, 400 m, out to the Sierra Nevada), `ground0.jpg` / `ground1.jpg` (landcover colours), `rivers.json` |
| `city.py` | OSM buildings, parts (cadastre levels), walls | `public/data/city.bin` (≈ 26,000 volumes, ≈ 0.7 M triangles: walls with storey UVs, tiled hip/gable roofs with eaves, terraces, inferred bell towers, the Albaicín walls) |
| `trees.py` | OSM trees, rows, woods, parks, orchards + the gaps of the Albaicín | `public/data/trees.bin` (≈ 100,000 trees in 11 species) |

```bash
cd alhambra/tools/gen
python terrain.py && python city.py && python trees.py
```

The plateau keeps its modelled level (y = 0 = 774 m). The DEM is blended into it within 4–14 m outside the enclosure and around the Generalife model. The viewer draws the two inner grids, the city and the trees in the main pass. The Vega and the Sierra Nevada (out to ≈ 40 km) are drawn in a separate far pass with their own depth range, and the sky is drawn there too. A 256 px cube of that far pass is the background for the water reflections. Haze is exponential, not squared, so the mountains stay visible.

Facades are drawn in the shader from a canvas atlas of 10 styles, one storey at a time, so the ground floors (doors, rejas, zócalo) never repeat upstairs. Bays are scaled per wall to whole windows. Trees (`tools/web/trees.js`) use leaf-card crowns with volumetric normals in two template LODs, re-binned around the camera. Every tree also has a camera-facing impostor, rendered at load time from its own template. The hand-built gardens add their trees with `plant(x, y, z, species, height)`.

The outdoor monuments now live in `tools/web/heroes/`: `alcazaba.js`, `carlos.js`, `partal.js`, `gates.js` (Justicia, Vino, Aljibes), `walls.js` (enclosure and towers), `grounds.js` (Calle Real, Santa María, Parador, Secano) and `generalife.js`. Each module exports `materials(M)` and `build(b, ctx)`. A failing module is logged and skipped.

Rendering load: shadow maps are re-rendered only when the camera or the light moves. The pixel ratio adapts between 1.0 and 1.6 (0.7–1.0 on phones) to keep frames under ~24 ms; `?pr=1` disables this. `ALH.bench()` times frames with `gl.finish`, and `?timing=1` logs the start-up phases. The texture credits of the hero modules are collected by `python3 tools/hero_credits.py`. Known gap: the Generalife model stands about 35 m south of its OSM position, inherited from the first version.

### Evening light, horizon and load (2026-10-23)

Evening now uses a sun about 12° above the west-south-west horizon (previously about 19°, which read as afternoon), with a warmer, denser sky. The far plain sits just below the terrain edge, so the overview no longer shows a cliff where the model ends. Distant foothills are unlit and pre-hazed, and an interpretive Sierra Nevada skyline with snow caps sits about 5 km to the south-east. It is not measured topography. Flower petals and their centres use 20-triangle buds and cast no shadows. Rendered triangles fell from about 12.7M to 6M (high, overview) and from 7.1M to 3.9M (touch/low, Court of the Lions). The Hall of the Kings arrival point now stands clear of the first arch. Its columns stand free of the walls, and its fill light is off the arch plane. The header has a stronger paper scrim and a halo, so it stays legible over stucco. `ALH.pick(x,y)` (viewport 0–1) and `ALH.heavy()` are debug hooks for material picking and triangle budgets.

### Abencerrajes dado

The Abencerrajes walls previously reused the generic Nasrid zellige dado. They now carry the room's own 16th-century Sevillian cuerda-seca azulejos and the blue-filleted border above them. Both come from R Prazeres' frontal photograph (CC BY-SA 4.0, credited in `texture-credits.html`). `tools/abencerrajes_tiles.py` derives `public/textures/abencerrajes-dado.jpg` (4 × 2 pattern units of about 28 cm) and `abencerrajes-border.jpg`. It resamples the foreshortened units to square and divides out the photo's lighting falloff, so the repeat is seamless. The source JPEG is kept in `tools/research/`, which is excluded from git and delivery. The upper walls and window drum use the room's own rosette and blue-cross stucco lattice, derived from Jebulon's public-domain photograph (`abencerrajes-stucco.jpg`, units of about 78 cm). The muqarnas cells are chalk-white plaster. About one cell in four is in deeper shade and one in twelve carries faded blue paint, picked per cell rather than mapped from a photo patch. The colours follow José Luis Filpo Cabana's view of the vault from below. Cell shapes remain an interpretive reconstruction.

### Two Sisters vault colour

The Two Sisters vault now has the same per-cell treatment as the Abencerrajes. Cells are warm ivory, about one in four is a deeper ochre recess, and about one in fourteen has faint green-turquoise paint. The eight-cell rosettes have ochre crowns. Odd tiers are offset by half a cell, so the cells interlock instead of forming concentric rings. The drum, the transition zone and the upper walls use a warm-tinted stucco (`sisStucco`) in place of the grey analogue and the brown exterior material. The colours follow R Prazeres' photograph of the vault, which is already in the reference gallery. Cell geometry remains interpretive.

The Two Sisters walls now use the room's own carved sebka lattice. `tools/sisters_stucco.py` derives `sisters-sebka.jpg` from a wall panel in the bundled hall photograph, and it is mirrored at its edges at runtime. The lattice covers the wall field and the carved registers, with a strong bump. Hanging muqarnas fans spill from each upper corner over both walls, and a lobed curtain sits over each central window. Pendants hang from their lower tiers, and the fillets use a warm carved trim (`sisTrim`) instead of the shared grey lime. The fan layout follows the photograph by eye.

### Court of the Myrtles proportions

The pool is 34 × 7.1 m and the myrtle hedges approximately 2.35 m wide × 1 m high, following the Patronato's [Patio de los Arrayanes](https://www.alhambra-patronato.es/patio-de-los-arrayanes). The previous pool was only 30.5 m long. The default view now stands on the south centre axis; the court itself has not been stretched. Side doors, their carved surrounds and paired upper lattice windows follow the bundled photograph, with approximate positions. Additional side chambers remain closed; existing east/west routes are preserved.

## BGM

右上の「♫」からアストゥリアスのギター向け簡略編曲（約5分37秒）を再生・一時停止できます。音量を保存し、曲末から自動リピートします。水の環境音は「≋」で独立して切り替えます。起動時に音楽の再生を試み、ブラウザーの自動再生制限がある場合は最初のクリック・キー操作で開始します。一時停止後は操作しても再開しません。場所リストは「見どころ」で開き、場所を選ぶと閉じます。制作・再生成手順は `tools/music/README.md`、公開クレジットは `public/credits.html#music` にあります。

## 紹介動画

ギャラリーの「紹介動画 · Film」から `public/film.html` を開きます。`public/movie/alhambra.mp4` は60秒、1280×720、24fps、H.264 / AAC、約13.3 MB。スマホのインライン再生と先頭からの逐次読み込みに対応します。映像は全15地点を4秒ずつ、アプリの移動経路で収録し、アストゥリアスの簡略ギター編曲をBGMにしています。

再生成（Chrome・ffmpeg使用、追加パッケージ不要）:

```sh
node alhambra/tools/build_web.mjs
node alhambra/tools/film/render.mjs scout /tmp/alhambra-film
node alhambra/tools/film/render.mjs render /tmp/alhambra-film
node gallery/build.mjs --skip-prebuild
```

中間フレームは `/tmp/alhambra-film`、公開MP4とポスターは `public/movie/` に保存します。`?film=1` のときだけ描画時計を固定し、各フレームを指定時刻で描きます。通常のアプリの自動案内には影響しません。

Workersでは `/media/movies/alhambra-film/video.mp4` が同梱静的ファイルを配信し、Safari等の途中再生に必要なHTTP Range（206）に対応します。R2への別アップロードは不要です。単純な静的プレビューではMP4直リンクへフォールバックします（途中再生の可否はプレビューサーバーのRange対応に依存）。
