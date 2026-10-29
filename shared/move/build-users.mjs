// Rebuild every city that bundles shared/move, each from its own <city>/tools (their build_web.mjs use paths
// relative to the cwd).  Run after any change under shared/:   node shared/move/build-users.mjs
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const USERS = ['vatican', 'kyoto', 'venice'];   // add a city when it moves onto shared/move

const root = fileURLToPath(new URL('../../', import.meta.url));
let failed = 0;
for (const city of USERS) {
  const cwd = root + city + '/tools';
  console.log(`── ${city}`);
  const r = spawnSync(process.execPath, ['build_web.mjs'], { cwd, stdio: 'inherit' });
  if (r.status !== 0) { failed++; console.error(`${city}: build failed (${r.status ?? r.error})`); }
}
process.exit(failed ? 1 : 0);
