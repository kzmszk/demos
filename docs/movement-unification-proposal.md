# 移動操作（歩行・飛行）共通化の設計提案

対象：venice / kyoto / alhambra / vatican の4都市。書いた日：2026-10-29（同日、オーナー決定と「将来のマルチユーザー対応」の前提を受けて改訂し、Codex の第2回レビューを反映して最終化）。このドキュメントは設計だけを扱い、実装はまだしていない。

## 要約

- リポジトリ直下に `shared/move/` を作り、各都市の `tools/web/*.js` から相対パス（`../../../shared/move/…`）で import して esbuild に同梱させる。npm パッケージ化やテンプレート複製はしない（§3.1, §5.2）。
- 共通モジュールは **three に依存しない**素の JS にする。`shared/` からは都市ごとの `node_modules` を解決できず、`three` と `three/webgpu` も混在しているため（§3.1）。カメラの読み書きは都市側が渡すビューアダプターに任せる。
- 共通部分を**コア**と**殻**に分ける。コア（`step`／`command`）は外部に副作用を持たない更新関数で、DOM・three・時刻・乱数・モジュール変数に触れず、状態・入力・コマンドはプレーンなデータにする。殻（`Mover`）は DOM のイベントを入力に変え、カメラと状態を受け渡す。目的は、将来サーバー側で同じコアを複数アバター分動かせる**再生可能な境界**をいま作ること。作業量は単純な共通化より明らかに増える（§3.5 (6)）。
- 共通にするのは入力の集約と解除、視点（yaw/pitch）、飛行の積分、ラスター歩行の共通部分（螺旋探索・高さ追従・揺れ・速度の補間）。通行判定は venice の strict と kyoto の glide を**別の戦略**にする。ゴンドラ、ツアー、オービット、alhambra の `Navigation`、UI の DOM は都市側に残す。
- 移行順は vatican → kyoto → venice → alhambra。共通部分は段階的に入れ、kyoto の後で API を見直す。alhambra は入力・視点だけで止めてもよい。
- **各都市は2コミット**：「挙動を保つ移行」→「操作変更（決定①②）」。検証は一つの表（§4.0）にまとめ、比較の基準版と許容誤差を固定する。
- **オーナー決定（2026-10-29）**：
  - ①**フレームレート依存の旋回は直す。** venice 1.2、kyoto 1.5 rad/s に換算（60Hz では変化なし）。
  - ②**ドラッグ方向は全都市をアルハンブラ方式（景色をつかむ方式）に揃える。** venice/kyoto/vatican で体感が反転する。符号は `input.js` 内の定数に閉じ、都市の設定にも公開 API にも出さない。移行コミットの間だけ旧符号を使う一時的な口を置き、全都市の操作変更が済んだら消す（§3.4）。
- **マルチユーザーへの備えの範囲**：いま作るのは「コア／殻の分離」「状態・入力・コマンドのプレーンデータ化と受け渡しの契約」「コアの純粋性の試験」。固定タイムステップ、互換性の識別子、`WalkGrid` は移行の後で、どの権威モデルを採るかによって要否が変わる（§3.5 (5)）。再現性について約束するのは「同じ初期状態・cfg・世界データ・tick ごとの入力とコマンド・時間処理がそろえば、同じ実装で同じ状態列になる」ことまで。固定ステップだけで軌跡が一致するとは主張しない（§3.5 (1)）。
- 最大の収穫は、ほぼ同じ内容の venice/kyoto の `controls.js`（118行と149行）の重複（入力・補間・揺れ・探索）を一本化すること。

---

## 1. 調査結果（4都市の現状）

以下の file:line はすべて作業ツリー上で実際に読んで確認したもの。推測や未確認の点は「未確認」と明記した。sparse checkout で作業ツリーに展開されていないファイル（`wrangler.jsonc`、`gallery/`、各都市の `demo.json` と `.gitignore`）は `git show HEAD:<path>` で読んだ。

### 1.1 venice — `venice/tools/web/controls.js`（118行）

| 項目 | 内容 | 根拠 |
|---|---|---|
| モードと切替 | `fly`（初期値）/ `walk` / `boat`。`app.setMode` → `controls.setMode`。boat→walk でゴンドラ位置に降り、boat→fly で `syncFromCamera()` | controls.js:1-3, :10, main.js:117-125 |
| キー | `e.code` の `Set`。W/S・↑/↓ 前後、A/D 横、←/→ **旋回**（0.02 rad/フレーム）、E/Space 上、Q/C 下、Shift。INPUT/SELECT では無視、blur でクリア | controls.js:25-27, :39-51 |
| ドラッグ・ホイール | mouse 0.003 / touch 0.005。pointerId を照合し pointercancel も処理。pitch の制限は**イベントごと**。ホイールは fly のときだけ速度を ×0.85/×1.18（1〜300）で、`enabled` を見ない | controls.js:13-24, :28 |
| タッチスティック | DOM は main.js。`controls.move.{x,y}` に -1..1。ポインターロック・ゲームパッドは4都市とも無い | main.js:324-334, controls.js:11, :49 |
| 歩行 | 1.45 m/s（Shift 3.6）、`vel.lerp(want, 1-exp(-8dt))`。高さは `walkZ += (z-walkZ)*min(1,12dt)`、EYE=1.62 に揺れ（0.012）。重力・ジャンプは無い | controls.js:5, :92-107 |
| 歩行の衝突 | `tiles.sample` の z：通れない所で null、未ロードで undefined。半径 0.24 の5点が歩行可能で段差 0.55 以内なら移動、だめなら X だけ・Y だけ、それもだめなら停止 | controls.js:53-64, :97-102, tiles.js:324-335 |
| 歩行の開始 | `walkZ=null` のとき半径 40 m まで螺旋探索。未ロードなら return して待つ（旋回キーの yaw はその前に進む） | controls.js:66-73, :83-91 |
| 飛行 | 速度 12、Shift ×4、滑らかさ 4。前進は pitch に追従しない。地面との衝突は無い | controls.js:108-113 |
| カメラ・boat | z-up、`cam.up=(0,0,1)` と `lookAt`。boat は `ride.seatPose(cam, boatYaw, boatPitch)`、手漕ぎでは `ride.steer` に入力、見回しは ±2.6/±1.0 | controls.js:21, :77-82, :114-116, gondola.js:256-263 |
| 外部との結合 | R キー（main.js:296-298）、ミニマップ（:372）、音が `controls.vel`（:310）、film_page.js が `vel.set()` と `enabled=false`（:55, :74, :83, :108, :119）、`VEN.walkAt/look`（main.js:395, :398） | 左記 |
| 既存のチェック | `bridge_check.py` が controls.js に倣った規則（docstring は半径 0.25 m・段差 0.55 m。実際の R は 0.24）で全橋を検査する。**定数を変えたら合わせる** | bridge_check.py:1-7 |

### 1.2 kyoto — `kyoto/tools/web/controls.js`（149行）

venice の controls.js から派生したとみられ、構造はほぼ同じ。違いだけ挙げる。

| 項目 | 内容 | 根拠 |
|---|---|---|
| モードと切替 | `walk`（初期値）/ `fly`。walk→fly でカメラを +1.5 m 上げる | controls.js:1-2, :11, main.js:99-103 |
| 入力の追加分 | `vert`（▲▼）と `fastLatch`（高速トグル）を ui.js が書く。旋回 0.025 rad/フレーム。ホイール 2〜600（fly のみ、`enabled` を見ない） | controls.js:13, :28, :44-49, ui.js:96-107 |
| 歩行 | 1.5 m/s（Shift 4.2）、滑らかさ 8、高さ追従 10dt、EYE=1.6、揺れは venice と同じ式 | controls.js:6, :97-134 |
| 歩行の衝突 | `tiles.sample` が `{z, blocked, water, covered, surf}`。R=0.12、UP=0.75、DOWN=1.2。`cost/can` で壁に向かう方向以外は動ける判定、だめなら ±0.35/0.7/1.2 rad 回して滑る（glide）、開口部へ横歩き、最後に軸ごと。blocked セルの中では高さを保つ移動を許す（`through`） | controls.js:4-6, :51-77, :102-131, tiles.js:193-203 |
| 歩行の開始 | 螺旋探索の半径 60 m | controls.js:78-85 |
| 飛行 | 速度 30、Shift ×4、滑らかさ 4。前進が pitch に追従。**地面から 2.0 m 以上を保つ**（歩行マップ、無ければ `farGround`） | controls.js:135-144, main.js:323 |
| 外部との結合 | ミニマップ（main.js:426）、音（:349）、film_page.js（:55, :74, :107, :117）、`KYO.walkAt/look`（:447, :450）、`goPlace` が `yaw/pitch/walkZ` を設定（:104-111）。`covered` は露出制御だけで移動に使わない（:419） | 左記 |
| 既存のチェック | **移動の自動検査は無い** | — |

### 1.3 vatican — `vatican/tools/web/fly.js`（42行）

| 項目 | 内容 | 根拠 |
|---|---|---|
| モード | `FlyControls` は飛行だけ。アプリ側に `title` / `tour` / `free` があり、`free` のときだけ `enabled=true`。F キーで切替 | fly.js:4, main.js:137-148, :170 |
| 入力 | W/S・↑/↓ 前後、A/D・←/→ **横移動**、E/Space 上、Q/C 下、Shift ×4、ドラッグ 0.0035。**pointerId の照合、pointercancel、blur での解除、入力欄の除外が無い**（index.html に入力欄自体が無い）。ホイールは 2〜400 で、**モードも `enabled` も見ずに**速度を変え、常に `preventDefault` | fly.js:11-20, :28-36, index.html |
| タッチ | ドラッグで見回すだけ。スティックが無く、タッチ端末では free モードで移動できない（コード上。実機は未確認） | index.html:11, :73 |
| 物理・カメラ | 滑らかさ 3、前進は pitch に追従しない。衝突・地面・範囲制限は無い。z-up（`DEFAULT_UP`）で `lookAt`、`cam.up` は設定しない | fly.js:37-40, main.js:11, :28 |
| 外部との結合 | ツアーは `poseAt(seg,t)` でカメラを直接置き、その間 controls は止まる。屋内外の切替は `world.update(camera.position)`。`VAT.look/stopLoop` が `syncFromCamera/enabled` を触る | tour.js:162-173, main.js:181-192, :233-240, :275-276, world.js:43-51 |
| ビルド | `build_web.mjs:2` が esbuild を **`/home/kazu/work/demos/node_modules/...` の絶対パス**で import し、package.json に esbuild が無い。**このままでは他の環境でビルドできない**（実行しては確かめていない） | build_web.mjs:2, package.json |
| 既存のチェック | snap.mjs だけ | — |

### 1.4 alhambra — `alhambra/tools/web/main.js` と `navigation.js` に埋め込み

| 項目 | 内容 | 根拠 |
|---|---|---|
| モード | `walk` / `fly` / `orbit`（orbit は `overview` 地点への移動）。walk に入るとき、床が 6 m 以上下にあるか塞がっていれば地点の定位置に戻す | main.js:34, :73-80, :84 |
| キー | **`e.key.toLowerCase()`**。W/S・↑/↓ 前後、A/D・←/→ **横移動**、E/Q 上下（fly のみ）、Shift ×2.4。`preventDefault` し、キーでツアーを止める。ダイアログ中や INPUT/TEXTAREA/SELECT では無視。blur と visibilitychange でクリア | main.js:131-137, :177-182 |
| ドラッグ | `yaw += dx*.003; pitch += dy*.003`（±1.48、イベントごと）を `camera.rotation`（YXZ）に直接入れる。**他の3都市と yaw も pitch も符号が逆**の「景色をつかむ」方式（main.js:128 のコメント）。orbit では `orb.theta -= dx*.004` | main.js:127-130 |
| タッチ | `#joystick`（半径 24px）→ `stick`、`#rise/#descend` → `alt.value`。スティックでツアーを止め、orbit なら walk に切替 | main.js:138-142 |
| 歩行・衝突 | 2.3 m/s、Shift ×2.4、**滑らかさ無し**（入力がそのまま変位）、EYE=1.65。**幾何モデル**：`Navigation` に箱・床・斜面・建物外形・地形関数を登録し、`move` は 0.14 m ごとに X と Z を別々に試す（上り 0.43、下り 0.9、半径 0.23） | main.js:177-182, :207, :221, navigation.js:1, :24-69 |
| 飛行・カメラ | 範囲の箱と y∈[地形+0.7, 850] に制限。**y-up**、`camera.rotation.set(pitch,yaw,0,'YXZ')`、`orientation()` で読み戻す | main.js:72, :128, :182 |
| ツアー・ミニマップ | 4秒×15地点。`buildTourShots` が**歩行と同じ `nav.move` で経路を掃く**。update でカメラを直接置く。`drawMap()` は `camera.position` と変数 `yaw` を読む | tour.js:19-28, main.js:110, :156-174, :288-292 |
| 既存のチェック | **3種類**：①`navigation.test.mjs`（node --test）②`check-walks.js` と `walk-routes.json`（`snap.mjs --verify` で実シーンを `ALH.move` で歩く）③snap.mjs が毎回 `ALH.placeCheck()` | snap.mjs:46-48 ほか |

### 1.5 配信形態とサーバー側での再現に関わる事実

| 項目 | 内容 | 根拠 |
|---|---|---|
| 配信 | 4都市とも、ギャラリー全体と同じ **1つの Worker（`name: "demos"`）の静的アセット**。Worker のコードが動くのは `/api/*` と `/media/*` だけ。都市専用の Worker・Durable Object・WebSocket は無い | wrangler.jsonc、gallery/worker.js:1, :273-279 |
| デプロイ経路 | `npm run deploy` = `node gallery/build.mjs && wrangler deploy`。4都市の demo.json は `serve: "public"` で `prebuild` を持たないので、**デプロイでは都市を再ビルドせず、コミット済みの `public/app.js` がそのまま配信される** | package.json、gallery/build.mjs:4-7, :82-89、各 demo.json |
| タイルデータ | venice `public/data/island/`（約 330 MB）、kyoto `public/data/city/`（約 0.9 GB）は**git の外**で、デプロイはローカルのコピーを使う。歩行ラスター（`<tile>.walk.png`）もこの中 | 各 .gitignore、venice tiles.js:70, :268 |
| 歩行ラスターの復号 | `createImageBitmap` + `OffscreenCanvas`。Workers にこの2つがあるかは**未確認**（無い前提で設計する） | venice tiles.js:268-277、kyoto tiles.js:72-76, :182-185 |
| alhambra の衝突形状 | シーン構築（`Builder`）の過程で登録される。地形の高さは `navigation.js` の**モジュール変数** `ground` に `setTerrainSampler` で差し込まれる | main.js:207, :211, :221, :241、navigation.js:11-12 |
| 時間の扱い | 移動のコードは `performance.now`・`Date.now`・`Math.random` を使っていない（grep）。時間は各都市のループが渡す dt だけ。dt の上限は venice/kyoto/vatican が 0.1 s、alhambra が 0.05 s で、**上限を超えた分は捨てられる**（経過時間を上限で丸めるだけで持ち越さない。非表示からの復帰直後も上限ぶんだけ進む。alhambra は非表示の間 update を呼ばない） | venice main.js:376、kyoto :430、vatican :255、alhambra :272 |
| 時刻に依存する周辺機能 | alhambra のツアーは `performance.now()`、vatican のツアーは音の時計。どちらも移動のコアの外 | alhambra main.js:88, :157、vatican :188 |

### 1.6 確認できなかったこと

- **ビルドを実際に実行していない。** 作業ツリーに `node_modules` が無い。§3.1 の解決順の議論は、esbuild の仕様とビルドスクリプトの記述からの推論。
- 実機での操作感とタッチ端末での挙動は見ていない。決定②の体感も実装後に実機で確かめる。
- 歩行ラスターだけの合計サイズ、Workers／DO のメモリー上限やアセットの上限は未確認。マルチユーザー化に着手するときに、その時点の公表値で確かめる。
- kyoto controls.js:103 のコメント「after a jump」は地点への瞬間移動の後を指すと読める（ジャンプのコードは無い）。意図は未確認。

---

## 2. 共通点と相違点

「決定」列の印：①＝旋回の修正、②＝ドラッグ方向の統一（§3.4）。

| 観点 | venice | kyoto | vatican | alhambra | 決定・扱い |
|---|---|---|---|---|---|
| 上方向 | z | z | z | **y** | ビューアダプターで吸収 |
| モード | fly / walk / boat | walk / fly | fly（アプリ側に tour / free） | walk / fly / orbit | boat・orbit は都市側 |
| キーの識別 | `e.code` | `e.code` | `e.code` | **`e.key`** | 設定（`keyField`） |
| ←/→ | 旋回（0.02/フレーム） | 旋回（0.025/フレーム） | 横移動 | 横移動 | ① 秒あたり（1.2 / 1.5 rad/s）に |
| 上昇 / 下降 | E,Space / Q,C | E,Space / Q,C + ▲▼ | E,Space / Q,C | E / Q + ▲▼ | 設定（`bindings`） |
| Shift | 歩行 ×2.5、飛行 ×4 | 歩行 ×2.8、飛行 ×4、ラッチ | ×4 | ×2.4 | 設定 |
| ドラッグの符号 | 見回す方式 | 見回す方式 | 見回す方式 | **景色をつかむ方式** | ② 全都市を景色をつかむ方式に（input.js の定数） |
| ドラッグの係数 | mouse .003 / touch .005 | 同左 | .0035 | .003（orbit .004） | 都市ごとのまま |
| pitch の制限 | ±1.5 | ±1.5 | ±1.5 | ±1.48 | 都市ごとのまま（イベントごとに掛ける） |
| タッチスティック | あり | あり（同じコード） | **なし** | あり（HTML の DOM） | vatican への追加は別作業 |
| ホイール | 飛行速度 1〜300 | 飛行速度 2〜600 | 飛行速度 2〜400（常に） | orbit の距離 | 設定 / モードの `wheel` |
| 速度の滑らかさ | 歩行 8、飛行 4 | 歩行 8、飛行 4 | 3 | **なし** | 設定（`smooth`、null＝即代入） |
| 歩行の速さ / 目の高さ / 揺れ | 1.45・3.6 / 1.62 / あり | 1.5・4.2 / 1.6 / あり | — | 2.3・5.5 / 1.65 / なし | 設定 |
| 地面の取得 | 歩行ラスター（z / null / undefined） | 歩行ラスター（z / blocked ビット） | — | 地形関数 + 床・斜面の幾何 | 世界クエリとして注入 |
| 衝突 | 5点 + 段差 ±0.55、軸ごと | 5点 + UP .75 / DOWN 1.2、glide・横歩き・through | なし | 箱・外形、細分移動、上 .43 / 下 .9 | strict / glide 戦略、alhambra は Navigation |
| 飛行の地面制限 | なし | 地面 +2 m | なし | 地形 +0.7 m と範囲の箱 | `clamp`（純粋関数） |
| 飛行の前進方向 | 水平のみ | pitch に追従 | 水平のみ | 水平のみ | 設定（`followPitch`） |
| dt の上限 | 0.1 s | 0.1 s | 0.1 s | 0.05 s | 都市のループ側（§3.5 (1)） |
| 外部から触る口 | VEN.controls / walkAt / look、film_page | KYO.controls / walkAt / look、film_page、ui.js | VAT.look / stopLoop | ALH.move / go / look / tourCheck / placeCheck | 互換プロパティ |

**共通にできる部分**：キーの集約（blur での解除、入力欄の除外）、ドラッグ（係数、pitch の制限、pointerId の照合、②により符号も）、yaw/pitch とカメラの相互変換（`syncFromCamera` は3都市で同一）、ホイールでの速度変更、速度の指数的な滑らかさ、飛行の積分、タッチスティックの値、歩行の揺れ、ラスター歩行の螺旋探索・高さ追従・速度の補間。

**入力の合成は都市ごとに違う**：venice/kyoto は f/r を成分ごとに ±1 に丸め、水平の正規化は歩行だけ（飛行の斜めは √2 倍まで出る）。kyoto は上下も `u+vert` を丸める。vatican は丸めも正規化も無い。alhambra は丸めずに足し、水平2成分を長さ1以下に正規化し、上下は `キー+alt` をそのまま足す（main.js:177-182）。共通化ではこの順序を設定で再現する。

**都市側に残す部分**：地面の表現、座標系、ゴンドラ・オービット・ツアー、キーの割り当て、速度などの定数。

---

## 3. 設計

### 3.1 置き場所と取り込み方

```
demos/
  shared/
    move/
      index.js          # 公開 API の再エクスポート
      # ── コア（DOM・three・時刻・乱数・モジュール変数を使わない。node と Worker で動く） ──
      state.js          # MoverState / InputFrame / Command の形、createState、toPlain/fromPlain、版の定数
      step.js           # step(state, frame, dt, world, cfg) と command(state, cmd, world, cfg)
      vec.js            # 小さな Vec3（フィールドは x/y/z だけ。set/lengthSq/lerp）
      fly.js            # 飛行の積分
      raster-walk.js    # ラスター歩行の共通部分（補間・螺旋探索・高さ追従・揺れ）
      walk-strict.js    # 通行判定：venice 方式（5点すべて + 軸ごと + 停止）
      walk-glide.js     # 通行判定：kyoto 方式（cost/can・through・glide・横歩き・半減）
      # ── ブラウザーの殻（DOM と camera に触るのはここだけ） ──
      input.js          # キー・ドラッグ・ホイール・タッチ値 → InputFrame と Command
      view.js           # 状態 ⇄ カメラのアダプター（z-up の lookAt 型、alhambra の Euler 型）
      mover.js          # 殻：入力 → command/step → ビュー、クライアント専用モード、互換プロパティ
      stick.js          # （任意）venice/kyoto で同じタッチスティック DOM の補助
      build-users.mjs   # shared を使う都市の一覧と、各都市の build_web.mjs を正しい cwd で実行する入口
      *.test.mjs        # node --test
```

各都市からは `import { Mover, flyMode } from '../../../shared/move/index.js';` のように読み込む。

- 4都市とも `bundle: true` と `entryPoints: ['web/main.js']` を使う（venice・kyoto build_web.mjs:4、alhambra :11-13、vatican :4-8）。esbuild は相対 import ならエントリーの外のファイルも取り込むので、**`shared/` を解決するためのビルド設定の変更は要らない**。ただし実行方法は別に決める（次項）。
- venice/kyoto/vatican は entry と outfile を相対パスで書き、`absWorkingDir` を持たない（alhambra だけ `absWorkingDir: here`）。`<city>/tools` を cwd にしないと壊れるので、全都市の再ビルドは `build-users.mjs` から各都市の cwd を指定して呼ぶ。
- `shared/` の中から bare import（`'three'`）すると、venice/kyoto では解決できない見込みが高く、解決できても `three` と `three/webgpu` が二重に入るおそれがある。**結論：`shared/move/` は three を一切 import しない。** `getWorldDirection` の出力ベクトルも都市側の `readDir()` が THREE.Vector3 で用意する。
- `vel` は共通側の小さな Vec3 にする。外部が使うのは film_page.js の `vel.set()` と音の `Math.hypot(vel.x, vel.y)` だけなので足りる。
- **前提として直すもの**：vatican の build_web.mjs:2 の絶対パス。`import * as esbuild from 'esbuild'` にし、vatican/tools/package.json に esbuild を版を固定して足し、package-lock.json も更新する。alhambra の `createRequire` 方式は写さない（alhambra は vatican をフォールバック先にしている＝build_web.mjs:7-9 ので、写すと vatican が自分自身にフォールバックする）。
- 配信されるのはコミット済みの bundle だけで、`shared/` はビルド時にだけ要る（§1.5）。

### 3.2 公開インターフェースと契約

**コア**はプレーンなデータを受け取って返す関数群、**殻（Mover）**はブラウザーの入力とカメラをコアにつなぐ組み立て役。移行時の互換プロパティ（main.js・ui.js・film_page.js・`VEN/KYO` フックが触るもの）はすべて殻に置く。

#### コアのデータ（state.js）

```js
// MoverState：プレーンなデータ
{
  v: MOVE_SCHEMA,                    // 状態・入力・コマンドの形の版（§3.5 (4)）
  mode: 'walk' | 'fly' | string,     // コアが知るのは walk / fly。boat・orbit はクライアント専用
  pos: { x, y, z },                  // 都市のワールド座標
  yaw, pitch,                        // 都市固有の規約のまま
  vel: Vec3,                         // 歩行・飛行で共用
  speed,                             // 飛行速度
  walk: { z: number | null, bob },   // z=null は「まだ着地点を探していない」（意図的な null）
  status: 'ok' | 'hold',             // 'hold'＝世界データが無くて、この step では動かなかった
}

// InputFrame：1回の step に渡す入力
{ f, r, u, fast,  yaw, pitch }       // compose 済みの軸と、この step で使う視点の絶対値

// Command：状態を変える離散的な操作。step とは別の、順序付きの列
{ type: 'setMode', name } | { type: 'setSpeed', value } | { type: 'place', pos, yaw?, pitch? }
```

- **再生可能な入力の単位は「InputFrame ＋ そのステップの前に適用する Command の列」**。1回の更新の記録は `{ dt, cmds: [...], frame }` で、`cmds` を順に `command()` で適用してから `step()` を呼ぶ。InputFrame だけでは速度の変更やモードの切替を再現できないので、**状態を変えるものはすべて Command を通す**。ホイールは `state.speed` を直接書かず `setSpeed` を出す（範囲の丸めは入力側で済ませ、コアでも範囲を検査する）。
- `place` は外部からの瞬間移動（`walkAt`、`goPlace`、ゴンドラから降りる処理、film）を表す。**コアで処理できることと、ネットワーク越しに受理してよいことは別**で、受理の権限は §3.5 (3) で扱う。
- 通信用の連番（tick 番号、最後に処理した入力の番号）はいまは持たないが、記録の形を `{ tick?, dt, cmds, frame }` に広げられるようにしておく。

#### コアの関数（step.js）

```js
step(state, frame, dt, world, cfg) → state     // 外部副作用のない更新関数。state を破壊的に更新して返す
command(state, cmd, world, cfg) → state        // 同上
```

- **「純粋」の範囲**：引数以外（DOM・camera・時刻・乱数・モジュール変数）を読まず、引数以外に書かない。ただし `state` はその場で書き換える（毎フレームの割り当てを避けるため）。比較・予測・巻き戻しでスナップショットが要る側は、呼ぶ前に `toPlain` で複製する。同じオブジェクトを2回渡して同じ結果を求める試験は成り立たないので、試験は複製から始める。
- **world**：都市が渡す世界クエリ。ラスター歩行なら `sample(x, y)`、飛行の地面制限なら `ground(x, y)`。**同期関数**で、データの取得は step の外で済ませる。コアが保証するのは「同じ world の内容に対して同じ結果」までで、world 自体がロードの進み具合で答えを変える（ストリーミング中のタイル）ことや、alhambra の地形がモジュール変数 `ground` を読むこと（§1.5）は world 側の事情として残る。**現時点で全都市の移動が厳密に純粋になるとは約束しない。**
- **cfg**：都市ごとの設定（§3.3）。数値と、`clamp(pos, vel, world)` のような引数だけを読む関数で書く。DOM・three を含めない。kyoto の飛行の地面制限は今 `tiles` と `farGround` を直接読んでいる（main.js:323）ので、`world.ground` 経由に直す。
- 視点（yaw/pitch）は InputFrame の絶対値で受け取る。旋回キー（決定①）とドラッグ（決定②）の積分は入力側（input.js）で行う。例外は walk に入るときの pitch の制限（venice controls.js:36、kyoto :36）で、`command({type:'setMode'})` の中で行い、殻が入力側の pitch に書き戻す。

#### toPlain / fromPlain の契約

- `toPlain(state)` はプレーンなオブジェクト（数値・文字列・null・配列・オブジェクトのみ）を返す。`fromPlain(obj)` は形と値を検査して `vel` を Vec3 に戻す。**JSON 経由でも構造化複製経由でも必ず `fromPlain` を通す**（構造化複製はクラスのメソッドを保たない）。
- 数値はすべて有限でなければならない。`NaN`／`Infinity` は JSON で `null` になるので、`fromPlain` は「`walk.z` の意図的な null」以外の null と非有限値を拒否する。`MOVE_SCHEMA` が違えば拒否する（変換は §3.5 (4)）。
- 送受信の形式（バイナリ化、差分送信）は後回し。

#### 殻（Mover）

```js
export class Mover {
  constructor({
    view,          // ビューアダプター。カメラに触るのはここだけ
    dom,           // ポインター / ホイールを受ける要素
    input = {},    // InputOptions（下記）
    modes,         // { walk: rasterWalkMode(…), fly: flyMode(…), boat: ClientMode, orbit: ClientMode, ... }
    mode, speed,   // 初期モード名、飛行速度の初期値
    world,         // 世界クエリ（コアへそのまま渡す）
    onUserInput,   // (kind: 'key'|'pointerdown') => void。alhambra のツアー停止用
  });
  update(dt);      // 下記の手順
  setMode(name);   // Command を積む。クライアント専用モードなら exit()/enter() も呼ぶ
  syncFromCamera();// view.read() → state.pos / yaw / pitch
  resetInput();    // キー・スティック・vert・alt・ドラッグ中のポインターをすべて解除
  dispose();
  state;           // MoverState（読み取りは自由。書き換えは互換プロパティか Command 経由）
  // 互換プロパティ（state への getter/setter。setter は対応する Command を積むか、次の update で取り込む）
  yaw; pitch; vel; enabled; mode; speed; keys; walkZ; move; vert; fastLatch; alt;
}
```

`update(dt)` の手順：

1. 溜まっている Command を順に適用する（`enabled` に関係なく。ホイールの速度変更が今 `enabled` を見ていない3都市の挙動を保つ）。
2. `frame = input.read(dt)`。キーの保持状態を読み、旋回キーを積分する。ドラッグはイベントが届くたびに input.js が yaw/pitch に足して**その場で制限を掛けている**ので、ここではその値を取るだけ（イベント順の clamp を保つ。§3.4 ②）。
3. `state.pos ← view.readPos()`。**位置の正本は当面 `camera.position`** のままにし、外部がカメラを直接動かしている今の挙動を変えない。
4. `enabled=false` なら終わり。
5. クライアント専用モード（boat、orbit）なら、そのモードの `update(ctx, frame, dt)` を呼んで**ここで終わる**（カメラはモード自身が置く。`view.apply` は呼ばない）。
6. コアのモードなら `step(state, frame, dt, world, cfg)`。`status==='hold'` なら位置も視点もカメラに適用せずに終わる（今の early return と同じ）。
7. `view.apply(state)`。

**状態の持ち主**（二重持ちをしない）：

| 状態 | 持ち主 | 備考 |
|---|---|---|
| yaw / pitch | 入力側が積分し、`mover.state` に入る | 都市固有の規約のまま |
| 位置 | ブラウザーでは `camera.position`、コアでは `state.pos` | 殻が毎回取り込み、step の後に書き戻す。サーバーでは `state.pos` だけが正本 |
| vel | `mover.state` | 歩行・飛行で共用 |
| speed | `mover.state` | 変えるのは `setSpeed` だけ。flyMode は `state.speed` を読む |
| walk.z, bob | `mover.state.walk` | `walkZ` は互換用の getter/setter |
| boatYaw / boatPitch、orbit の球面座標 | 各都市のクライアント専用モード | コアの state には入れない |

**ビューアダプター**：`{ apply(state), read() → {pos, yaw, pitch}, readPos(), forward(yaw) → [a, b], right(yaw) → [a, b], up }`。水平の2成分は z-up なら (x, y)、y-up なら (x, z)。`forward/right` はコアからも使うので純粋関数として切り出し、コアは規約を `cfg.axes: 'zUp' | 'alhambra'` で受け取る。

- `zUpView(camera, readDir)`（venice/kyoto/vatican）：forward=(cos y, sin y)、right=(sin y, −cos y)。`cam.up.set(0,0,1)` と `lookAt`（vatican は up を設定しない今の挙動を保つ）。
- `alhambraView(camera)`：forward=(−sin y, −cos y)、right=(cos y, −sin y)（main.js:181）。`camera.rotation.set(pitch, yaw, 0, 'YXZ')`、読み戻しは `orientation()` と同じ。
- yaw の基準は統一しない。どちらの規約でも「yaw が増える＝左に回る」は一致する。四方位で forward/right と `apply→read` の往復を単体テストで固定する。

**InputOptions**（都市ごとの「好み」）：

```js
{
  keyField: 'code' | 'key',              // alhambra は 'key'（toLowerCase した値）
  bindings: { forward, back, left, right, turnLeft, turnRight, up, down, fast },
  turnRate: 1.2,                         // rad/s（決定①）。移行コミットの旧挙動は Mover の migration で（§3.4）
  compose: 'clampEach' | 'sum',          // venice/kyoto/vatican='clampEach'、alhambra='sum'
  drag: { mouse: 0.003, touch: 0.005, pitchLimit: 1.5, button: null },  // 符号は持たない（input.js の定数）
  wheel: { min: 1, max: 300, modes: ['fly'] | null } | null,           // modes:null＝モードを見ない（vatican）
  ignore: (e) => boolean,                // 新しいキーイベントを無視する条件（入力欄・ダイアログ）
  resetOn: ['blur'] | ['blur', 'hidden'],
  preventDefault: false,                 // alhambra は true（割り当て済みのキーだけ）
}
// 'clampEach' は f/r/u をそれぞれ ±1 に丸める（kyoto の u+vert を含む）。'sum' は丸めない。
// 水平の正規化はモードの normalizeXY が行う。
```

- `ignore(e)` は新しいイベントを捨てるだけで、押されている入力は解除しない。ダイアログを開く・ツアーを始める・外部からカメラを置くときは、都市側が `mover.resetInput()` を呼ぶ（alhambra の `pauseInput`、main.js:114 の置き換え）。
- `enabled=false` の意味は今の3都市と同じ「積分と視点の更新を止め、ドラッグも無視する。キーは集め続ける。ホイールの速度変更は効く」。
- `onUserInput` は Mover が受けたイベント（割り当て済みキー、pointerdown）だけを通知する。スティック、▲▼、orbit のホイールは都市側が今どおり `stopTour()` を呼ぶ。vatican は渡さない。

**クライアント専用モード**（boat、orbit。ブラウザーの中だけで動く）：

```js
{
  enter(ctx, prevName), exit(ctx),
  update(ctx, frame, dt),  // カメラを自分で置く
  look?(dx, dy, e),        // あればドラッグはここへ行き、yaw/pitch は変えない
  wheel?(e),               // あれば既定のホイール処理の代わりに呼ぶ（alhambra の orbit 半径）
}
```

- `look(dx, dy)` には**係数と符号を掛けた後の値**をイベントごとに渡し、制限もモードがイベントごとに掛ける。これで決定②の反転は boat の見回しにも自動で効く。alhambra の orbit は今の式（`orb.theta -= dx*.004`）を保つため、都市側で係数の比（.004/.003）を掛け直す。alhambra は符号が変わらないので orbit の挙動は変わらない。
- ポインターとホイールのリスナーは Mover だけが持ち、`look/wheel` を持つモードに振り分ける（alhambra main.js:128-130 の分岐を二重処理なしで表す）。

**標準モード（コアの cfg）**：

```js
flyMode({
  fastMul: 4,
  smooth: 4,                // vel.lerp(want, 1-exp(-smooth*dt))。null は vel を want に即代入（alhambra）
  normalizeXY: false,       // alhambra は true
  followPitch: false,       // kyoto は true
  clamp: (pos, vel, world) => {},  // kyoto：地面+2 m、alhambra：範囲の箱と地形+0.7
})

rasterWalkMode({
  strategy: strictStep({ radius: .24, step: .55 })            // venice
          | glideStep({ radius: .12, up: .75, down: 1.2 }),   // kyoto
  eye, speed, runSpeed, smooth: 8, follow, searchRadius,
  normalizeXY: true, bob: { amp: 0.012 } | null, pitchOnEnter,
})
// 地面は world.sample(x, y) → { z, blocked? }。z===undefined は世界データ未準備（status 'hold'）
```

- 共通部分（raster-walk.js）：速度の補間、螺旋探索、高さ追従、揺れ、'hold'。
- 戦略が持つもの：通行判定、探索で受け入れる条件、blocked セルからの脱出（glide だけが `through`）、衝突後の速度（strict は 0、glide は ×0.5）、高さ追従に使う z の取り方。venice controls.js:57-64, :99-104 と kyoto controls.js:52-77, :103-131 をそのまま移す。
- **venice の `sample` は変換しない。** null（建物・水面）、undefined（未ロード）、数値の3状態を保つ。「null を 0 にして blocked にする」アダプターは、glide の `through` と組み合わさるとダミーの高さが判定に混ざり得るので採らない。
- alhambra を `navWalkMode(nav)` まで載せる場合も `Navigation` は都市側に置き、`world` 経由で渡す。

### 3.3 都市ごとに残す設定とコールバック

設定（cfg）は、DOM と three を含まないモジュール（例：`<city>/tools/web/move-config.js`）にまとめる。将来その都市のサーバーからも同じファイルを import できるようにするため。

| 都市 | Mover に渡すもの | 都市側に残すもの | 操作変更コミットで変わること |
|---|---|---|---|
| vatican | `zUpView`（up は設定しない）、`speed:25`、`flyMode({smooth:3})`、arrows を横移動に、`drag:{mouse:.0035, touch:.0035}`、`wheel:{min:2,max:400,modes:null}` | tour.js、world.js、`enabled` を mode と連動させる処理（main.js:144）、F キー | ② ドラッグ反転 |
| kyoto | `rasterWalkMode({strategy: glideStep(…), eye:1.6, speed:1.5, runSpeed:4.2, follow:10, searchRadius:60, pitchOnEnter:.6})`、`speed:30`、`flyMode({followPitch:true, clamp: 地面+2 m})`、`turnRate:1.5`、wheel 2〜600 | タイトル画面、goPlace、ui.js のタッチボタン（`mover.vert/fastLatch`）、ミニマップ、音 | ① 旋回、② ドラッグ反転 |
| venice | `rasterWalkMode({strategy: strictStep(…), eye:1.62, speed:1.45, runSpeed:3.6, follow:12, searchRadius:40, pitchOnEnter:.5})`、`world:{sample: tiles.sample}`、`speed:12`、`flyMode({})`、`turnRate:1.2`、`boat: boatMode(ride)`（`look()` で ±2.6/±1.0 に制限） | gondola.js、R キー、ゴンドラから降りる処理、bridge_check.py | ① 旋回、② ドラッグ反転（ボート中の見回しも） |
| alhambra | `alhambraView`、`keyField:'key'`、`compose:'sum'`、`resetOn:['blur','hidden']`、`onUserInput: stopTour`、`drag:{mouse:.003, touch:.003, pitchLimit:1.48, button:0}`、`navWalkMode(nav)`（smooth:null、normalizeXY、2.3 m/s、×2.4）、`flyMode({smooth:null, normalizeXY:true, fastMul:2.4, clamp: 範囲の箱と地形})`、`orbit: orbitMode` | navigation.js 全体、ツアー、drawMap、`setMode` の定位置へ戻す処理、`#joystick/#rise/#descend` の DOM | 無し（操作変更コミットも無い） |

- alhambra の今の式は `speed*dt` を掛けた変位を直接足す（main.js:180-182）。`smooth:null` で `vel=want; pos+=vel*dt` にすると掛け算の順序が変わるが、差は丸め程度で §4.0 の許容誤差に収まる。

### 3.4 二つの決定事項（オーナー決定 2026-10-29）

**① フレームレート依存の旋回（venice 0.02、kyoto 0.025 rad/フレーム）— 決定：直す。**

- 移行コミットでは一時的な口 `migration.turnPerFrame`（下の②と共通）で今の値を保ち、その都市の操作変更コミットでそれを消して `turnRate`（60Hz 換算で venice 1.2、kyoto 1.5 rad/s）を効かせる。60Hz の利用者には変化が無い。
- 理由：今は 120Hz の画面で2倍速、30Hz で半分の速さで回る。vatican/alhambra は ←/→ が横移動なので関係しない。
- マルチユーザーとの関係：フレームあたりの旋回は**描画の回数**に依存する唯一の箇所。固定量の旋回でも、明示的な入力として渡せば step を関数にすること自体はできるので、①の目的は純粋性ではなく描画回数への依存を除くこと。①だけでは旋回の角度が揃うだけで、移動の軌跡は揃わない（§3.5 (1)）。

**② ドラッグ方向 — 決定：全都市をアルハンブラ方式（景色をつかむ方式）に揃える。**

- 変わること：右へドラッグすると yaw が増えて**左**を向き、下へドラッグすると上を向く。venice/kyoto/vatican でドラッグの体感が反転する（venice のボート中の見回し boatYaw/boatPitch も）。alhambra は今のまま（orbit の式も変わらない）。
- 変わらないこと：←/→ の旋回の向き、ドラッグの係数、pitch の制限、`X.look`・`walkAt`・`goPlace`・film・snap の shots（yaw/pitch を直接書くので符号を通らない）。
- **符号の置き場所（設計判断）**：符号は `input.js` の定数 `DRAG_SIGN = +1`（両軸）に閉じ、InputOptions にも都市の設定にも出さない。移行コミットで旧挙動を再現するためだけに、Mover の構築引数に一時的な口 `migration: { dragSign: -1, turnPerFrame }` を置く。名前で一時的なものと分かるようにし、①の `perFrame` もここへまとめる。各都市の操作変更コミットでこの引数を消し、最後の都市（venice）が済んだら shared から口ごと消す。将来、利用者向けの「視点操作を反転」設定を足すことになれば、それは別の機能追加として設計する。
- **イベント順の clamp を保つ**：今はドラッグのイベントごとに pitch（boat では boatYaw/boatPitch も）を制限している。InputFrame に詰めるときにドラッグ量を1回分に合算して最後に一度だけ制限すると、「制限の端まで動かしてから戻す」イベント列で結果が変わる。input.js はイベントごとに足して制限し、InputFrame にはその結果の絶対値を入れる。
- 注意：マウス操作では、多くの一人称視点のゲームや地図アプリと逆の向きになる。オーナー決定として採用し、違和感の報告が多ければ改めて判断する（戻し方は §5.1）。
- 手動確認：マウスとタッチの両方で、歩行・飛行（venice はボートも）を実機で触る。操作説明の文言に向きを示す表現があれば合わせる（有無は未確認）。

**vatican にタッチスティックを足すこと**は機能追加なので、共通化とは別の作業にする。

### 3.5 将来のマルチユーザー対応への備え

**前提（オーナーの見立て）**：マルチユーザー対応をするなら、都市ごとに Cloudflare Worker を分ける。

**現状**：4都市はギャラリーと同じ Worker `demos` の静的アセットで、都市ごとのサーバー処理は無い（§1.5）。ただし `public/app.js` はコミット時点の bundle なので、`shared/move/` を入れた時点で「都市ごとに中身の版がずれる」状態は起こり得る（shared を直して一部の都市だけ再ビルドした場合）。

#### (1) 再現性の契約

**約束すること**：同じ初期状態・cfg・世界データ・更新ごとの入力（Command の列と InputFrame）・dt の列がそろえば、同じ実装は同じ状態列を返す。これは移行時点から成り立ち、比較 A（§4.0）はこの性質の上に立つ。

**約束しないこと**：
- **描画のフレームレートが違っても同じ軌跡になること。** dt を引数にしても、dt が違えば結果は変わる（`min(1, 12dt)` の追従、`1-exp(-k dt)` の補間の途中で目標が変わること、衝突判定を1ステップ分の移動量でまとめて行うこと）。
- **固定ステップを入れれば自動的に揃うこと。** 揃うには、入力をどの tick に割り当てるかまで決める必要がある。たとえば描画フレームごとに最終の yaw/pitch を1回だけ作って複数の tick に渡すと、30Hz では2つの tick がどちらも最終角度を使い、120Hz では tick の無い描画フレームで視点だけが進む。旋回しながら前進する軌跡は揃わない。
- **ブラウザーと Workers（あるいはブラウザー同士）で末尾のビットまで一致すること。** 四則演算と `Math.sqrt` は IEEE 754 で結果が決まるが、`Math.sin/cos/exp/hypot` は実装ごとの近似が許されている（[ECMAScript の数学関数の規定](https://tc39.es/ecma262/2025/multipage/numbers-and-dates.html#sec-math.sqrt)）。小さな丸め差が衝突の境界で「通れる／止まる」の分岐差に広がることもある。したがって入力だけを送り合うロックステップは前提にせず、サーバーが状態を持つ場合も、サーバー状態のスナップショットからの復帰、入力の再実行、表示上の補間が必要になり得る。

**固定タイムステップを入れるときの契約**（実装は移行の後。cfg `fixedStep: null | 1/60`、既定 null から）：

| 項目 | 決めること |
|---|---|
| tick | 長さは都市の cfg で固定（例 1/60 s）。tick 番号を数え、記録は `{ tick, cmds, frame }` にする |
| キー | 各 tick の開始時点の保持状態を読む。1 tick より短い押下は今と同じく落ちる |
| 旋回キー | tick ごとに `turnRate × tick長` を積む（描画フレームごとに1回ではない） |
| ドラッグ | イベントを届いた順に溜め、決めた規則で tick に割り当てる（案：その描画フレームで溜まったイベントは、そのフレームで最初に回る tick に入れる）。tick の中ではイベント順に足して制限し、その tick の yaw/pitch とする。tick の回らない描画フレームでは state を変えない（表示だけ先に向きを変えるかは表示側の選択） |
| Command | tick に割り当て、その tick の step の前に順に適用する |
| 余剰時間 | 1描画フレームで回す tick の上限を決め（今の dt 上限 0.1 s / 0.05 s に相当する数）、超えた分は**捨てる**（今と同じ。持ち越さない） |
| 非表示からの復帰 | アキュムレーターを 0 に戻す（追いかけて回さない） |
| hold | tick は進める。その tick では pos・vel・walk を変えず、yaw/pitch だけ入力の値を受け取る（今も、着地点を探して待つ間に旋回キーの yaw は進む）。サーバーでも同じ規則にする |
| 世界データの準備 | world は同期関数なので、データの取得は step の外で済ませる。準備ができていない範囲への問い合わせは `undefined` を返して hold にする。クライアントとサーバーで準備の具合が違えば状態はずれるので、それはサーバー状態への補正で扱う（下記 (3)） |

- 固定ステップは**挙動を変える**（低いフレームレートでの当たり判定の細かさが変わる）ので、独立したコミットで入れ、30/60/120Hz 相当の描画間隔で、上の割り当て規則に従った入力列から同じ状態列が出ることを確かめる。
- 権威モデルによっては固定ステップ自体が要らない（(5)）。

#### (2) 状態・入力・コマンドの受け渡し

- `MoverState`・`InputFrame`・`Command` はプレーンなデータで、`toPlain/fromPlain`（§3.2）を通して JSON でも構造化複製でも送れる。
- 視点は**絶対値の yaw/pitch** で送る。ドラッグの係数・符号や旋回の速さはクライアントの入力処理で閉じる。ただし絶対値は「どの tick の視点か」と組にして初めて意味を持つ。
- **送れることは正しいことを意味しない。** 受け取る側の境界で、数値が有限か、軸が範囲内か（clampEach なら ±1、sum なら合成後の上限）、pitch が制限内か、速度が範囲内か、モードとコマンドが許されているか、を検査する。
- 後から足す前提のもの：tick／連番、最後に処理した入力の番号、Command の順序。いまの記録の形（`{ dt, cmds, frame }`）はこれを足せる形にしてある。
- **クライアント専用モード（boat、orbit、ツアー、film）の姿勢は「検証しない姿勢」**。他人に見せるなら、そのときのカメラの位置と yaw/pitch をそのまま送る。ゴンドラ自体の同期は別の設計課題で、この提案の範囲外。

#### (3) 権威モデルと保証の範囲（決めるのはマルチユーザー化のとき）

| 候補 | サーバーがすること | 保証すること | 保証しないこと |
|---|---|---|---|
| **P. 姿勢の中継** | クライアントの姿勢（位置・yaw/pitch・モード）を受けて配る。有限値・範囲・送信頻度だけを検査 | 他人のカメラがおおよそどこを向いているか | 歩行可能な場所にいること、速さ、壁を抜けないこと |
| **C. クライアント権威 + 検査** | P に加え、**サーバーが持つ時刻と直前に受理した状態**を基準に速さの上限を検査する（申告された dt は使わない）。`place` とモードの切替は Command として別に扱い、許すものだけ受ける | 速さの上限。終点を検査するなら、歩行モードの終点が歩行可能であること | 終点の検査だけでは途中の壁抜けを防げない。防ぐには区間の検査と、クライアントと同じ衝突データが要る |
| **S. サーバー権威（DO で再計算）** | InputFrame と Command を tick ごとに受け、同じ `step` で再計算して正す | 歩行可能性・速さ・衝突を、サーバーの世界データの範囲で | クライアントとの末尾ビットの一致（補正で扱う） |

それぞれに要るものは (5) の表にまとめた。

- **検証しない姿勢との境界**：クライアントが「検証しない姿勢」を自由に名乗れると、C の歩行の検査はそこから迂回できる。C や S を採るなら、クライアント専用モードへの切替を Command としてサーバーが許可し（例：ゴンドラに乗れる場所でだけ boat を許す）、検証しない姿勢は「アバター」ではなく「カメラ」として別扱いで表示する。P ならこの区別は要らない。競争要素の無いデモなので、まず P か軽い C で足りる見込みだが、どの保証が要るか（他人のカメラを見せるだけか、歩行可能性を保証したアバターか）を決めてから選ぶ。
- **未ロードの扱い**：クライアントは歩行ラスターが無いと hold になるが、サーバーが世界データを持っていれば同じ入力でも進む。「hold 中は移動入力を送らない」は停止の代わりにならない（残っている vel の減衰、前回の入力の保持、歩行開始の探索が残る）。候補は2つ：(a) サーバーは状態を進め、クライアントは描画に要るデータがそろうまで予測を止めてサーバー状態に合わせる（自然なのはこちら）、(b) 入力に hold を明示し、サーバーもその tick を (1) の hold の規則で扱う。
- **サーバー側の世界データ**：サーバーも世界データを全部持つとは限らない（タイル単位で読むなら、読み終えるまでは (1) の「世界データの準備」の規則に従う）。
  - venice/kyoto：歩行ラスターの復号が Workers で使えない前提で、①ビルド時に生のバイナリ（高さコードと water/blocked の対）へ書き出すか、②純 JS の PNG 復号を使う。`tiles.sample` の参照ロジック（venice tiles.js:324-335、kyoto tiles.js:193-203）を `Tiles` から切り出して `WalkGrid` として共有する。合計サイズと DO のメモリーとの関係は未確認。
  - alhambra：衝突形状をビルド時にデータとして書き出し、地形サンプラーをモジュール変数ではなくインスタンスに注入する。navigation.js を変えるので、tour.js・check-walks・`navigation.test.mjs` の確認が要る。
  - vatican：衝突が無いので不要。venice の `water`、kyoto の `covered` は移動に使っていないので不要。
- **DO の分割単位**：「都市ごとに Worker を分ける」ことと「DO をどの単位で作るか」は別の問題。1都市1DO を前提にせず、ルーム単位などをマルチユーザー化のときに決める。

#### (4) 版の一致：何が違えば何をするか

`MOVE_VERSION` 1つでは判定できない。決定①②のように step を変えずに入力側で挙動が変わる変更があり、同じ step でも cfg（速度・段差・座標規約）や世界データ（歩行ラスター・衝突形状）が違えば結果は変わるため。識別子を次のように分ける（定数の置き場所だけいま決め、運用は移行の後）。

| 識別子 | 何の変更で変わるか | 違ったときの扱い |
|---|---|---|
| `MOVE_SCHEMA`（state.js の整数） | MoverState・InputFrame・Command の形の変更 | 接続を拒否して再読み込みを促す。保存状態は変換するか、捨てて初期位置から始める |
| `MOVE_VERSION`（state.js の整数） | 同じ入力・cfg・世界データに対して step／command の結果が変わる変更 | S では接続を拒否する。P・C では診断用（C の検査の規則が変わる場合は拒否） |
| `cfgId`（都市の `move-config.js` のハッシュ） | 速度・段差・座標規約などの都市設定の変更 | C・S では接続を拒否する |
| `worldId`（その都市の歩行ラスター一式、または Navigation の書き出しのハッシュ） | 世界データの変更 | C（世界データで検査する場合）・S では接続を拒否する。git の外のデータなので、デプロイ時にローカルのコピーから計算し直して照合する |
| `buildId`（実際に bundle に入った入力ファイルのハッシュ。esbuild の metafile から作る） | 入力側を含め、bundle の中身の変更すべて | 診断用。どの都市がどの中身で配信されているかを確かめる。**ソースのコミットでは代わりにならない**（コミット済みの app.js がそのコミットのソースから作られたとは限らないため） |

- 運用の原則：1都市のクライアント bundle とサーバーは同じコミットから作り、一緒にデプロイする。これに意味があるのは、**その時点で bundle を作り直し（`build-users.mjs`）、`worldId` が配信するデータと一致することを確かめた場合**だけ。
- それでも古いクライアントは残る（キャッシュ、開きっぱなしのタブ）。まずは「違えば再読み込み」で始める。直前の版を受け入れるなら、その版の step を残す必要がある。
- マルチユーザー化のときの設計項目に加えるもの：既存の接続がある状態でのデプロイ（接続を切るか、版の混在を許すか）、DO の保存状態の扱い（DO のメモリー上の状態は休止や再生成を越えて残らないので、保存と復元が要る。スキーマが変わったときの変換か破棄）。参考：[Cloudflare：Durable Objects の WebSocket と休止](https://developers.cloudflare.com/durable-objects/best-practices/websockets/)。
- **shared の変更の規則（時期で分ける）**：
  - 今回の全都市移行（決定①②を含む）は例外。①②は全都市の共通の既定を変える決定で、都市の設定で選ばせない。各都市の操作変更コミットで、その都市の bundle に入る。
  - 移行が済んだ後の shared の変更は、既定の挙動を変えない。挙動が変わる変更は、cfg で都市が明示的に選ぶ形で入れ、選んだ都市の再ビルドで初めて効くようにする。結果が変わるなら該当する識別子を上げる。
- 置き場所は A 案（相対 import）のままでよい。版は「どのコミットからビルドしたか」と上の識別子で決まる。都市ごとに shared の版を固定したくなったら、そのときに C 案（版付きパッケージ）を改めて比べる。都市ごとの Worker へのルーティング（route か service binding か）とデプロイの分け方（cf CLI など）もマルチユーザー化のときに決める。

#### (5) 権威モデルごとに要るもの

| 項目 | P（姿勢の中継） | C（クライアント権威 + 検査） | S（サーバー権威） |
|---|---|---|---|
| コア／殻の分離、プレーンデータ、受け渡しの契約（いま作る） | 役立つ（姿勢の形が決まる） | 要る | 要る |
| `MOVE_SCHEMA` | 要る | 要る | 要る |
| `cfgId`・`worldId`・`MOVE_VERSION` による拒否 | 不要 | 検査に使うものだけ | 要る |
| 固定タイムステップと tick の契約 | 不要 | 不要 | 要る |
| サーバー側の世界データ（`WalkGrid`、Navigation の書き出し） | 不要 | 終点・区間を検査するなら要る | 要る |
| 補正（スナップショットと再実行）と他人の補間 | 補間だけ | 補間と、拒否時の巻き戻し | 両方 |

#### (6) いつやるか

| 時期 | やること | 理由 |
|---|---|---|
| **いま（移行と同時）** | ・コア（`step`/`command`）と殻（`Mover`）の分離<br>・MoverState／InputFrame／Command をプレーンなデータにし、状態を変えるものはすべて Command にする（ホイールは `setSpeed`）。`toPlain/fromPlain` の契約<br>・`state.pos` をコアに持たせ、殻がカメラと同期する<br>・視点を入力側で積分し、イベント順の clamp を保つ<br>・cfg を `move-config.js` に分け、`clamp` を引数だけで書く<br>・互換プロパティ<br>・純粋性と多重インスタンスの試験<br>・決定①②（旧来の旋回と符号は一時的な `migration` の口に閉じ、操作変更コミットで消す） | 後から分けると、移行で作るトレースと互換プロパティを作り直すことになる。**作業量は小さくない**：venice/kyoto の controls を単純に一本化するだけの場合に比べ、状態の持ち主の整理、Command の経路、cfg の分離、カメラとの同期、互換プロパティの getter/setter、多重インスタンスの試験が加わる。それでもいまやる理由は、再生可能な境界（「記録した入力から同じ状態列が出る」）が移行の比較そのものにも使えること、後からでは同じ比較をもう一度やり直すことになることにある |
| **移行の後（権威モデルを決めてから、要るものだけ。どれも独立したコミット）** | ・識別子（`MOVE_SCHEMA` 以外）の運用と bundle への `buildId` の埋め込み（診断用の `buildId` はシングルユーザーでも役立つので、権威モデルに関係なく入れてよい）<br>・固定タイムステップと tick の契約（S のとき）<br>・`WalkGrid` の切り出し（C で世界データを検査するとき、S のとき。node 試験の偽サンプラーを実データに置き換える用途だけなら任意） | 挙動が変わる、または移行の比較の邪魔になる |
| **マルチユーザー化のとき** | ・権威モデルの選択と保証の範囲<br>・都市別 Worker／DO の構成（分割単位）、ルーティング、デプロイの分離、既存接続と DO の保存状態の扱い<br>・通信の形式、受信境界の検査、補正と補間<br>・サーバー側の世界データ<br>・クライアント専用モードの扱い<br>・Workers／DO の上限の確認 | 要件（同時接続数、見せたいもの、保証したいもの）が決まるまで形が決まらない |

---

## 4. 移行計画

各都市は**2コミット**を基本にする：

1. **移行コミット**（挙動を保つ）：`migration:{ dragSign:-1, turnPerFrame }` で旧挙動を再現する。比較の基準は**旧実装**。
2. **操作変更コミット**（決定①②。操作感が変わる）：`migration` 引数を消す。比較の基準は**直前の移行コミット**（旧実装と一致を確認済み）。kyoto/venice は①②を同じコミットに入れ、「旋回だけ」「ドラッグだけ」「両方」の入力列を分けて検証して原因を切り分ける。vatican は②だけ。alhambra はこのコミットが無い。

オーナー決定は①②を移行と別のコミットにすることを求めていて、この形はそれを満たす。①と②を別コミットにすることまでは求めていない。

### 4.0 準備と検証の共通の表

**比較の仕組み**（先に作る）：

- **A. ロジック比較（node）**：2つに分ける。
  - **A1 入力変換**：旧実装と新しい input.js に、同じ偽の DOM イベント列（keydown/keyup、pointerdown/move/up/cancel、wheel、blur）を `EventTarget` の偽物経由で与え、毎回の yaw/pitch・speed・軸の値を比べる。旧 controls.js／fly.js は window の `addEventListener` と `dom` にリスナーを付けるので、node ではその2つを用意する。**完成した yaw/pitch を step に渡すだけの比較では係数や符号の誤りを検出できない**ので、A1 か B で必ずリスナーを通す。
  - **A2 移動**：同じ偽カメラ・偽 `sample`・入力列・dt 列を与え、毎回の位置・方向ベクトル・yaw（2π の折り返しを考慮）・pitch・vel・walkZ・mode を比べる。新実装は記録 `{ dt, cmds, frame }` を step/command に直接流せる。旧ファイルは `three/webgpu` を import するので、node でそのまま読めなければ esbuild で `three/webgpu → three` の alias を付けて束ねる。
- **B. 実シーン比較（ブラウザー）**：snap.mjs の shots `eval` から実イベント（`KeyboardEvent` を window に、pointer イベントを canvas に）を送り、`X.step(1/60)` を N 回呼ぶ。`controls.keys` に直接入れる方法は使わない。
  - venice/kyoto：`stopLoop()` → `walkAt` → **経路の範囲で `tiles.sample` が undefined でなくなるまで待つ** → 記録。`step` は controls の後で `tiles.update` を呼ぶ（venice main.js:358-359、kyoto :409-410）ので、待たないと結果が取得順で変わる。
  - vatican：`VAT` は `controls` を公開していない（main.js:273）ので、振る舞いを変えない1行のフックを別コミットで足す。`stopLoop()` は予約済みの RAF を取り消さず controls も無効にする（main.js:254-259, :275）ので、`stopLoop()` → 2フレーム待つ → `look()`（`setMode('free')` で再び有効、:144, :276）→ 入力、の順に固定する。
  - alhambra：`?film=1`（RAF が update を呼ばない、main.js:272）のもとで `ALH.step(dt)=update(dt)` を足す。`ALH.move` と check-walks は Navigation の検査として残すが、入力経路の検査にはならない。

**用語**：「**一致**」は、比べるすべての量が毎回 **1e-6（m / rad）以内**であることをいう（A1・A2・B 共通。alhambra の掛け算の順序の差もこの範囲に収まる）。B でこれを超えた場合は、まずロード待ちなど手順の不備を疑い、手順を直しても残れば不具合として扱う。「完全一致」という言い方はしない。

**入力列の種類**：K＝キーだけ、T＝スティック（kyoto は ▲▼ も）だけ、D＝ドラッグを含む。D には **pitch の制限の端まで動かして戻す往復**を必ず入れ、venice では boatYaw/boatPitch の制限（±2.6/±1.0）の往復も入れる。さらに旋回キーとドラッグを同時に使い、前進しながら行う混合の列 M を用意する。vatican にはスティックが無いので T は**該当なし**。

**期待値の作り方**：

- 移行コミット：旧実装に同じ入力列を与えたトレース。
- 操作変更コミットのドラッグ：**移行コミット**に「ドラッグの dx/dy を符号反転した入力」を与えたトレース。pitch の制限は両者で同じなので、端に当たる往復も含めて一致する。
- 操作変更コミットの旋回：60Hz では旧来のフレームあたりの値と秒あたりの値が同じ回転量になるので、移行コミットのトレースがそのまま期待値になる。30/120Hz では、軌跡は描画間隔で変わる（§3.5 (1)）ので比べず、**同じ実時間で回った角度**（ドラッグ由来の分を除く）が一致することだけを見る。アプリの dt 上限（0.1 s）を超えない範囲で見る。

**検証の表**（各都市の節はこの表を参照し、都市固有の場所と例外だけを書く）：

| | 移行コミット | 操作変更：旋回（①） | 操作変更：ドラッグ（②） |
|---|---|---|---|
| 基準版 | 旧実装 | 移行コミット | 移行コミット |
| A1 入力変換 | K・T・D・M の全部が一致 | K（←/→ を含む）：60Hz で一致、30/120Hz で実時間あたりの角度が一致 | D・M：反転入力の期待値と一致。K・T は一致 |
| A2 移動 | K・T・D・M が一致 | 60Hz で K・M が期待値と一致 | D・M が反転入力の期待値と一致、K・T は一致 |
| B 実シーン | 都市ごとの場所で K・T・D が一致 | 60Hz で K が一致 | D が反転入力の期待値と一致、K・T は一致 |
| モード | 切替の前後で一致（mode・vel=0・walk の pitch 制限） | 変化なし | ボート（venice）も反転 |
| 手動 | 既存チェックが通る | ←/→ で回る速さが体感で変わらない（60Hz） | マウスとタッチで歩行・飛行（venice はボートも）を実機で触る |
| 除外 | 意図した不具合修正に触れる入力（vatican の項） | — | — |

- コミットメッセージには、操作変更コミットで何が変わるかを書く。

**`shared/move/` の最初の中身**：コア（state/step の骨組み・飛行）と殻（入力・視点・Mover）。`node --test` の単体テスト：キーの合成と `compose`、blur/hidden での解除、`resetInput`、ビューの四方位の往復、`smooth:null`、`setSpeed` と `enabled=false` 時のホイール、クライアント専用モードへの look/wheel の振り分けと符号、イベントごとの clamp、`status:'hold'`、`DRAG_SIGN` が +1 であること、`toPlain/fromPlain`（JSON と構造化複製の両方、非有限値と不正な null の拒否）、コアのソースが `three`・`document`・`window`・`performance`・`Date`・`Math.random` を参照しないこと、DOM の無い node で import して step を回せること、同じ step を N 個の state で回しても互いに影響しないこと。ソースの検査と node での実行は補助で、渡された world や cfg の関数に隠れた依存が無いことまでは証明しない。

**`build-users.mjs`**：shared を使う都市の一覧を持ち、各都市を `<city>/tools` を cwd にしてビルドする。各都市の esbuild の版は lockfile のとおりに固定する。

### 4.1 vatican（ビルド経路と飛行の試験台）

- 準備（別コミット）：build_web.mjs の esbuild 解決を直す（§3.1）。旧来の esbuild の版は分からないので bundle のバイト一致は参考に留め、新しく固定した版を記録する。`VAT.controls` のフックを足し、比較データを記録する。
- **移行コミット**：fly.js を `Mover` + `flyMode` に置き換える。呼び出し側（main.js:48, :144, :238, :275-276）は互換プロパティで動く見込み。挙動の差として**受け入れる不具合修正**と、**保つもの**：

  | 項目 | 扱い |
  |---|---|
  | blur でのキー解除 | 不具合修正として受け入れる（押したままフォーカスを失うと飛び続ける） |
  | pointerId の照合、pointercancel | 不具合修正として受け入れる |
  | 入力欄の除外（共通の `ignore`） | 入る。ただし index.html に入力欄が無いので、今は観察できる差が無い |
  | ホイール（モードも `enabled` も見ない、常に `preventDefault`） | 保つ（`wheel.modes:null`、Command 適用は `enabled` に関係なく行う） |

  比較では、受け入れる修正に触れない入力列で K・D・M の一致を見る（T は該当なし）。
- **操作変更コミット（②だけ）**：`migration` 引数を消す。手動では free モードのマウスとタッチ（タッチ端末ではドラッグしか無いので操作の全部が反転する）。ツアー・タイトルはドラッグを使わないので影響しないことも確かめる。

### 4.2 kyoto（ラスター歩行をここで初めて入れる）

- **移行コミット**：raster-walk.js と walk-glide.js を作り、controls.js を薄いラッパー（`class Controls extends Mover`）にする。main.js、ui.js、film_page.js の参照は変えない。飛行の地面制限（main.js:323）は `world.ground` 経由にする。
  - A2 は偽サンプラーで石段・狭い通路・柱の回り込み・blocked セルからの脱出・飛行の地面制限を、B は産寧坂、三十三間堂の堂内、千本鳥居、飛行中の地面への接近で取る。title → walk → fly、`KYO.walkAt`、film.mjs、タッチのエミュレーション（alhambra snap.mjs:39-41 の方式を移植）も見る。
- **操作変更コミット（①②）**：`migration` 引数を消し、`turnRate:1.5` にする。手動では、スティックで歩きながらドラッグで見回す両手の操作を実機で確かめる。`goPlace` とタイトル画面のカメラは yaw/pitch を直接書くので影響しないことも確かめる。
- **ここで API を見直す。** コア／殻の境界、InputFrame と Command、状態の持ち主、クライアント専用モードの形が足りたかを確かめ、必要なら venice に進む前に直す。

### 4.3 venice（第2の歩行戦略）

- **移行コミット**：walk-strict.js を足し、`boatMode(ride)` を venice 側にクライアント専用モードとして置く。radius と step の定数は変えない（bridge_check.py の前提が段差 0.55 なので）。
  - A2 で strict の判定（5点・軸ごと・停止で vel=0）を、B でリアルト橋の上り下り、カッレの角、サン・マルコ広場を見る。`python bridge_check.py`、ゴンドラ（自動 / R で手漕ぎ / 降りる / ボート中のドラッグ範囲）、film.mjs も確認する。
- **操作変更コミット（①②）**：`migration` 引数を消し、`turnRate:1.2` にする。続けて shared から `migration` の口そのものを消す（全都市が済んだため）。
  - ボート中の ←/→ は今 `yaw`（boatYaw ではない）を回している（controls.js:45-46, :78）ので、秒あたりになるだけで向きは変わらないことを確かめる。
  - ボートの見回しの制限は左右・上下対称なので、反転しても届く範囲は変わらない。`VEN.walkAt/look` と demo.json の shots（`VEN.controls.pitch = 0.35` など）は影響しないので、snap の画像が変わらないことを確かめる。

### 4.4 alhambra（最後。入力・視点だけで止めてもよい）

- 最低限の到達点は入力（キー・ドラッグ・解除）と視点を Mover に載せること。`navWalkMode`／`flyMode` まで載せるかは §4.2 の見直しの後で決める。navigation.js は**動かさない**（tour.js:24、check-walks、`ALH.move` が直接依存）。
- orbit は都市側のクライアント専用モード（`look/wheel` を持つ）にし、ポインターとホイールの持ち主を Mover に一本化する。
- 決定①②による変化は無いので、移行コミットだけで、K・T・D・M の一致を求める。
- 確認：`npm test`、`node snap.mjs out.jpg "" --verify`、`ALH.tourCheck()`、B、ツアー中の入力で止まること（キー・pointerdown・スティック・▲▼・orbit のホイール）、ダイアログを開いたときの入力解除、ミニマップの矢印、orbit のドラッグの向きが変わらないこと。

### 4.5 完了条件

- 移行コミット：§4.0 の表の「移行コミット」列を満たし（除外と該当なしを除く）、その都市の既存チェックが通り、`build-users.mjs` で再ビルドした `public/app.js` を含める。
- 操作変更コミット：表の①②の列を満たし、実機でマウスとタッチを触っている。コミットメッセージに何が変わるかを書く。
- `shared/` を変えたら、一覧にある全都市を再ビルドしてチェックし直す。**全都市が同じ Mover を使うこと自体は完了条件にしない。**
- 全都市の操作変更が済んだら、shared に `migration` の口が残っておらず、都市の設定に符号の指定が無いことを確かめる。

### 4.6 移行の後

§3.5 (6) の「移行の後」の項目を、採る権威モデルに応じて要るものだけ、それぞれ独立したコミットで入れる（§3.5 (5) の表）。権威モデルを決める前に入れてよいのは `buildId` の埋め込みだけ。

---

## 5. リスクと代替案

### 5.1 リスク

| リスク | 内容 | 対策 |
|---|---|---|
| 意図しない操作感の変化 | 合成順・補間・判定のわずかな違いで感触が変わる | §4.0 の比較。挙動を変える修正は操作変更コミットか、受け入れる修正として明記 |
| 決定②の違和感 | マウスでは一般的な一人称視点の操作と逆になる | 操作変更コミットに分けて明記する。**戻し方に注意**：`DRAG_SIGN` を戻すと alhambra を含む4都市が「見回す方式」になり、4都市の再ビルドが要る。3都市だけを決定②の前に戻すには都市ごとの符号が要り、決定②と矛盾するので、オーナーの判断を取り直す（利用者向けトグルを足す案も含めて） |
| 1箇所の変更が4都市に効く／ソースと公開物のずれ | shared を直すと全都市に影響する。再ビルドを忘れると公開物が黙ってずれる | 単体テストと `build-users.mjs` の全都市再ビルドを完了条件にし、shared を変えるコミットに全都市の bundle を含める。`buildId` を埋め込む。移行後は挙動の変更を cfg で選ぶ形に（§3.5 (4)） |
| コアの純粋さが崩れる | コアに camera・DOM・時刻・モジュール変数・three の bare import が入り込む。シングルユーザーでは気づかない | 純粋性と多重インスタンスの試験。world/cfg の関数の隠れた依存と `shared/` の bare import はレビューで見る |
| Command の取りこぼし | 互換プロパティや外部コードが state を直接書き、記録に載らない変更が生まれる | 互換プロパティの setter は Command を積む。記録した列から再生して一致することを A2 で確かめる |
| 先回り・抽象化のしすぎ | 使われない仕組みを先に作る。4都市の違いを1つのクラスに押し込む | 「いま」の項目（§3.5 (6)）に限る。通行判定は戦略に分け、都市固有のものは都市側に置き、kyoto の後で API を見直す |
| 外部からの参照が壊れる | film_page.js、ui.js、VEN/KYO フック、demo.json の shots、bridge_check.py の docstring が controls の内部に依存 | 互換プロパティを残し、位置の正本は当面 camera のまま。bridge_check.py の docstring の参照先を shared の設定に書き換える |
| 入力の取り残し | ダイアログや外部カメラ制御に移ったとき、押された入力が残る | `resetInput()` を契約にし、呼ぶ場面を都市ごとに確かめる |
| sparse checkout | `shared/` が sparse の対象から漏れるおそれ（未確認） | 共通化を入れるときに sparse checkout の設定に `shared/` を加える |

### 5.2 代替案の比較

| 案 | 概要 | 良い点 | 悪い点 | 評価 |
|---|---|---|---|---|
| **A. shared/ を相対 import（推奨）** | `demos/shared/move/` を `../../../shared/...` で読む | 共通ファイルの解決にビルド設定の変更が要らない。ソースの変更はすぐ全都市に届く（配信は再ビルドの後）。パッケージの版の固定が要らない（互換性の識別は §3.5 (4) で別に要る） | 変更がほかの都市に波及する。three に依存できない。全都市を再ビルドする入口が要る。都市ごとに shared の版を固定できない | ◎ |
| B. テンプレートを複製 | 雛形を各都市にコピー | 都市ごとに独立していて安全 | 今の「venice→kyoto の派生」がまさにこれで、すでに離れてきている。直した内容が他に伝わらない | △ |
| C. npm パッケージ | `@demos/move` を各 tools/package.json の依存に | 版を固定でき、ある都市だけ古い版に留められる | 4都市の package-lock、インストール手順、three の peerDependency、vatican・alhambra の変則的な解決との相性。個人のデモリポジトリには重い | △（都市ごとの版の固定が本当に要るようになったら再検討） |
| D. npm workspaces | ルートに workspaces | 依存の解決がまとまる | ルートの package.json はギャラリーと wrangler 用で、デプロイ経路に影響する。各都市の esbuild の版もそろっていない（0.25 系 / 0.28.1） | × |
| E. A + esbuild alias | `alias: {'@demos/move': shared/move}` | import 文が読みやすい | 4つの build_web.mjs を変える | ○（A の後でよい） |

**推奨：A 案。** 移す順は vatican → kyoto → venice → alhambra で、共通部分は段階的に入れ、各段階の前に比較データを記録する。

---

## 6. レビュー反映メモ

### 6.1 Codex 第1回レビュー（2026-10-29）への対応

**採用**（反映先）：1 `smooth:null`＝即代入（§3.2, §3.3）／2 入力の合成順を `compose` と `normalizeXY` に分離（§2, §3.2）／3 ビューアダプターが forward/right を定義し四方位の往復を試験（§3.2）／4 カメラ契約をビューアダプターに一本化し `opts.Vector3` 案を撤回（§3.1, §3.2）／5 状態の持ち主、`look/wheel`、'hold'（§3.2）／6 kyoto の walk 入場時の pitch 上限 0.6（§3.3）／7 strict/glide の2戦略に分け null→0 の変換を撤回（§3.2）／8 `build-users.mjs`、esbuild の版の固定、バイト一致は参考扱い（§3.1, §4.1）／9 全都市の再ビルドを完了条件に（§4.5）／10 共通部分を段階的に入れ kyoto の後で API を見直す（§4）／11 比較 A/B の手順を具体化（§4.0）／12 `resetInput()`・`enabled`・`onUserInput` の定義と orbit の扱い（§3.2, §4.4）。

| # | 指摘 | 対応 | 理由 |
|---|---|---|---|
| 13 | 最初から全体を統括する Mover を完成させない | 一部採用 | 段階的な導入と「全都市が Mover を使うことを完了条件にしない」は採用。Mover は薄い組み立て役として残す（部品を都市ごとに手で配線すると venice/kyoto の重複が戻る） |
| 14 | THREE.Vector3 を残す案も比較 | 不採用 | 外部が vel に使うのは `set` と x/y だけ。THREE.Vector3 を差し込むと `three` と `three/webgpu` の二系統を共通側が意識する。状態をシリアライズできることも理由 |
| 15 | 旋回は直す、alhambra は揃えない | 一部が決定で上書き | 旋回はオーナー決定で確定。ドラッグ方向は逆の結論になった（§3.4） |
| — | bridge_check.py の半径の記述（自分で見つけた点） | 修正 | docstring 0.25 m と R=0.24 の食い違いを記述（§1.1） |

### 6.2 オーナー決定と新しい前提（2026-10-29）への対応

| # | 内容 | 反映 |
|---|---|---|
| 1 | フレームレート依存の旋回は直す | §3.4 ①。操作変更コミットで秒あたりに換算 |
| 2 | ドラッグ方向は全都市をアルハンブラ方式に揃える | §3.4 ②。符号は input.js の定数、移行中だけ一時的な口。検証は §4.0 の表。venice のボートの見回しも対象 |
| 3 | 将来のマルチユーザー対応と都市別 Worker | §1.5 に配信形態を記録し、§3.5 を新設。いま作るもの・移行の後・マルチユーザー化のときを切り分けた |

### 6.3 Codex 第2回レビュー（2026-10-29、`movement-unification-codex-comments2.md`）への対応

| # | 指摘 | 対応 | 理由・反映先 |
|---|---|---|---|
| 1-a | 固定ステップだけでは入力列が揃わない。tick ごとの入力割り当てが要る | 採用 | 「約束すること／しないこと」を分け、固定ステップ導入時の tick の契約（キー・旋回・ドラッグ・Command の割り当て）を表にした（§3.5 (1)） |
| 1-b | 最大ステップ数を超えた余剰時間・非表示からの復帰が未定義 | 採用 | 今のコードは上限を超えた分を捨てていることを確認（§1.5）。同じく「捨てる」、復帰でアキュムレーターを 0 に、と定義（§3.5 (1)） |
| 1-c | 「perFrame を消すことが step を関数にする前提」は不正確 | 採用 | 目的は描画回数への依存の除去、と書き直した（§3.4 ①） |
| 1-d | 丸め差が衝突境界で分岐差に広がる。スナップショット・再実行・補間が要り得る | 採用 | §3.5 (1) と §5.1 に留保を足した |
| 2-a | InputFrame に速度変更や command の順序が載っていない | 採用 | 再生可能な入力を「Command の列 ＋ InputFrame」と定義し、ホイールを `setSpeed` にした。状態を変えるものはすべて Command を通す（§3.2） |
| 2-b | `place` を純粋コアで処理できることと、ネットワークで受理することを混同しない | 採用 | §3.2 と §3.5 (3) の C で分けた |
| 2-c | 連番・最終処理番号・command 順序を後で足す前提、受信境界での検査 | 採用 | 記録の形を広げられるようにし、受信境界の検査項目を列挙した（§3.5 (2)） |
| 3-a | MOVE_VERSION だけでは一致を判定できない（入力側の変更、cfg、世界データ） | 採用 | `MOVE_SCHEMA`・`MOVE_VERSION`・`cfgId`・`worldId`・`buildId` に分け、何が違えば拒否・変換・診断かを表にした（§3.5 (4)） |
| 3-b | bundle の診断にソースコミットは不十分。実際に束ねた入力の識別が要る | 採用 | `buildId` を esbuild の metafile から作る（§3.5 (4)） |
| 3-c | 「同じコミットから一緒にデプロイ」は再生成とデータの対応確認まで含めて意味を持つ。既存接続と DO の保存状態 | 採用 | 原則に条件を付け、マルチユーザー化のときの設計項目に加えた（§3.5 (4), (6)） |
| 4-a | 終点だけの検査では壁抜けを防げない。速度上限はサーバー時刻と受理済み状態を基準に | 採用 | 権威モデルの表に「保証すること／しないこと」を書いた（§3.5 (3)） |
| 4-b | 検証しない姿勢を自由に選べると検査を迂回できる | 採用 | 切替を Command としてサーバーが許可し、検証しない姿勢は「カメラ」として別に扱う、と境界を書いた（§3.5 (3)） |
| 4-c | 「移動入力を送らない」は停止の代わりにならない。hold の扱い | 採用（方式の選択はマルチユーザー化のとき） | 理由を明記し、(a) サーバーは進めてクライアントは予測を止める、(b) hold を明示、の2案を書き、(a) を自然な案とした。tick 上の hold の規則は §3.5 (1) で定義 |
| 4-d | 「サーバーは全データを持つ」と「タイル単位で読む」の食い違い。world は同期関数 | 採用 | 世界データの準備を step の外に置き、未準備は hold、という境界条件にした（§3.5 (1), (3)） |
| 4-e | 都市ごとの Worker と DO の分割単位は別問題 | 採用 | §3.5 (3) に明記 |
| 5-a | 「純粋だが state を書き換えてよい」は用語上矛盾 | 採用 | 「外部副作用のない更新関数。state を破壊的に更新する」とし、スナップショットは複製から、と書いた（§3.2） |
| 5-b | world の注入だけでは純粋にならない。全都市が厳密に純粋になると約束しない | 採用 | 保証を「同じ world の内容なら同じ結果」に限定。ソース検査と node 実行は補助と明記（§3.2, §4.0） |
| 5-c | 構造化複製でもメソッドは残らない。NaN/Infinity と意図的な null の区別 | 採用 | `toPlain/fromPlain` の契約を§3.2 に新設 |
| 6-a | `drag.sign` を公開 InputOptions に残すと「都市ごとの変更を禁止」と噛み合わない | 採用 | 符号を `input.js` の定数に閉じ、移行中だけの `migration` 引数（`perFrame` と同居）にして、全都市の操作変更後に口ごと消す。前回の「将来のトグルのために残す」理由は撤回（トグルを作るなら別の機能追加として設計する）（§3.4 ②） |
| 6-b | 「既定値1箇所を戻せば済む」は alhambra にも及ぶ | 採用 | 戻すと4都市すべてが変わり4都市の再ビルドが要ること、3都市だけ戻すには決定のやり直しが要ることを書いた（§5.1） |
| 6-c | InputFrame 化でドラッグを合算して最後に clamp すると往復で一致しない。比較 A で完成済み yaw/pitch を渡すだけでは係数・符号の誤りを検出できない | 採用 | イベント順の clamp を保つことを §3.2・§3.4 に明記。入力列 D に制限の端の往復（venice は boat の制限も）を入れ、比較 A を A1 入力変換（リスナーを通す）と A2 移動に分けた（§4.0） |
| 7-1 | 共通の検証表を一つに | 採用 | §4.0 に表を作り、各都市の節は都市固有の点だけにした |
| 7-2/7-3 | 各都市2コミットを基本に、または①②の順番を固定。基準は直前の成功済み版 | 採用（2コミット案） | 移行コミット → 操作変更コミット（kyoto/venice は①②同居で、旋回だけ・ドラッグだけ・混合を分けて検証）。操作変更の基準版は移行コミット（§4） |
| 7-4 | 固定ステップは別変更、クライアント申告型では必須にしない。WalkGrid も必要になってから | 採用 | 権威モデルごとに要るものの表（§3.5 (5)）と §4.6 |
| 8-1 | 版管理の既定ルールが決定②と衝突 | 採用 | ①②は今回の全都市移行の例外、移行後の変更に既定を変えない規則を適用、と時期で分けた（§3.5 (4)） |
| 8-2 | A案「バージョン管理が要らない」「変更がすぐ全都市に届く」 | 採用 | 「パッケージの版の固定が要らない（互換性の識別は別に要る）」「ソースは届くが配信は再ビルドの後」に直した（§5.2） |
| 8-3 | 「完全一致」と許容誤差の混在、§4.5 の vatican の除外 | 採用 | 「一致＝1e-6 以内」に統一し、B の超過時の扱いを決めた。完了条件に除外と該当なしを入れた（§4.0, §4.5） |
| 8-4 | vatican の変更範囲が3点に限定されているのは不正確 | 採用 | コードで確認：vatican のホイールはモードも `enabled` も見ない、index.html に入力欄は無い。受け入れる修正と保つものの表にし、ホイールは保つ（`wheel.modes:null`、Command は `enabled` に関係なく適用）。T は該当なし（§1.3, §4.1） |
| 8-5 | 専用モードの後に view.apply を無条件に呼ぶと上書きする | 採用 | update の手順でクライアント専用モードはそこで終わる、とした（§3.2） |
| 8-6 | 「いま3点だけ」「追加コストは小さい」は控えめすぎる。『いま』から決定②も参照、§4.6 の『任意』『前提』を権威モデルごとに | 採用 | 作業量が増える内訳を書き、いまやる理由を「再生可能な境界が移行の比較にも使えること」にした。「いま」に①②を入れ、§4.6 は §3.5 (5) の表に従う形にした（§3.5 (6), §4.6） |
| — | 全体の圧縮（自分の判断） | 実施 | §3.4 と §4 の都市ごとの検証手順を §4.0 の表に集約し、§1・§2・§5.1・§6.1 の繰り返しを削った。上の契約（tick、Command、識別子、権威モデル）を足したので、全体は 94KB から 90KB への縮小に留まる |
