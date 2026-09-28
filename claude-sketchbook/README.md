# Claude のスケッチブック

ランプの下に閉じたスケッチブック。ひらくと10ページが、ひと筆ずつ描かれていく。手書きの字、線、絵具、紙、本、音楽、効果音まで、すべてコードで作っています。公開するのは `dist/index.html` だけ（three.js を含む単一の HTML ファイル）。

```
claude-sketchbook/
  src/
    glyphs/        自分で決めた字（かな、漢字の部品と組み立て、欧文・数字・記号）
    hand.js        字のストローク化（ゆらぎ、右上がり、筆圧、はね・はらい）
    layout.js      文字組み（禁則、上付き、打ち消し線、縦書き）
    marks.js       手描きの線・円・矢印・ハッチング・点描
    media.js       鉛筆・ペン・水彩・消しゴム・こすれ・テープ・しみ・やぶれ
    runtime.js     ページが自分で描かれていく仕組み（時間 → 描画、道具の位置）
    pages/         10ページの中身（p01〜p09、p10は白紙）
    covers.js      表紙・見返し・裏表紙（線の総数）
    three/         机、ランプ、本（ページのめくれ、背、ゴムバンド、ペンループ）、道具
    app.js         シーンと映像モード
    live.js ui.js  操作モード（タップ、スワイプ、最後のページに描く）
    timeline.js    映像の時間割（3/4拍子・76bpm、1ページ8小節）
    audio/         フェルトピアノ、楽譜、残響、効果音、映像用のオフライン書き出し、操作モード用の再生
  build.mjs        src → dist/index.html（esbuild でまとめて1ファイルに）
  render/render.mjs  映像の書き出し（ヘッドレス Chromium でコマ送り → ffmpeg）
  render/web.mjs     原本から配信用の軽い版を作る（2 パスで容量に合わせる）
  tools/           確認用（字の一覧、ページ単体、カメラ、音）
  video/           配信用の MP4（claude-sketchbook-web.mp4、約 20MB）。原本（約 70MB）は入れていない
```

## コマンド

```bash
npm install                 # esbuild と three
node build.mjs              # dist/index.html を作る（--dev で圧縮なし）
node render/render.mjs      # 原本 video/claude-sketchbook.mp4（1080×1080、60fps、約 70MB、約 70 分）
node render/web.mjs         # 配信用 video/claude-sketchbook-web.mp4（原本から 2 パスで 20MiB 以内に）
node render/render.mjs --jobs 2 --from 20 --to 30   # 一部だけ
```

- 映像の書き出しには Playwright の Chromium と、libx264 と AAC の入った ffmpeg が必要です。WebGL は Mesa の llvmpipe（`--use-angle=gl-egl`）で描きます。
- すべての乱数は種から作っているので、何度書き出しても同じ映像になります。コマは 1/60 秒ずつ進め、各コマの状態は時刻だけで決まるので、区間に分けて並列に書き出せます（途中から始めた区間と頭から進めた区間のコマが一致することを確認済み）。
- 鉛筆やペンの影はシャドウマップを使わず、受ける面ごとに「電球（16点の円盤）のうち道具（先細りの棒）に隠れる割合」を計算しています。先端はくっきり、遠い端ほどやわらかく薄くなります。
- `index.html#p1` 〜 `#p10` でそのページまで描かれた状態から開きます。`#p12` は裏表紙。

## ライセンス

Apache License 2.0（[LICENSE](LICENSE)）。Copyright 2026 kzmszk.

`dist/index.html` には three.js（MIT、Copyright 2010-2026 Three.js Authors）が入っています。その表記はファイル末尾に残しています。
