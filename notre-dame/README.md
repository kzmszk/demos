# NOTRE-DAME — Web Walk & Fly

2019年4月の火災前のノートルダム大聖堂を、写真・図面・公表寸法から推定再構成した3D空間です。身廊、側廊、礼拝堂、バラ窓、ヴォールト、外観を歩行と自由飛行で見学できます。公式デジタルツインや測量モデルではありません。

公開URL: https://demos.kazumasa.workers.dev/notre-dame/

PCのWebGL 2対応ブラウザ向けです。初回読み込みは約258MBで、展開後にはさらにメモリが必要です。WebAssembly、Web Crypto、Streams、gzip対応のDecompressionStreamも使用します。モバイル・Safari・Firefoxは未検証です。

## 構成と公開範囲

- `public/`：配信用の入口HTMLと、版を固定した `assets/<build hash>/`。Web実行データ、Credits、素材・Godot・フォントのライセンス文書を含みます。
- `demo.json`：ギャラリー情報。`serve: "public"` により、このフォルダだけを `site/notre-dame/` へコピーします。
- `import-web.mjs`：完成済みの `site_bundle/` から、公開に必要なファイルを取り込むスクリプト。
- `SOURCE.json`：取込元、ビルド版、保全情報の記録。配信用フォルダの外に置きます。
- `../gallery/covers/notre-dame/`：Web版の実画面2枚。`01.png` は身廊、`02.png` は北バラ窓です。

編集可能な独立ソースは `/home/kazu/work/codex/2026-10-01/task-5/notre_dame_pre2019/` に保持しています。Blender原本は `/home/kazu/work/codex/2026-10-01/task-5/notre_dame_pre2019/build/Notre_Dame_Pre2019.blend`、Webプロジェクトは同フォルダの `web/godot/` です。Blenderでの形状・素材編集はこの原本から行います。

このリポジトリは公開用配布物と取込手順を保持します。Blender原本、制作素材、ローカル実行環境は `public/` に含めません。編集ソース一式を引き継ぐ場合は、上記の独立ソースとその出典台帳を別途渡してください。

## 操作

| 操作 | キー・UI |
|---|---|
| 移動 | WASD / 矢印 |
| 視線 | マウス。捕捉できない場合は左ドラッグ |
| 高速移動 | Shift |
| 歩行 / 飛行の切替 | F / 画面下のボタン |
| 飛行中の上昇 / 下降 | E・Space / Q・C |
| 停止・メニュー | Esc |
| 6つの見学地点 | 1–6 / 選択欄 |
| 画質・写真 | 画面下の選択欄・写真保存ボタン |

飛行では壁や屋根を通過できます。歩行へ戻すと、有効な床へ着地するか、最後の安全な歩行位置へ戻ります。屋根や椅子は歩行床に含めません。

## 更新

元作品を変更した場合は、独立ソース側でWeb版を書き出してから、静的配布物を生成します。ビルドと取込は同時に実行しないでください。

```bash
cd /home/kazu/work/codex/2026-10-01/task-5/notre_dame_pre2019
./web/build_web.sh
python3 web/tools/package_static.py
```

次にdemosリポジトリのルートで完成したフォルダを取り込み、確認・公開します。ギャラリービルドは全作品の `demo.json` を収集するため、他の未公開作業がある場合は、公開済みのGit状態から専用worktreeを作ってこの作品だけを追加してください。今回の配信用worktreeは `codex/notre-dame-web` ブランチです。

```bash
node notre-dame/import-web.mjs /absolute/path/to/site_bundle
npm run dev
npm run deploy
```

この環境の取込元は `/home/kazu/work/codex/2026-10-01/task-5/notre_dame_pre2019/web/site_bundle/` です。取込後は起動、歩行・飛行、Creditsリンクを確認してください。ファイル分割はホストの単体サイズ上限に合わせたもので、合計ダウンロード量を減らす処理ではありません。`index.html` のダブルクリックでは起動できないため、HTTP(S)で配信します。

表紙は独立ソースの `web/screenshots/web_nave_high_900.png` と `web/screenshots/web_north_rose_flight_900.png` を加工せずコピーしたものです。`shots: []` とし、通常の `npm run shoot` で再撮影しません。差し替える場合も、更新済みWeb版を実際に表示して撮影したPNGを使います。

## 出典・ライセンスと再現の限界

作品内の **Credits & sources** から、全出典台帳、著作者、出典URL、ライセンス、改変内容、用途・限界を確認できます。CC BY / CC BY-SAの写真素材、CC0の石材素材、Godotとフォントの個別ライセンスを保持しています。作品全体に一括のライセンスは設定していません。素材を再配布・改変する場合は、各記録に従ってください。参照専用の写真は実行素材に含めていません。

彫刻の顔・聖書場面、礼拝堂の祭壇・絵画、全窓の図像は完全再現していません。窓の配置や形状には推定があり、光はリアルタイム表示用の近似です。塔内の全階段・登頂経路、屋根裏、地下遺構、周辺市街は対象外です。Web版はGodot Compatibilityで動作するため、ネイティブ版の面光源・体積霧・SSIL・TAAとは表示が異なります。考証と検証条件の詳細は、独立ソースの `docs/ARCHITECTURE.md` と `web/docs/VALIDATION_WEB.md` を参照してください。
