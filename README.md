# DEMOS

ウェブの実験を1本ずつ置いていくリポジトリです。トップフォルダ1つが1作品になり、`gallery/` がそれらをギャラリーにまとめます。ギャラリーは Cloudflare Workers の静的アセットとして公開します。

```
demos/
  raster/  kinetic/ …   作品（1フォルダ＝1作品、demo.json を持つ）
  gallery/
    build.mjs           作品を集めて site/ を作る（ギャラリー、404、各作品の公開ファイル）
    shoot.mjs           ヘッドレス Chrome で表紙のフレームを撮る → gallery/covers/<作品>/
    site.json           サイト名とキャッチ
    src/                ギャラリーの CSS / JS
    covers/             撮影済みの表紙（コミットする）
  site/                 生成物（公開されるのはここだけ。コミットしない）
  wrangler.jsonc        静的アセットのみの Worker 設定
```

## 作品を追加する

1. トップにフォルダを作り、ページを置きます（`index.html` など）。
2. 同じフォルダに `demo.json` を置きます。

```json
{
  "no": "021",
  "title": "作品名",
  "subtitle": { "ja": "日本語の副題", "en": "English subtitle" },
  "summary": { "ja": "1〜2文の紹介", "en": "One or two sentences." },
  "date": "2026-10-01",
  "tags": ["canvas", "audio"],
  "serve": ".",
  "entry": "index.html",
  "shots": [
    { "path": "index.html" },
    { "path": "index.html#dark", "eval": "document.body.click()", "after": 1200 }
  ]
}
```

| 項目 | 意味 |
|---|---|
| `no` | 100本コレクションの番号など。空なら表示しない |
| `serve` | 公開するフォルダ。`.` ならフォルダ全体 |
| `entry` | 公開フォルダ内の入口ファイル |
| `links` | 入口を複数並べたいとき（`[{ "label": "日本語", "href": "move-ja.html" }]`） |
| `prebuild` | ビルド前に作品フォルダ内で実行するコマンド（例：`node build.mjs`） |
| `lang` | doctype のないページを包むときの `lang`（既定 `ja`） |
| `shots` | 表紙のフレーム。`path` を開き、`wait` ms 待つ。`eval` があれば実行して `after` ms 待ってから撮る |
| `gpu` | `true` なら表紙を撮るときにヘッドレス Chrome で実際の GPU を使う（GPU で描く重い作品向け。ソフトウェア描画では遅すぎるため） |

- 公開されないもの：`demo.json`、`prompts/`、`README.md`、ドットファイル。
- 並び順：`date` の新しい順です。
- doctype のないページ：Artifact 用に書いた本文だけのページには、ビルド時に自動で `<!DOCTYPE html>` などの外枠を付けます。
- `shots` がない作品：表紙は作品名の文字組みになります。

## コマンド

```bash
npm install          # 初回のみ（wrangler）
npm run shoot        # 表紙を撮り直す（全作品。特定の作品だけなら npm run shoot -- raster）
npm run dev          # ビルドして http://127.0.0.1:8787 で Workers と同じ環境で確認
npm run deploy       # ビルドして Cloudflare に公開
```

- 初めて公開するときは、先に `npx wrangler login` で Cloudflare にログインしてください。
- 公開先は `https://demos.<アカウントのサブドメイン>.workers.dev` です。名前は `wrangler.jsonc` の `name` で変えられます。
- 独自ドメインを使う場合は、Cloudflare のダッシュボードで Worker に Custom Domain を追加します。

## Worker（`gallery/worker.js`）

ギャラリーの大半は静的アセットですが、`/api/*` と `/media/*` だけは Worker が先に受けます。

| パス | 用途 |
|---|---|
| `POST /api/sketch`、`GET /api/sketch/:id` | スケッチブックの「おためし」。`illustration.svg` のジョブを hermes-llm-jobs に登録し、このPCが描く |
| `POST /api/movie`、`GET /api/movie/:id` | auto_movie の「つくる」。`video.generate` のジョブ（テーマ・2か3分・任意の事実メモ）を登録し、このPCが10〜15分で動画をつくる |
| `GET /media/movies/<id>/video.mp4`・`poster.webp` | できあがった動画とポスター。非公開の R2 バケット `demos-media`（バインディング `MEDIA`）から、バイト範囲つきで返す（シークできる）。それ以外のキーは返さない |

- シークレット（`npx wrangler secret put …`）：`SKETCH_PASSPHRASE`、`LLM_JOBS_API_KEY`（スケッチ用）、`MOVIE_JOBS_API_KEY`（動画用。hermes-llm-jobs の `provision-app.py auto-movie --types video.generate` で発行したアプリ用キー）、任意で `MOVIE_PASSPHRASE`（なければ `SKETCH_PASSPHRASE` を使う）。
- ローカルでは `.dev.vars` に `SKETCH_MOCK=1`・`MOVIE_MOCK=1` を書くと、ジョブサービスの代わりに偽の進行（受付 → 制作中 → 完成）を返します。R2 はローカルの模擬ストレージ（`npx wrangler r2 object put demos-media/movies/<id>/video.mp4 --file … --local`）。
- テスト：`npm test`（Worker の検証・ジョブの登録・結果の見せ方・`/media` の範囲リクエストを、偽のジョブサービスと偽のバケットで確かめる）。
- 動画づくりの全体と、PC 側の仕組みは [auto_movie/README.md](auto_movie/README.md) と hermes-llm-jobs の README にあります。
