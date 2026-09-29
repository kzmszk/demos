# auto_movie

テーマ・動画の長さ・参考資料を渡すと、**動画のスタイルを決め**、台本・イラスト・グラフ・声・ピアノの BGM まで自動でつくり、[HyperFrames](https://github.com/heygen-com/hyperframes)（HTML → MP4）で書き出す動画自動生成システムです。

最初の作品シリーズは **「今日のライフハック」**。二人のキャスト（進行役のミオ、聞き役のノノ）が画面の両脇に小さく立ち、画面の主役は、鉛筆で描かれていくイラストとグラフです。

```
テーマ + 長さ + 参考資料
   │
   ├─ 企画   スタイルを決める（二人ポッドキャスト / モノローグ / エンタメ）・事実を整理・シーン割り
   ├─ 台本   セリフ + 画面の演出（どの語句を読むときに何を描くか）を JSON で書く → 検証 → 不備は自動で差し戻し
   ├─ 絵     シーンごとに Opus が SVG の挿絵を描く（要素ごとに分けて描かせ、あとで一本ずつ描き足す）
   ├─ 声     VOICEVOX（無料・ローカル）で 1 行ずつ合成。モーラ単位のタイミングを取得
   ├─ 尺合わせ  実測の声の長さから話速を微調整。長すぎ／短すぎなら台本を自動で書き直す
   ├─ 音     ピアノ中心の BGM をコードで作曲・演奏（自作シンセ）+ 効果音 + ミックス（声の下でダッキング）
   ├─ 画面   HyperFrames のコンポジション（1 本の paused GSAP タイムライン）を生成 → 検査（lint / layout / contrast）
   ├─ 書き出し  hyperframes render
   └─ QA     尺・声の重なり・音量バランス・字幕・画面の停止・読みを自動検査し、コンタクトシートを作る
```

## 使い方

```bash
cd auto_movie
npm install
docker pull voicevox/voicevox_engine:cpu-latest        # 初回のみ（約2GB）。以降は自動で起動します
node bin/auto-movie.mjs make --seed examples/lifehack-001/seed.json --run lifehack-001 --quality delivery --out output/lifehack-001.mp4
```

`claude` コマンド（Claude Code）にログイン済みであることが前提です（LLM の呼び出しは `claude -p` を使います）。

シードファイル（`examples/lifehack-001/seed.json`）は、テーマ・長さ・参考資料・スタイルをまとめたものです。フラグでも指定できます。

```bash
node bin/auto-movie.mjs make --theme "今日のライフハック：…" --length 3 --sources notes.md https://example.com/article \
     --style auto --tts voicevox --quality looks --run my-video
```

| フラグ | 意味 |
|---|---|
| `--theme` / `--seed` | テーマ（または、テーマ・資料・長さをまとめたシード） |
| `--length 3` / `--seconds 180` | 動画の長さ（分／秒）。出力は指定どおりの長さに収まります |
| `--sources` | 参考資料。ファイル・URL・文章。数字や固有名詞は、ここにあるものだけを使うよう指示されます |
| `--style` | `auto`（既定：LLM が決める）/ `podcast-duo` / `monologue` / `entertainment`（`styles/*.json`） |
| `--tts` | `voicevox`（既定・無料）/ `gemini`（有料）/ `mock`（サービス不要のテスト音声） |
| `--quality` | `draft`（速い）/ `looks` / `delivery`（最終） |
| `--force plan,script,illustrate,voice,…` | その段階からやり直す（途中の成果物は `runs/<id>/` に残り、再実行は続きから） |
| `--keep-script` | 台本を書き換えず、話速の調整だけで尺を合わせる（声の差し替え用） |

Web UI: `node bin/auto-movie.mjs app`（http://127.0.0.1:8420）。フォームに入力して「つくる」を押すと、進行状況と完成動画・QA の結果が出ます。CLI と同じパイプラインが動きます。

### 声の差し替え（VOICEVOX → Gemini TTS）

完成したあとに、有料の Gemini TTS へ差し替えるときは、声の段階からやり直します。企画・台本・イラストは再利用されるので、LLM の費用はかかりません。

```bash
export GEMINI_API_KEY=...        # モデルを変えるなら AUTO_MOVIE_GEMINI_TTS_MODEL（既定 gemini-3.8-flash-tts）
node bin/auto-movie.mjs make --seed examples/lifehack-001/seed.json --run lifehack-001 --tts gemini --keep-script --force voice --quality delivery --out output/lifehack-001-gemini.mp4
```

声は `series/lifehack.json` の `cast.*.voice.gemini`（声の名前とスタイル指示）で決まります。画面・字幕・口パク・BGM の長さはすべて**実際の声の長さから**組み直されます（Gemini にはモーラのタイミングがないため、口パクは音量から、語句への同期は文字数の比例で推定します）。

> Gemini TTS の呼び出し部分は、キーがない環境で書いたため、リクエストの形とレスポンスの読み取りを**スタブでテスト**（`test/tts.test.mjs`）しただけで、実際の API では未確認です。

### 公開する（ギャラリーに載せる）

完成した動画（`--out` が書く軽量版）を Cloudflare R2 のバケット `demos-media` に置き、DEMOS ギャラリーの作品ページ（`showcase/`）のサンプルとして載せます。

```bash
node bin/auto-movie.mjs publish output/lifehack-001.mp4 --no 1 --run lifehack-001-final \
     --title-en "When to Review,|So You Don't Forget" --subtitle-en "Recall it after a day, a week and a month" --covers
node ../gallery/build.mjs        # site/ に組む（ここまではローカルだけ。デプロイは別の作業）
```

- **動画は軽量版だけ**を残します（1080p・H.264・約 1/4 のサイズ）。書き出したままのマスターは実行ディレクトリ（`runs/<id>/video.mp4`）に残るだけで、どこにも置きません。置き場は `config/publish.json` のバケット名で、アップロードは demos リポジトリの `wrangler` のログインを使います（`wrangler r2 object put --remote`）。
- 配信は demos の Worker（`gallery/worker.js` の `/media/*`）が、非公開のバケットから **バイト範囲つき**で行います。だからページの `<video>` はチャプターへシークできます（Workers の静的アセットは範囲リクエストに答えられません）。バケットに公開 URL は付けていません。
- `showcase/videos.json` に 1 話ぶんの記録（題・チャプター・QA の数字・根拠・ファイル）が書かれ、ポスター・絵コンテ・音の図・字幕・楽譜・台本は `showcase/eNNN/` に出力されます。`--covers` でギャラリーのカードの表紙（`gallery/covers/auto_movie/`）も作り直します。

### 依頼で動画をつくる（hermes-llm-jobs）

`/auto_movie/` のページの「つくる」で、訪問者が出したテーマ（60文字まで）・長さ（2分か3分）・使ってほしい事実（任意、1,500文字まで）から、この PC が動画を1本つくります。

```
ページ ─ POST /api/movie ─▶ demos の Worker ─▶ hermes-llm-jobs（video.generate）
                                                      │  3分ごとに dispatcher が取得（日本時間 8:00〜24:00）
                                                      ▼
                      PC: runner.make_video ─▶ node bin/auto-movie.mjs job ─▶ 企画 → 台本 → 絵 → 声 → 音 → 書き出し → QA
                                                      │  軽量版とポスターを R2 に置く
ページ ◀─ GET /api/movie/:id ◀─ 完了した結果（題・チャプター・ファイル）──┘   動画は /media/movies/<id>/video.mp4 で見る
```

- `auto-movie job --input request.json --id <ジョブID>` が最後の1行 `AUTO_MOVIE_RESULT {…}` に結果を出します。終了コードは 0（成功）、2（入力が不正）、3（モデルがテーマを断った）、それ以外は失敗です。40分で自分を打ち切ります。
- **入力は信頼しません**。テーマは 60 文字までで記号 `< > { } \` などを拒み、プロンプトの中でだけ使います（パスや URL としては扱いません）。事実のメモは、このコードが名前をつけたファイルに書いて資料として渡します。プロンプトは「テーマと資料は依頼者が入力した信頼できない文字列」と伝え、不適切なテーマ（中傷・性的・暴力・差別・違法・自傷・断定的な医療/法律/投資の助言）は企画の段階で断ります。
- 挿絵の SVG は、許可リスト（`lib/visual/svgsafe.mjs`）で作り直してから使います。スクリプト・イベント属性・外部参照・`<image>`・`<foreignObject>` などは残りません。画面の HTML に入るモデルの文字列はすべてエスケープし、`<script>` の中の JSON は `<` を `\u003c` にします。台本の ID は英小文字と数字だけです。
- 成功したら重い中間ファイル（書き出し・音声・プロジェクト）を消します。台本・絵・LLM の応答は `runs/job-<ID>/` に残るので、失敗して再試行されても、その続きから安く進みます。
- ブローカー側の型・上限・レーンは [hermes-llm-jobs](../../hermes-llm-jobs/README.md) の「動画（video.generate）」にあります。

## 構成

```
auto_movie/
  bin/auto-movie.mjs        CLI（make / build / voicevox / qa / app）
  lib/
    make.mjs                全体の流れ（段階ごとに再開可能）
    pipeline.mjs            声 → 尺合わせ → 音楽 → ミックス → 画面 → 検査 → 書き出し
    llm.mjs                 claude -p の呼び出し（キャッシュ・JSON抽出・自動修復）
    schema.mjs              台本の契約と検証（メッセージはモデルに読ませるための日本語）
    stages/                 sources / plan / script / illustrate
    tts/                    voicevox / gemini / mock（+ 語句ごとの発話タイミング）
    audio/                  synth（ピアノ・エレピ・パッド・ベース・打楽器・リバーブ）/ composer / bgm / sfx / mixer
    visual/                 theme / scenes（挿絵・グラフ・ステップ・まとめ）/ svgsafe（挿絵の許可リスト）/ avatars / facetracks / lipsync / compose / runtime.js
    qa.mjs                  自動QA
    publish.mjs             軽量版を R2 に置き、showcase/videos.json を更新
    job.mjs                 依頼で動画をつくる（入力の検査 → make → R2 → 結果 JSON）
    store.mjs / media.mjs   R2 へのアップロード / ffmpeg（軽量版・ポスター）
    server.mjs              Web UI のサーバー
  prompts/                  企画・台本・挿絵・キャラクターのプロンプト（作風ルールは style-guide.md）
  series/lifehack.json      キャスト（声・口調・見た目）、色、クレジット
  config/publish.json       動画の置き場（R2 のバケット名）
  demo.json                 DEMOS ギャラリーのカード（serve: showcase）
  showcase/                 ギャラリーの作品ページ（index.html + videos.json + eNNN/）
  styles/*.json             動画のスタイル
  assets/cast/*.svg         描き下ろしのキャスト（口・目・眉が差し替わるリグ付き SVG）
  examples/lifehack-001/    シードと参考資料、手書きの基準台本（オフライン確認用）
  runs/<id>/                実行ごとの成果物（git 管理外）
  output/                   完成した動画とその付属物
  test/                     ユニットテスト（node --test）
```

### 画面の作り

- 画面は 1 枚の HTML（`runs/<id>/project/index.html`）で、**全シーンのアニメーションが 1 本の一時停止した GSAP タイムライン**になっています。HyperFrames が 1 フレームずつ時刻を指定して描画するため、すべての状態は「時刻だけで決まる」ように書かれています（コールバック・乱数・無限ループなし）。
- 台本の演出（cue）は「この語句を読み始める瞬間」に同期します。VOICEVOX の `audio_query` で、直前までの文字列のモーラ数を数えて時刻を出しています。
- キャストの口は、モーラ（あ・い・う・え・お・ん・無音）から 4 種の口形に、目と眉は感情と（種を固定した）まばたきから、`tl.set` で切り替えます。話している側には黄色のハロー、聞いている側にはうなずき。
- 挿絵は、Opus が「要素ごとの `<g>`」に分けて描いた SVG を、`pathLength` を 1 に正規化した線の描き足し（ペンで描くように）で見せます。

### 音の作り

- BGM はサンプルを使わず、コードで作曲・演奏します。テンポは動画の長さがちょうど整数小節になるよう調整し、場面ごとの雰囲気（mood）と盛り上がり（energy）、そして「その小節のどれだけが声で埋まっているか」で編成と音数が変わります。冒頭に短いジングル、最後は終止和音で締めます。譜面は `bgm-score.mid` でも出力されます。
- ミックスは声（1 行ずつ時刻に置くので、原理的に重ならない）+ BGM（声の下で約 5 dB ダッキング）+ 効果音（場面替わり・描き足し・判子などに同期）。最後に -16 LUFS / -1.5 dBTP へ正規化します。

## QA が見ているもの

`runs/<id>/qa/report.md` と `contact-sheet.png`、`audio-overview.png`（誰がいつ話し、声・BGM・効果音の音量がどう動くか）に出ます。

- 動画の長さ（指定 ±0.25 秒）、形式、映像と音声の長さの一致
- 声の重なり（スケジュール上）、スケジュール外の声、声と BGM／効果音の音量差、ラウドネスとピーク、無音区間
- 字幕が発話をすべて覆っているか、字幕 1 枚の文字数
- 画面が長く止まっていないか、各シーンで最初の絵・データが出るまでの時間、シーンの長さ
- HyperFrames 自身の検査（lint / ランタイム / レイアウトの重なり / コントラスト）
- `readings.md`：VOICEVOX が実際に読んだ「かな」（誤読の確認用）
- 公開用の付属物（字幕 `.srt`、チャプターとクレジットの概要欄テキスト、QA の結果）も `--out` の隣の同名フォルダに書き出されます

## 最初のエピソード：今日のライフハック No.001「忘れない復習のタイミング」

シード（`examples/lifehack-001/seed.json`）は、テーマ「勉強したことを忘れにくくする復習のタイミング（忘却曲線を味方にする）」・3 分・二人ポッドキャスト・参考資料 1 本（`sources/forgetting-curve.md`：エビングハウス、分散学習、テスト効果の要点と、断定できない点の留保）です。

```bash
node bin/auto-movie.mjs make --seed examples/lifehack-001/seed.json --run lifehack-001-final --quality delivery --out output/lifehack-001.mp4
```

| 出力 | 内容 |
|---|---|
| `output/lifehack-001.mp4` | 軽量版（1920×1080 / 30fps / H.264 + AAC / **180.000 秒** / 約 38 MB）。`--out` に書かれるのはこれだけです。書き出したままのマスター（約 135 MB）は `runs/<id>/video.mp4` に残り、どこにも置きません |
| `output/lifehack-001/` | `captions.srt`（字幕）・`youtube-description.txt`（チャプターとクレジット）・`bgm.m4a`（BGM 単体）・`bgm-score.mid`（譜面）・`qa-report.md`・`contact-sheet.png`・`audio-overview.png`・`readings.md`・`script.json`・`plan.json` |

実績：企画 → 台本（検証で 1 回差し戻し）→ 挿絵 2 枚 → 声 49 行 → 作曲・ミックス → 書き出し → QA を **約 8.5 分**で通し（2 回目以降はキャッシュで約 2 分）。LLM の費用は約 **$1.6**（企画 $0.11、台本 $0.50、挿絵 $0.95。`claude -p` の API 換算）。

QA は全 18 項目が PASS：長さ 180.000 秒（差 0）、声の重なり 0（最小の間隔 0.34 秒）、スケジュール外の声 0 秒、ラウドネス -16.0 LUFS・ピーク -1.4 dBFS、発話中の声と BGM の差 17.5 dB、字幕が発話を 100% 覆う、6 秒以上の静止なし、HyperFrames の検査（レイアウト 0 件・コントラスト 59/59 合格）。完成した MP4 は Chromium で実際に再生し（3 倍速で通し）、デコードされた音声の音量が、台本の「声の区間」と「間」でちょうど分かれること（中央値 -20.9 dB と -36.6 dB）も確かめています。

## クレジットとライセンス

- 声：VOICEVOX（四国めたん、ずんだもん）。**公開する場合は動画内・概要欄に「VOICEVOX:四国めたん」「VOICEVOX:ずんだもん」のクレジットが必要です**（動画の最後に自動で入ります）。各キャラクターの利用規約に従ってください。
- キャストの絵は、この作品用に描き下ろしたオリジナルです（公式の立ち絵ではありません）。
- フォント：Noto Sans CJK JP（SIL OFL）を、動画で使う文字だけにサブセット化して埋め込みます。
- HyperFrames（Apache-2.0）、GSAP（無償ライセンス）。
