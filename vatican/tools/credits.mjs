// credits.mjs — writes public/credits.html (fragment shown in the in-page Credits overlay) from the download
// manifests, listing only what the published page actually uses.
import fs from 'fs';
const A = '/home/kazu/work/vatican-assets/';
const man = (p) => JSON.parse(fs.readFileSync(A + p + '/manifest.json'));
const P = man('paintings'), M = man('maps'), S = man('scans'), PH = man('refs/photos'), VT = man('vault'), TX = JSON.parse(fs.readFileSync(A + 'textures/manifest.json'));
const art = JSON.parse(fs.readFileSync('art.json'));
const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
const byFile = (m) => { const o = {}; for (const v of Object.values(m)) o[v.file] = v; return o; };
const PF = byFile(P), MF = byFile(M), SF = byFile(S), PHF = byFile(PH);
const row = (v, note) => `<li><a href="${esc(v.page)}" target="_blank" rel="noopener">${esc(v.title.replace(/^File:/, ''))}</a> — ${esc(v.artist || 'unknown')}${v.credit && !/own work/i.test(v.credit) ? ' (' + esc(v.credit) + ')' : ''}. <b>${esc(v.license)}</b>${note ? ' · ' + note : ''}</li>`;
const used = new Set();
const paintings = [], maps = [];
for (const [k, a] of Object.entries(art)) {
  if (k.startsWith('_') || !a.src || a.src.startsWith('proc:') || a.src === 'keep' || a.src.startsWith('comp:')) continue;
  if (a.src.startsWith('maps:')) { const v = MF[a.src.slice(5)]; if (v && !used.has(v.file)) { used.add(v.file); maps.push(row(v)); } continue; }
  const v = PF[a.src]; if (v && !used.has(v.file)) { used.add(v.file); paintings.push(row(v)); }
}
// images used inside composed textures
const comps = ['Raffaello_La_Poesia_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', 'Raffaello_La_Giustizia_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg',
  'Raffaello_La_Filosofia_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', 'Volta_della_stanza_della_segnatura_04_teologia_2_.jpg',
  'Raffaello_Apollo_e_Marsia_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', 'Raffaello_Giudizio_di_Salomone_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg',
  'Raffaello_Peccato_originale_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', 'Noè_esce_dall_arca_volta_della_Stanza_di_Eliodoro_Musei_Vaticani_-FG.jpg',
  'Il_sacrificio_di_Isacco_volta_della_Stanza_di_Eliodoro_Musei_Vaticani_-FG.jpg', 'Stanza_di_eliodoro_volta_03_roveto_ardente.jpg',
  'Hendrick_van_den_Broeck_-_The_resurrection_of_Christ.jpg', 'Michelangelo_-_Sistine_Chapel_-_Lunette_Eleazar_and_Mathan.png', 'Michelangelo_lunetta_Jacob_-_Joseph_01.jpg'];
for (const f of comps) { const v = PF[f]; if (v && !used.has(f)) { used.add(f); paintings.push(row(v, 'in a composed texture')); } }
const dome = PHF['2025-03-10_St._Peter_s_Basilica_Inside.jpg'];
const vault = Object.values(VT).filter((v) => art.maps_vault.bays.some((b) => v.file.endsWith(`-FG${b}.jpg`))).sort((a, b) => a.file.localeCompare(b.file)).map((v) => row(v, 'cropped into the vault texture'));
const scansUsed = ['Michelangelo_Buonarroti_Maria_med', 'Apollo_Belvedere', 'Ubekendt_Laokoon', 'Scan_the_World_-_Belvedere_Torso', 'Ubekendt_Stående_nøgen_ung_mand', 'Michelangelo_Buonarroti_Den_genopstandne',
  'Ubekendt_Johannes_Døberen', 'Ubekendt_Ecclesia_sancta', 'Ubekendt_Frans_af_Assisi', 'Ubekendt_Niobide_Chiaramonti', 'Ubekendt_Stående_kvinde', 'Ubekendt_Stående_muse_Polyhymnia'];
const scans = Object.values(S).filter((v) => scansUsed.some((p) => v.file.startsWith(p))).map((v) => row(v, 'decimated'));
const tex = Object.entries(TX).filter(([id]) => ['large_sandstone_blocks_01', 'marble_01', 'white_plaster_rough_01', 'cobblestone_square', 'clay_roof_tiles_02', 'castle_brick_02_red', 'forest_leaves_02', 'gravel_floor'].includes(id))
  .map(([id, v]) => `<li><a href="${v.url}" target="_blank" rel="noopener">${id}</a> — ${esc(v.authors.join(', '))}, Poly Haven. <b>CC0</b></li>`);
const html = `
<h2>Credits &amp; sources ／ 出典</h2>
<p>An interpretive 3D reconstruction made for this gallery from public data, measured drawings and photographs — not an official or survey model. Architecture, lighting and sound were generated procedurally (Blender + three.js); artworks are shown with the images listed below. Some sculptures are stand-ins taken from the cast collection where no free scan of the original exists.<br>
公開データ・実測図・写真から推定再構成した3D空間です（公式の測量モデルではありません）。建築・光・音は手続き的に生成し、作品は以下の画像・3Dデータで再現しています。自由に使える3Dスキャンのない彫刻の一部は、別作品の石膏像スキャンで代用しています。</p>
<h3>Paintings, frescoes and tapestries (Wikimedia Commons)</h3><ul>${paintings.join('')}</ul>
<h3>Gallery of Maps (Wikimedia Commons)</h3><ul>${maps.join('')}</ul>
<h3>Vault of the Gallery of Maps (Wikimedia Commons)</h3><ul>${vault.join('')}</ul>
<h3>Dome mosaics</h3><ul>${dome ? row(dome, 'cropped and recomposed into the dome texture') : ''}</ul>
<h3>Sculpture scans (Wikimedia Commons; Statens Museum for Kunst cast collection, Scan the World)</h3><ul>${scans.join('')}</ul>
<h3>Map data</h3><ul><li>Buildings, trees, green areas and water: © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>, <b>ODbL 1.0</b>.</li></ul>
<h3>Material textures</h3><ul>${tex.join('')}</ul>
<h3>Measured drawings used as reference (not redistributed)</h3><ul><li>Carlo Fontana, <i>Templum Vaticanum et ipsius origo</i> (Rome, 1694), plates on Wikimedia Commons (public domain).</li></ul>
<h3>Software</h3><ul><li><a href="https://threejs.org" target="_blank" rel="noopener">three.js</a> (MIT) · <a href="https://github.com/zeux/meshoptimizer" target="_blank" rel="noopener">meshoptimizer</a> (MIT) · Blender / Cycles (GPL; used to build and light the scene).</li>
<li>Piano and water synthesis from <a href="../aloft/">ALOFT</a> in this gallery.</li></ul>
<p>Images under CC BY / CC BY-SA licences remain under those licences, including the textures derived from them in this page.</p>`;
fs.writeFileSync('../public/credits.html', html);
console.log('credits:', paintings.length, 'paintings,', maps.length, 'maps,', vault.length, 'vault photos,', scans.length, 'scans,', tex.length, 'textures');
