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
- 場所メニューに15地点。URLの `?place=sisters#ja` などで直接到着。
- 画面下の場所タイトル（「実際の写真」）をクリックすると、その場所の参考写真を表示。全15地点・28枚。複数枚ある場所では左右のボタン／矢印キーで切り替え、Esc・×・背景クリックで閉じる。同じ3D視点から見学を続けられる。
- 自動案内は約14秒ごとに見学地点を切り替える。徒歩操作・ドラッグ・Escで停止。
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

### Court of the Myrtles proportions

The pool is 34 × 7.1 m and the myrtle hedges approximately 2.35 m wide × 1 m high, following the Patronato's [Patio de los Arrayanes](https://www.alhambra-patronato.es/patio-de-los-arrayanes). The previous pool was only 30.5 m long. The default view now stands on the south centre axis; the court itself has not been stretched. Side doors, their carved surrounds and paired upper lattice windows follow the bundled photograph, with approximate positions. Additional side chambers remain closed; existing east/west routes are preserved.
