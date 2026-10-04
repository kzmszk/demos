# Runtime / Web の再生成

このディレクトリは制作ソースです。生成済み GLB、PCK、WASM、Web 配布物、Godot のキャッシュは含みません。クローン直後に見学を開始するには、先にプロジェクトのモデル生成手順を実施してください。

必要なソフトウェア:

- Python 3.11 以降。通常のステージング・配布生成・サーバーは標準ライブラリのみを使用します。
- Godot Engine **4.7.2** と、同じリリースの Web エクスポートテンプレート。
- Bash、`timeout`、`grep`、`tail`、`cp` などの通常の Linux コマンド。

モデル生成後、プロジェクト直下の `build/` に以下の3ファイルが必要です。

```
build/sagrada_familia.glb
build/colliders.json
build/runtime_lighting.json
```

## ビルド

以下は `sagrada-familia/` をカレントディレクトリにした例です。Godot とテンプレートの場所は各環境に合わせて指定してください。ビルドスクリプトはソフトウェアのダウンロード、インストール、外部公開を行いません。

```bash
export GODOT_BIN=/path/to/Godot_v4.7.2-stable_linux.x86_64
export GODOT_WEB_TEMPLATE_DIR=/path/to/godot-4.7.2-web-templates
./web/build_web.sh
python3 web/tools/verify_static.py
```

テンプレートディレクトリには `web_nothreads_debug.zip` と `web_nothreads_release.zip` の両方を置いてください。`configure_web_export.py` が追跡対象の `web/godot/export_presets.cfg.in` から、ローカルの絶対パスを含む未追跡の `export_presets.cfg` を生成します。Web は単一スレッド・GL Compatibility / WebGL2、ネイティブは既定で Forward+ を使用します。

`stage_assets.py` が正本の `runtime/project.godot`・`main.tscn`・`scripts/` と生成したモデルを `web/godot/` に配置します。Web 側のこれらの生成コピーを直接編集しないでください。`web/godot/web_shell.html` と `export_presets.cfg.in` は追跡対象のソースです。

通常ビルドは `web/dist/` の生成、クレジットの生成、最大20 MiBに分割した `web/site_bundle/` の生成までを行います。比較検証などで分割配布物の更新を保留する場合:

```bash
SKIP_STATIC_PACKAGE=1 ./web/build_web.sh
# 新しい出典監査を行った場合は、その結果をクレジットへ反映してから配布を作る。
python3 web/tools/build_credits.py
python3 web/tools/package_static.py > web/qa/package_summary.json
python3 web/tools/verify_static.py
```

`verify_static.py` はサイズ・ハッシュ・ステージングの一致を確認します。実ブラウザでの描画や操作の検証は別途必要です。新規ビルドへ過去の `browser_tested` 記録を引き継がないでください。`package_static.py` は `dist/` 内のファイルを収録するため、ここに診断用ファイルや非公開資料を置かないでください。

## 起動

```bash
# 分割配布版。127.0.0.1:8777、起動用端末から切り離したサーバー。
python3 web/open_local.py
# ブラウザを開かずサーバーだけ準備する場合
python3 web/open_local.py --no-browser

# 分割前の dist。127.0.0.1:8776、この端末は開いたままにする。
./web/START_WEB.sh --no-browser
# 分割配布版を foreground で起動する場合
./web/START_WEB.sh --bundle site_bundle --port 8777 --no-browser

# ネイティブ Godot
./runtime/launch.sh
```

起動はローカルのループバックアドレスだけを使用します。常駐ランチャーは同じプロジェクト・配布種別・ポートのサーバーだけを再利用し、別プロセスや別クローンが使うポートを停止しません。OS サービスや自動起動の設定は行いません。

## フォント・ライセンス・出典監査

`runtime/assets/sagrada_familia_ui.woff2`、`web/tools/font_audit.json`、`font_license.txt` は小さな日本語 UI フォントとその検証情報・ライセンスです。フォントのハッシュと現 UI の文字収録が一致すれば、fontTools/Brotli やシステムフォントなしで再利用できます。生成キャッシュを除外しても、この3ファイルは残してください。

UI に未収録の文字を追加した場合だけ、Noto Sans CJK の元フォントとライセンス、Python の `fontTools`・`brotli` が必要です。Linux の既定パス以外を使用する場合は `FONT_SOURCE` と `FONT_LICENSE_SOURCE` を指定できます。既存 Python パッケージへのパスは `FONTTOOLS_PYTHONPATH`、強制再生成は `FONT_REBUILD=1` で指定します。再生成時は同梱フォント・検証情報・ライセンスも更新されるため、差分を確認してください。

Godot の MIT ライセンスと第三者著作権表記は `web/licenses/godot/` から配布へコピーし、クレジットにリンクします。写真素材の帰属はプロジェクトの `docs/` にある素材・出典台帳から生成するため、モデルだけをコピーして台帳を省略しないでください。

`web/tools/audit_sources.py` は任意の追加監査で、Pillow と台帳で参照する写真・派生素材の入力が必要です。基本モデル再生成に不要な原写真を省略した場合、この監査の全項目を再実行できるとは限りません。過去の監査報告はその時点の成果物に対する記録です。

この移植では Python AST と Bash 構文、同梱フォントのハッシュ・文字収録を静的に確認しています。移植先で Blender/Godot/ブラウザを起動した再生成検証は行っていません。
