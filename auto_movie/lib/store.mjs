// Where the finished videos live: a Cloudflare R2 bucket that only the demos Worker reads (gallery/worker.js serves /media/* from it
// with byte ranges, so the page can seek). Uploads use the wrangler login of the demos repo: `wrangler r2 object put --remote`.
import path from 'node:path';
import { ROOT, run, readJSON, exists, log } from './util.mjs';

const CONFIG = path.join(ROOT, 'config', 'publish.json');
const DEMOS = path.resolve(ROOT, '..');                                   // owns wrangler.jsonc and node_modules/wrangler
const WRANGLER = path.join(DEMOS, 'node_modules', 'wrangler', 'bin', 'wrangler.js');

/** movies/<id>/video.mp4 | movies/<id>/poster.webp — the only keys the Worker will serve (see gallery/worker.js). */
export const KEY_RE = /^movies\/[A-Za-z0-9][A-Za-z0-9-]{0,63}\/(?:video\.mp4|poster\.webp)$/;
export const mediaPath = (key) => `/media/${key}`;
export const bucket = () => readJSON(CONFIG).bucket;

export async function putObject(key, file, contentType) {
  if (!KEY_RE.test(key)) throw new Error(`bad object key: ${key}`);
  if (!exists(WRANGLER)) throw new Error(`wrangler not found at ${WRANGLER} (run "npm install" in ${DEMOS})`);
  log('store', `r2 put ${bucket()}/${key}`);
  await run(process.execPath, [WRANGLER, 'r2', 'object', 'put', `${bucket()}/${key}`, '--file', file, '--content-type', contentType, '--remote'], {
    cwd: DEMOS, check: true, timeoutMs: 20 * 60 * 1000,
    env: { ...process.env, WRANGLER_SEND_METRICS: 'false', CI: '1' },
  });
}
