# バチカン移行レビュー

対象：ブランチ `move-unification` の `628ce7c`（準備）と `632a8ea`（移行）。基準：`docs/movement-unification-proposal.md`、特に §3.2／§3.3／§4.0／§4.1。設計書は sparse checkout で未展開のため `git show HEAD:docs/movement-unification-proposal.md` から読んだ。

## 結論

バチカンの通常の入力・移動について、今回の固定スクリプト上の挙動保存は確認できた。`sum` の W+↑ の期待値を 1 にした判断も正しい。ただし、再現可能なビルド依存の宣言、`place` の殻とコアの受け渡し、設計で必須とした実シーン比較に不足がある。移行完了としては必須修正あり。

## 指摘

### 1. 【必須修正】esbuild が依存・lockfile に無く、準備コミットだけでは新規環境のビルドを直せない

根拠：`vatican/tools/build_web.mjs:2`、`vatican/tools/package.json`、`vatican/tools/package-lock.json`、設計 §3.1／§4.0／§4.1。

絶対パスを `import ... from 'esbuild'` に変える方向は正しい。しかし package.json に esbuild が無く、lockfile にも項目が無い。今回の環境には node_modules/esbuild 0.28.1 があるが、管理された依存からその存在・版を復元できない。ルートから偶然解決できる場合も都市ごとの版固定にはならない。クリーンな環境で都市の依存だけを導入すると失敗し得る。

準備コミットで都市のビルド依存として esbuild と lockfile を追加し、版を固定してビルドできることを確認する必要がある。バイト一致は有用な補助証拠だが、依存宣言の代わりにはならない。

### 2. 【必須修正】殻に渡した `place` がカメラの旧位置と入力の旧視点で消される

根拠：`shared/move/mover.js:36-59`、`shared/move/step.js:17-20,37-41`、設計 §3.2 の Command と状態の持ち主。

`update()` は Command 適用後、`view.readPos()` と state の差をすべて外部カメラ移動と見なし、もう一つの `place` でカメラ位置に戻す。さらに `apply(place)` は入力側の yaw/pitch を更新しないため、その直後の `step()` が frame の古い yaw/pitch を上書きする。

最小再現：位置・視点が 0 の Mover に `queue.push({type:'place',pos:{x:100,y:0,z:0},yaw:1,pitch:.5})` を入れて `update(0)`。実測は pos=(0,0,0)、yaw=0、pitch=0。コア単体の `command(place)` とは意味が異なる。公開 `apply(place)` を先に呼んでも、次の update で同様に消える。

現在の Vatican は先にカメラを置き `syncFromCamera()` で入力も同期するため、この不具合を踏まない。しかし `place` は将来の walkAt/goPlace/降船/film のために定義した境界であり、現時点の共通 API の不整合である。カメラ由来の変更と明示 Command の優先順位を定め、明示 place の位置を適用し、指定 yaw/pitch を入力側にも反映する必要がある。今後 setMode で walk 入場時の pitch を制限する際も、入力への書き戻しを忘れると同じ問題になる。殻経由の place とその記録再生を検証したい。

### 3. 【必須修正】§4.0 の B（実シーン比較）が無く、移行完了の根拠が A に限られる

根拠：`vatican/tools/trace/app.mjs`、`fake.mjs`、`run.mjs`、未変更の `vatican/tools/web/main.js:273-276`、設計 §4.0／§4.1／§4.5。

準備コミットは build_web の1行だけで、指定された `VAT.controls` フックも比較データも含まない。移行コミットにある比較は node の偽カメラと main.js を縮約したアプリによるもの。実ブラウザーの K/D 比較や既存 snap の結果は成果物・コミット説明から確認できない。こちらでもブラウザー検証は実施していない。

B は A と別の必須行であり、誤差0でも代替できない。実 main.js・THREE.Camera・実イベントで旧新を測り、結果と再実行手順を残す必要がある。設計指定の `stopLoop()` → 2フレーム待つ → `look()` → 入力の手順を使う。準備フックと移行を分離する方針に合わせて整理するか、設計との手順差を明示すること。

### 4. 【推奨】専用モードの記録は、全体を再生可能なログとして扱えない

根拠：`shared/move/mover.js:54-56,62-64`、設計 §3.2 の専用モード契約。

専用モードでは `frame:null` を記録してから `client.update()` がカメラを置く。コア再生はその tick を停止と扱うため、その tick の最終位置を再現できない。次の tick のカメラ取り込みで追いつく場合はあるが、ログ末尾やモード中の状態列は一致しない。`look/wheel` による専用状態もログに無い。

専用モードをコアへ押し込む必要はない。設計どおりブラウザー専用のままでよいが、startRecording のコメントは「コアモード区間の再生」を保証範囲として明示し、専用区間を識別するか、必要なスナップショットを別途記録することを推奨する。今回の Vatican の title/tour は clientModes ではなく外部制御なので、この欠落を検証してはいない。

### 5. 【推奨】初期専用モードの enter が呼ばれない

根拠：`shared/move/mover.js:15-34,36-42`。

enter/exit は setMode 適用時だけで、constructor の `mode` が専用モードでも enter は実行されない。初期 orbit/boat の初期化を enter に置く実装では、切替で入った場合と起動時で違いが出る。起動時にも初期化するか、初期専用モードは禁止・別途初期化という契約を明記し、試験を加えるのがよい。Vatican への直接の影響は無い。

### 6. 【推奨】最初の試験項目のうち hidden と hold が未検証

根拠：`shared/move/move.test.mjs`、設計 §4.0「shared/move/ の最初の中身」。

blur/resetInput は試験済みだが、document.hidden と visibilitychange の経路は無い。hold のとき位置・視点を適用しない分岐も試験されていない。現在 fly は常に ok を返すため、hold を返すモードはまだ無い。歩行導入時に early return と入力側の旋回継続を実際に試すこと。pointerId/pointercancel の単体試験も、別IDのmoveはあるが cancel や別IDのupまで網羅してはいない。

## 挙動保存と「最大誤差0」の意味

### 実施した確認

- `node shared/move/move.test.mjs`：13試験成功。`node --test shared/move/move.test.mjs` も成功（この環境の表示はファイル単位の1件）。
- `node vatican/tools/trace/run.mjs /tmp/vatican-new.json` と `--orig /tmp/vatican-orig.json` を実行。それぞれ同梱 golden と比較し、1001サンプル全量で pos/dir/yaw/pitch/vel/speed の最大誤差0、mode/enabled も一致。
- 新側の JSON 往復ログ747 tick をコアで再生し、毎 tick の位置誤差0。
- `trace/fly.orig.js` は `628ce7c:vatican/tools/web/fly.js` と SHA-256 が一致。旧実装の基準として適切。
- 現環境の esbuild 0.28.1 で本番同等のオプションを使い、出力先だけ `/tmp` にしてビルド。コミット済み public/app.js と SHA-256 が一致。ソース・公開 bundle の対応は確認できた。クリーンインストール可能性は確認できていない。

### カバーするもの

完成済みの yaw/pitch を直接コアに注入するだけの比較ではない。旧新の実際のリスナー関数を偽 EventTarget の key/pointer/wheel イベントで通しているため、A1 の符号・係数・合成と A2 の移動の両方について意味がある。

K は移動、斜め、両Shift、別名キーのOR、逆方向の相殺、上下降、複数 dt を含む。D は mouse/touch、pitch 上下限への到達と往復を含み、複数イベント間に step が無い区間もある。このため「合算して最後だけ clamp」の誤実装を検出できる。M は移動中の drag とキーの混合である。

W は2〜400への到達、同 tick の連続ホイール、正負・deltaY=0を含む。Input が毎回 queue 上の最新 speed を読むので、連続ホイールも逐次乗算と逐次 clamp が保たれる。Vatican は wheel.modes=null で enabled を見ず、preventDefault を呼ぶ。speed getter は適用待ちの値も返すため、通常のイベント直後の観測値も旧実装に合う。

S は縮約アプリの title/free/tour、F、look、stopLoop、無効中のキー収集・ホイール・drag原点維持と復帰を扱う。Vatican のアプリモード切替は setMode Command ではないので vel をゼロにせず持ち越す点も旧挙動どおりである。

### カバーしないもの・留保

- 偽 EventTarget はブラウザーのイベント伝播、実際のフォーカス、pointer capture/lostpointercapture、タッチの既定動作やブラウザー差を再現しない。偽カメラは THREE の行列・quaternion・up の計算を使わない。three-hook は依存欠落時に shim へ切り替わるため、実 three を使ったかも記録するとよい。
- app.mjs は main.js の複製・縮約で、ツアー軌道は代用品。実 UI、ready Promise、音の時計、RAF の停止・予約済みフレーム、実シーンの初期化順までは検証しない。将来 main.js と乖離しても自動検出しない。
- blur、pointercancel、複数ポインターによる旧新差は意図的に除外。これは §4.1 が認めた変更なので誤りではない。入力欄の除外も承認済みで、現 index.html には入力欄が無い。
- preventDefault の有無は golden の比較項目ではない（新側の単体試験にはある）。A1 の軸値も直接比較せず、移動への反映から間接的に確かめている。
- ログ再生が比較するのは位置だけ。向き・vel・speed・status を含む「コア状態列すべて」の一致の証明ではない。旧新トレースには向き等もあるが、再生の試験とは別である。
- 比較器の合格基準は 1e-6。今回たまたま0だったことを一般的な完全等価性の保証にしてはいけない。全キー組合せ・任意イベント順・任意の初期状態は網羅していない。例えば旧版は forward/back を個別にベクトル加減算し、新版は軸を先に相殺するので、反対キーと横移動の組合せでは微小な浮動小数点差が生じ得る。設計の許容誤差内なら問題ではない。

## compose テスト変更の評価

**期待値を `sum` でも W+↑=1 にした修正は妥当。必須修正ではない。**

alhambra/tools/web/main.js:177-182 は `(keys.has('w') || keys.has('arrowup') ? 1 : 0)` としており、同じアクションの別名キーは OR。W+↑ で2にはならない。W+↑+S もキー軸は0で、修正後テストと一致する。

設計 §3.2 の sum は、別名キーを全数カウントする指定ではない。キー軸に stick/vert/alt を足した後に成分を ±1 に丸めるかどうかの指定で、水平正規化はその後モード側が行う。例えば alhambra の W とスティック前進の合計2は丸めず、横成分も含めて normalizeXY する。上下の E+alt はそのまま2になり得る。

ただし現 Input には stick/vert/alt が無く、any() は0/1のみなので、現実装では clampEach と sum の出力は常に同じ範囲になる。このテストは「別名キーの OR」の回帰試験であり、compose の差を試したものではない。タッチ入力を入れる都市の移行時に、キー＋スティック、上下＋vert/alt、normalizeXY の順序を検証する必要がある。期待値を2へ戻すことは逆に現行挙動と食い違う。

## API の設計適合性と将来の都市

- コアは three/DOM/時刻/乱数を使わず、state を引数内で更新する。pos はプレーン、vel は Vec3 だが、これは設計が明記した内部表現であり、クラスがあること自体は違反ではない。
- toPlain は独立したプレーンデータを作り、fromPlain は schema、有限数、status、walk.z だけの意図的 null を検査して Vec3 を復元する。JSON／structuredClone の両方の試験も適切。MOVE_SCHEMA 以外の識別子や固定ステップが無いことは、後工程として設計済みなので問題ではない。
- Command は離散操作のプレーンデータで、wheel は setSpeed 列に入る。外部カメラ位置も place として取り込む方向はよい。ただし指摘2の優先順位問題がある。place の yaw/pitch は有限値を検査せず NaN も入るため、将来の受信境界での検査とは別に、ローカル command の引数規約も整理するとよい。
- zUpView は read/readPos/apply と forward/right/up、cfg.axes の分離を実装し、Vatican の camera.up を変更しない。四方位と往復の試験もある。alhambra 軸／アダプターは未実装で、現時点の cfg.axes は zUp だけである。
- fly のみの STEPS、followPitch:true の明示的エラー、ラスター戦略の未実装は、§4.0 の最初の導入範囲および §4.2 の段階導入に沿う。今回から全都市分を完成させる必要はない。kyoto で STEPS とモード入場処理、axes、タッチ互換口を拡張すれば載せられるので、「今未実装＝将来載せられない」とは評価しない。
- Navigation は都市側に保持できる。入力・視点だけの採用や client update を使う構成も可能で、navWalk をコアに載せる場合は新しい kind と world 経由の受け渡しを足す必要がある。update 関数の有無で client 判定する契約は明記しておきたい。
- 専用モードへの look/wheel は二重処理せず、look はイベント単位で係数と符号を掛けて渡し、専用 update の後は view.apply せず終了する。§3.2 に合う。初期 enter と記録範囲は指摘4・5のとおり。
- setMode の walk 初期化（walk.z のリセット、探索、pitchOnEnter と入力への書き戻し）、move/vert/fastLatch/alt/walkZ の互換プロパティは未実装。Vatican では不要だが、kyoto 導入前の実装・試験項目として残すこと。vel.set() の外部変更も現録画には Command として載らないため、film を含む記録範囲の拡張時に対応が要る。

## コミット構成・成果物

- build_web の環境依存解消と挙動移行を分けたことは適切。移行に migration.dragSign=-1 を残し、決定②を別コミットにする点も設計どおり。今回の2コミットに操作変更まで含まれていないこと自体は問題ではない。
- ただし準備は依存固定・VAT.controls フック・比較データまで含む設計だった。実際は build の1行だけで、旧コード／golden／比較器が移行と同居している。旧コードのハッシュと golden の再生成一致を確認できたので基準の捏造等を疑う根拠はないが、「移行前に成功済みの測定」をレビューしやすい構成にはなっていない。
- golden.json の同梱は適切。旧コード・入力スクリプト・比較器が一緒にあり、期待値を再生成して由来を確認できる。更新時には旧実装からの再生成なのか、操作変更の反転期待値なのかを区別すること。
- trace/.gitignore の `out.json` は妥当。実行のたび変わる出力だけを除外し、golden は追跡対象。`git check-ignore` でもその区別を確認した。
- public/app.js の同梱と build-users の都市一覧が Vatican だけであることは適切。現時点で shared を使うのは Vatican のみ。sparse-checkout の shared も設定済み。

**最終判定：必須修正あり（依存・版固定、place の同期契約、実シーン比較）。** コードは変更せず、このレビュー文書だけを追加した。
