# Sagrada Família — editable reconstruction source

2026年10月1日の姿を目指して制作した、サグラダ・ファミリアの独立した3D再構成です。**工事状況の最新確認資料は2026年9月22日**です。完成予定を完成実績として扱わず、栄光のファサードと被昇天礼拝堂は未完成、イエス塔は外装完成・内部工事中として扱います。測量モデルや全周3Dスキャンではありません。

[公開済みウォークスルー](https://demos.kazumasa.workers.dev/sagrada-familia/) · [資料基準](docs/CURRENT_STATE.json) · [推定と制約](docs/MODEL_LIMITS.md) · [素材ライセンス一覧](docs/ASSET_LICENSE_NOTICES.md)

このフォルダにはBlenderの生成コード、編集用の窓輪郭・彫刻レリーフデータ、素材、Godotの歩行／飛行コード、Webのローダーとビルドツールを保存しています。**クローン直後は生成済みモデルを含みません。** 下記の手順で編集可能な `.blend` と実行用GLBを作り、必要に応じてWeb版を生成します。

## 構成

| パス | 内容 |
| --- | --- |
| `src/` | 建築・柱・天井・塔・各ファサード・照明・マテリアル・GLB生成 |
| `assets/textures/` | 石PBR、実写真の窓素材、手編集の開口輪郭・彫刻マスク・推定奥行き |
| `assets/reference/` | 素材準備処理が読む、CC条件と作者を確認した原写真16点のみ |
| `runtime/` | ネイティブGodotプロジェクト、衝突と歩行／飛行、UIフォント |
| `web/` | 単一スレッドGodot WebGL2、20 MiB単位の分割配布、ローカルサーバー |
| `docs/` | 工事状況・写真照合・近似・出典・素材の公開／除外台帳 |
| `tools/validate_source.py` | Blenderを起動しない依存ファイル・構文・任意SHA検証 |

## Blender原本を再生成する

Linux、Python 3.11以降、**Blender 5.2.1**（公式配布に含まれるPython/NumPy）を使用します。ソフトウェアや追加サービスは自動インストールしません。素材は同梱済みなので、最初のモデル生成にPillow/SciPyの追加インストールは不要です。

```bash
cd sagrada-familia
python3 tools/validate_source.py --strict
export BLENDER_BIN=/path/to/blender-5.2.1/blender
./REBUILD_SCENE.sh
```

出力は `build/Sagrada_Familia_2026.blend`、`build/sagrada_familia.glb`、`build/colliders.json`、`build/runtime_lighting.json` です。Blenderの編集可能な個別オブジェクトを保存した後、実時間用に空間／素材単位で結合したGLBを別に出力します。静止画レンダーは自動実行しません。`./REBUILD_SCENE.sh --skip-export` ならGLB出力を省略できます。

既定は `SAGRADA_STONE_PROFILE=web_v11`、`SAGRADA_STONE_FINISHES=on`。`BLENDER_THREADS` は既定8です。造形コードやJSON、画像を編集した後はSHAが変わるため、`--strict`を付けずに入力と構文を検証できます。公開用の素材台帳は変更に合わせて更新してください。

石素材も再生成する場合だけ、任意のPython仮想環境に `requirements-tools.txt` の依存を用意し、以下の順に実行します。

```bash
mkdir -p logs docs screenshots
python3 src/materials.py --textures-only
python3 src/prepare_stone_pbr_web_v11.py
python3 src/stone_finishes.py --prepare
python3 src/prepare_nativity_part_variation.py
```

写真窓の準備スクリプト、`assets/textures/exterior_sculpture/grade_nativity_render.py` とその入力も保存しています。ただし窓の手編集輪郭、彫刻のマスク・奥行き設定は**編集ソースそのもの**です。原写真1枚から全形状を自動復元できるという意味ではありません。通常の再生成は同梱済みの編集データを使います。

## 歩行／飛行とWeb版

モデル生成後、Godot **4.7.2** を指定します。

```bash
export GODOT_BIN=/path/to/Godot_v4.7.2-stable_linux.x86_64
./START_WALKTHROUGH.sh

# 同じGodotリリースの単一スレッドWebテンプレートを指定
export GODOT_WEB_TEMPLATE_DIR=/path/to/godot-4.7.2-web-templates
./web/build_web.sh
python3 web/tools/verify_static.py
python3 web/open_local.py
```

テンプレートは `web_nothreads_debug.zip` と `web_nothreads_release.zip` が必要です。WASD移動、マウスで視線、Fで歩行／飛行、E/Qで上昇／下降、Escでメニュー。ローカルサーバーはループバックのみで起動します。[Web構築・フォント・起動の詳細](web/BUILDING.md)を参照してください。

再生成した配布物には、新しくブラウザのロード、入力、床への復帰、衝突、Esc、再起動の確認が必要です。過去の検証結果を新しいビルドの実施結果として流用しないでください。公開済みV12は約325 MBの初回ダウンロード、PC・WebGL2向けです。

## 大容量原本・保存対象・再現の範囲

既存の編集可能なV12原本はABC4090上に保存しています。

```text
/home/kazu/work/codex/2026-10-01/task-6/sagrada_familia_2026/build/Sagrada_Familia_2026.blend
167,304,659 bytes
SHA-256: a0c38f6ee5770d2bebfa93b089c5bd27e3a9006e6e6bbd23dd55e4228fd1a5f9
```

原本は[GitHubの通常ファイル上限100 MiB](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)を超えるため、このリポジトリには含めません。既存リポジトリにLFS方針はなく、今回LFS導入・容量購入・課金設定変更は行っていません。アカウントのLFS残量は未確認です。GLB・PCK・WASM・Web配布物・キャッシュ・ログ・認証設定もGit対象外です。

ここでの「再生成可能」は、保存したコードと素材から編集可能モデルを作り直せる構成を指します。Blenderファイルのバイト単位一致、過去の全作業履歴、レンダーマシン差による完全な見た目一致は保証しません。原本を直接開きたい場合は上記ホストのファイルを使用してください。

このソース整理時点ではBlenderが別作業で使用されているため、Blender/Godot起動・GPU処理・再レンダーは行っていません。依存と素材SHA、Python/JSON/Bash/JavaScriptの静的検証を実施した範囲です。[ソース版の検証記録](docs/SOURCE_RELEASE.json)に実施範囲を記録しています。

## 素材と出典

同梱素材は154ファイル、約225 MB。公式の参照専用写真・冊子・完成予想図、未採用の候補や取得HTMLなど131ファイルは除外しました。各パスの採否、作者、CC条件、改変内容、SHA、欠落の影響は [ASSET_PUBLICATION.json](docs/ASSET_PUBLICATION.json) にあります。写真の著作権条件と、写されたガラス・彫刻そのものの権利は区別しています。

石材は独自の手続き生成です。写真とその派生物には各素材のCC BY／CC BY-SA条件、フォントにはSIL OFL、Godotと同梱通知には各ライセンスが適用されます。このフォルダ全体に一律の新しいオープンソースライセンスを付与していません。公式公認作品ではありません。

## DEMOSとの関係

このブランチは制作ソースの保存用です。ギャラリーが自動検出するトップレベル `demo.json` を置かず、ルートの配備設定も変更していません。既存の公開作品や他のデモをこの追加だけで再構築・配備することはありません。Web配布物は `web/site_bundle/` に生成され、将来の明示的なギャラリー統合で利用できます。生成配布物と素材の出典ページは一緒に扱ってください。
