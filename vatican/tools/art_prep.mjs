// art_prep.mjs — web copies of every art key (public/art/<key>.jpg) + mean colour (art/index.json).
// Procedural textures are drawn as SVG and rasterised with sharp.
import sharp from 'sharp'; import fs from 'fs';
const P = '/home/kazu/work/vatican-assets/paintings/';
const OUT = '../public/art/';
const ART = JSON.parse(fs.readFileSync('art.json'));
const only = process.argv.slice(2);
const index = fs.existsSync(OUT + 'index.json') ? JSON.parse(fs.readFileSync(OUT + 'index.json')) : {};

const PROC = {
  drapery(S) {   // painted silver curtains with gold brocade, fringe and folds (one tile = 1/3 bay)
    let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><defs>
      <linearGradient id="f" x1="0" x2="1"><stop offset="0" stop-color="#6e6a62"/><stop offset=".25" stop-color="#aaa497"/><stop offset=".5" stop-color="#8a8478"/><stop offset=".75" stop-color="#b3ad9f"/><stop offset="1" stop-color="#6e6a62"/></linearGradient>
      <pattern id="b" width="${S / 8}" height="${S / 8}" patternUnits="userSpaceOnUse"><circle cx="${S / 16}" cy="${S / 16}" r="${S / 40}" fill="none" stroke="#b8923e" stroke-width="${S / 200}" opacity=".7"/><path d="M0 ${S / 16} H${S / 8} M${S / 16} 0 V${S / 8}" stroke="#b8923e" stroke-width="${S / 400}" opacity=".5"/></pattern></defs>`;
    for (let i = 0; i < 6; i++) s += `<rect x="${i * S / 6}" y="${S * 0.08}" width="${S / 6}" height="${S * 0.84}" fill="url(#f)"/>`;
    s += `<rect y="${S * 0.08}" width="${S}" height="${S * 0.84}" fill="url(#b)"/>`;
    s += `<rect width="${S}" height="${S * 0.08}" fill="#8a6d3b"/><rect y="${S * 0.06}" width="${S}" height="${S * 0.02}" fill="#d8b766"/>`;
    for (let i = 0; i < 48; i++) s += `<rect x="${i * S / 48}" y="${S * 0.92}" width="${S / 96}" height="${S * 0.07}" fill="#c9a24e"/>`;
    s += `<rect y="${S * 0.985}" width="${S}" height="${S * 0.015}" fill="#5d4a2a"/></svg>`;
    return s;
  },
  band(S) {
    let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S / 4}"><rect width="${S}" height="${S / 4}" fill="#9a7f52"/>`;
    for (let i = 0; i < 8; i++) s += `<ellipse cx="${(i + 0.5) * S / 8}" cy="${S / 8}" rx="${S / 22}" ry="${S / 14}" fill="#d9c08a" stroke="#5c4526" stroke-width="3"/>`;
    s += `<rect width="${S}" height="${S / 40}" fill="#4b3a20"/><rect y="${S / 4 - S / 40}" width="${S}" height="${S / 40}" fill="#4b3a20"/></svg>`;
    return s;
  },
  pilaster(S) {
    let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S / 4}" height="${S}"><rect width="${S / 4}" height="${S}" fill="#c9b48a"/><rect x="${S / 40}" y="${S / 40}" width="${S / 4 - S / 20}" height="${S - S / 20}" fill="#b49a67" stroke="#6b5532" stroke-width="3"/>`;
    for (let i = 0; i < 7; i++) s += `<path d="M${S / 8} ${S * (0.08 + i * 0.13)} c ${S / 12} ${S / 30} ${S / 12} ${S / 15} 0 ${S / 10} c ${-S / 12} ${-S / 30} ${-S / 12} ${-S / 15} 0 ${-S / 10}" fill="#8a3b2a" opacity=".55"/>`;
    return s + '</svg>';
  },
  upper(S) {     // window-tier wall: painted pilasters + two pope niches per bay (window cut in geometry)
    let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#b8a888"/>`;
    for (const cx of [0.17, 0.83]) {
      const x = cx * S, w = S * 0.14;
      s += `<rect x="${x - w / 2 - 6}" y="${S * 0.22}" width="${w + 12}" height="${S * 0.5}" fill="#8f7a58"/>`;
      s += `<path d="M${x - w / 2} ${S * 0.7} V${S * 0.3} a${w / 2} ${w / 2} 0 0 1 ${w} 0 V${S * 0.7} Z" fill="#5a5048"/>`;
      s += `<path d="M${x - w / 3} ${S * 0.7} V${S * 0.42} q${w / 3} -${w * 0.35} ${w * 2 / 3} 0 V${S * 0.7} Z" fill="#8c4a38"/>`;
      s += `<circle cx="${x}" cy="${S * 0.36}" r="${w * 0.12}" fill="#d8b89a"/><path d="M${x - w * 0.14} ${S * 0.345} h${w * 0.28} l-${w * 0.14} -${w * 0.22} z" fill="#f2efe6"/>`;
    }
    for (const x of [0.02, 0.98]) s += `<rect x="${x * S - S * 0.02}" y="0" width="${S * 0.04}" height="${S}" fill="#a68d5d"/>`;
    s += `<rect y="${S * 0.78}" width="${S}" height="${S * 0.025}" fill="#7a6440"/>`;
    return s + '</svg>';
  },
  cosmati(S) {   // opus alexandrinum: rotae of porphyry and serpentine in guilloche bands
    let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#cfc8b8"/>`;
    const c = S / 2, R = S * 0.36;
    for (let k = 0; k < 5; k++) s += `<circle cx="${c}" cy="${c}" r="${R - k * R * 0.17}" fill="${['#6a2d27', '#cfc8b8', '#33503c', '#cfc8b8', '#6a2d27'][k]}" stroke="#2b2b2b" stroke-width="${S / 300}"/>`;
    for (let i = 0; i < 18; i++) { const a = i * Math.PI / 9; s += `<circle cx="${c + Math.cos(a) * R * 0.5}" cy="${c + Math.sin(a) * R * 0.5}" r="${S / 90}" fill="#2b2b2b" opacity=".6"/>`; }
    for (const [x, y] of [[0, 0], [S, 0], [0, S], [S, S]]) s += `<circle cx="${x}" cy="${y}" r="${S * 0.12}" fill="#2e5a3e" stroke="#e6e1d6" stroke-width="${S / 80}"/>`;
    for (let i = 0; i < 24; i++) { const a = i * Math.PI / 12; s += `<rect x="${c + Math.cos(a) * R * 1.12 - S / 70}" y="${c + Math.sin(a) * R * 1.12 - S / 70}" width="${S / 35}" height="${S / 35}" fill="${i % 2 ? '#7a2a25' : '#2b2b2b'}" transform="rotate(45 ${c + Math.cos(a) * R * 1.12} ${c + Math.sin(a) * R * 1.12})"/>`; }
    s += `<rect width="${S}" height="${S}" fill="none" stroke="#2b2b2b" stroke-width="${S / 60}"/>`;
    for (let i = 0; i < 32; i++) s += `<rect x="${i * S / 32}" y="${S * 0.005}" width="${S / 64}" height="${S / 64}" fill="#7a2a25"/><rect x="${i * S / 32}" y="${S * 0.98}" width="${S / 64}" height="${S / 64}" fill="#2e5a3e"/>`;
    return s + '</svg>';
  },
};

const roman = (txt, W, H, fs, fill = '#e8c46a', bg = '#1f2b4a', ls = 0.12) => `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><rect width="${W}" height="${H}" fill="${bg}"/>` +
  `<rect y="0" width="${W}" height="${H * 0.08}" fill="#c9a24e"/><rect y="${H * 0.92}" width="${W}" height="${H * 0.08}" fill="#c9a24e"/>` +
  `<text x="${W / 2}" y="${H * 0.5 + fs * 0.36}" text-anchor="middle" font-family="Nimbus Roman" font-size="${fs}" letter-spacing="${fs * ls}" fill="${fill}" textLength="${W * 0.98}" lengthAdjust="spacingAndGlyphs">${txt}</text></svg>`;
Object.assign(PROC, {
  vault_incendio(S) {
    let b = `<rect width="${S}" height="${S}" fill="#24345e"/>${goldDots(S, S, 3000, 5)}<path d="M0 0 L${S} ${S} M${S} 0 L0 ${S}" stroke="#d8b766" stroke-width="${S / 50}"/>`;
    for (const [x, y] of [[0.5, 0.2], [0.5, 0.8], [0.2, 0.5], [0.8, 0.5]]) b += `<circle cx="${x * S}" cy="${y * S}" r="${S * 0.13}" fill="#e7d3a0" stroke="#d8b766" stroke-width="${S / 60}"/><circle cx="${x * S}" cy="${y * S}" r="${S * 0.07}" fill="#b58a3c"/>`;
    return b.startsWith('<svg') ? b : `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}">${b}</svg>`;
  },
  vault_costantino(S) {
    let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#c7b48a"/>`;
    b += `<rect x="${S * 0.2}" y="${S * 0.25}" width="${S * 0.6}" height="${S * 0.5}" fill="#6f87a8" stroke="#d8b766" stroke-width="${S / 40}"/>`;
    b += `<rect x="${S * 0.45}" y="${S * 0.38}" width="${S * 0.1}" height="${S * 0.24}" fill="#e8dcc0"/><rect x="${S * 0.43}" y="${S * 0.4}" width="${S * 0.14}" height="${S * 0.04}" fill="#e8dcc0"/>`;
    for (let i = 0; i < 12; i++) b += `<rect x="${S * (0.02 + i * 0.08)}" y="${S * 0.05}" width="${S * 0.06}" height="${S * 0.12}" fill="#9a7f52" stroke="#d8b766" stroke-width="3"/><rect x="${S * (0.02 + i * 0.08)}" y="${S * 0.83}" width="${S * 0.06}" height="${S * 0.12}" fill="#9a7f52" stroke="#d8b766" stroke-width="3"/>`;
    return b + '</svg>';
  },
  pieta_back(S) {   // gilded mosaic apse behind the Pietà with a dark cross and two angels' haloes
    let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#5a3e2e"/>`;
    b += `<path d="M${S * 0.12} ${S} V${S * 0.42} a${S * 0.38} ${S * 0.38} 0 0 1 ${S * 0.76} 0 V${S}Z" fill="#b8913c"/>`;
    for (let i = 0; i < 900; i++) { const x = S * 0.12 + ((i * 97) % 100) / 100 * S * 0.76, y = S * 0.08 + ((i * 61) % 100) / 100 * S * 0.9; b += `<rect x="${x}" y="${y}" width="${S / 160}" height="${S / 160}" fill="#f2d68a" opacity=".5"/>`; }
    b += `<rect x="${S * 0.485}" y="${S * 0.14}" width="${S * 0.03}" height="${S * 0.4}" fill="#3a2a1c"/><rect x="${S * 0.4}" y="${S * 0.22}" width="${S * 0.2}" height="${S * 0.03}" fill="#3a2a1c"/>`;
    b += `<path d="M${S * 0.12} ${S * 0.42} a${S * 0.38} ${S * 0.38} 0 0 1 ${S * 0.76} 0" fill="none" stroke="#e8cf8a" stroke-width="${S * 0.02}"/>`;
    b += `<rect y="${S * 0.62}" width="${S}" height="${S * 0.38}" fill="#6b4a38"/>`;
    return b + '</svg>';
  },
  stanza_floor(S) {
    let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#c9bfae"/>`;
    b += `<rect x="${S * 0.03}" y="${S * 0.03}" width="${S * 0.94}" height="${S * 0.94}" fill="#e2dccf" stroke="#6e3b30" stroke-width="${S / 40}"/>`;
    b += `<circle cx="${S / 2}" cy="${S / 2}" r="${S * 0.3}" fill="#5a6f55"/><circle cx="${S / 2}" cy="${S / 2}" r="${S * 0.22}" fill="#e2dccf"/><circle cx="${S / 2}" cy="${S / 2}" r="${S * 0.14}" fill="#6e3b30"/>`;
    return b + '</svg>';
  },
  stanza_dado_win(S) { return dado(S, true); }, stanza_dado_door(S) { return dado(S, false); },
  costantino_wall(S) {
    let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#b49a6e"/>`;
    b += `<rect x="${S * 0.04}" y="0" width="${S * 0.1}" height="${S}" fill="#cdb98c"/><rect x="${S * 0.86}" y="0" width="${S * 0.1}" height="${S}" fill="#cdb98c"/>`;
    b += `<path d="M${S * 0.3} ${S * 0.9} V${S * 0.35} a${S * 0.2} ${S * 0.2} 0 0 1 ${S * 0.4} 0 V${S * 0.9}Z" fill="#8a7a5e"/>`;
    b += `<rect y="${S * 0.85}" width="${S}" height="${S * 0.15}" fill="#7a6648"/>`;
    return b + '</svg>';
  },
  maps_end(S) {
    let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#e3d9bf"/>`;
    b += `<path d="M${S * 0.36} ${S} V${S * 0.62} a${S * 0.14} ${S * 0.14} 0 0 1 ${S * 0.28} 0 V${S}Z" fill="#6b5a40"/><path d="M${S * 0.38} ${S} V${S * 0.63} a${S * 0.12} ${S * 0.12} 0 0 1 ${S * 0.24} 0 V${S}Z" fill="#3a2e22"/>`;
    b += `<rect x="${S * 0.3}" y="${S * 0.1}" width="${S * 0.4}" height="${S * 0.3}" fill="#c9a24e"/><rect x="${S * 0.33}" y="${S * 0.13}" width="${S * 0.34}" height="${S * 0.24}" fill="#7d9bb5"/>`;
    b += `<rect y="${S * 0.68}" width="${S * 0.3}" height="${S * 0.04}" fill="#c9a24e"/><rect x="${S * 0.7}" y="${S * 0.68}" width="${S * 0.3}" height="${S * 0.04}" fill="#c9a24e"/>`;
    return b + '</svg>';
  },
  maps_floor(S) {
    let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#b2a690"/>`;
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) b += `<rect x="${i * S / 4 + 4}" y="${j * S / 4 + 4}" width="${S / 4 - 8}" height="${S / 4 - 8}" fill="${(i + j) % 2 ? '#cfc3ab' : '#a4927a'}"/>`;
    return b + '</svg>';
  },
  maps_wall(S) {
    let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#e3d9bf"/>`;
    b += `<rect x="0" y="0" width="${S * 0.06}" height="${S}" fill="#c9a24e"/><rect x="${S * 0.94}" y="0" width="${S * 0.06}" height="${S}" fill="#c9a24e"/>`;
    b += `<rect y="${S * 0.86}" width="${S}" height="${S * 0.14}" fill="#8f7f66"/><rect y="0" width="${S}" height="${S * 0.05}" fill="#c9a24e"/>`;
    return b + '</svg>';
  },
  rotonda_dome(S) {
    let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#d9d0bc"/>`;
    for (let j = 0; j < 5; j++) { const h = S / 5, y = S - (j + 1) * h, w = S * (0.82 - j * 0.1); b += `<rect x="${(S - w) / 2}" y="${y + h * 0.1}" width="${w}" height="${h * 0.8}" fill="#b9ad94"/><rect x="${(S - w * 0.7) / 2}" y="${y + h * 0.22}" width="${w * 0.7}" height="${h * 0.56}" fill="#e6dfcf"/><circle cx="${S / 2}" cy="${y + h / 2}" r="${h * 0.12}" fill="#c9a24e"/>`; }
    return b + '</svg>';
  },
  otricoli_floor(S) {
    const c = S / 2; let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#d8d0c0"/>`;
    b += `<circle cx="${c}" cy="${c}" r="${S * 0.49}" fill="#2b2b2b"/><circle cx="${c}" cy="${c}" r="${S * 0.47}" fill="#e6dfcf"/>`;
    for (let k = 0; k < 16; k++) { const a = k * Math.PI / 8; b += `<ellipse cx="${c + Math.cos(a) * S * 0.36}" cy="${c + Math.sin(a) * S * 0.36}" rx="${S * 0.05}" ry="${S * 0.035}" transform="rotate(${a * 180 / Math.PI} ${c + Math.cos(a) * S * 0.36} ${c + Math.sin(a) * S * 0.36})" fill="#3d3a36"/>`; }
    b += `<circle cx="${c}" cy="${c}" r="${S * 0.22}" fill="#b28a4a"/><circle cx="${c}" cy="${c}" r="${S * 0.12}" fill="#e2c9a0"/>`;
    return b + '</svg>';
  },
  muse_wall(S) { return `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#a8574a"/><rect y="${S * 0.85}" width="${S}" height="${S * 0.15}" fill="#5e4a3e"/><rect x="${S * 0.02}" y="${S * 0.02}" width="${S * 0.96}" height="${S * 0.8}" fill="none" stroke="#e2d2b0" stroke-width="${S / 60}"/></svg>`; },
  pina_floor(S) { let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#6e4a2e"/>`; for (let i = 0; i < 8; i++) b += `<rect x="${i * S / 8}" y="0" width="${S / 8 - 3}" height="${S}" fill="${i % 2 ? '#7d5634' : '#684528'}"/>`; return b + '</svg>'; },
  pina_wall(S) { return `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#5b2d2a"/><rect y="${S * 0.9}" width="${S}" height="${S * 0.1}" fill="#3a2a22"/></svg>`; },
  momo_rail(S) {
    let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S / 4}"><rect width="${S}" height="${S / 4}" fill="none"/><rect width="${S}" height="${S / 4}" fill="#2f2416" opacity="0.0"/>`;
    b += `<rect x="0" y="0" width="${S}" height="${S * 0.02}" fill="#5c4524"/><rect x="0" y="${S * 0.23}" width="${S}" height="${S * 0.02}" fill="#5c4524"/>`;
    for (let i = 0; i < 4; i++) b += `<circle cx="${(i + 0.5) * S / 4}" cy="${S / 8}" r="${S * 0.08}" fill="none" stroke="#6b5129" stroke-width="${S * 0.012}"/><path d="M${i * S / 4} ${S * 0.02} L${(i + 0.5) * S / 4} ${S / 8} L${i * S / 4} ${S * 0.23}" stroke="#6b5129" stroke-width="${S * 0.01}" fill="none"/>`;
    return b + '</svg>';
  },
  sp_ring: (S) => roman('TV ES PETRVS · ET SVPER HANC PETRAM AEDIFICABO ECCLESIAM MEAM · ET TIBI DABO CLAVES REGNI CAELORVM ·', S, S / 32, S / 32 * 0.62),
  sp_oculus: (S) => roman('S·PETRI·GLORIAE·SIXTVS·PP·V·A·MDXC·PONTIF·V· ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦', S, S / 32, S / 32 * 0.5),
  sp_frieze: (S) => roman('HINC VNA FIDES MVNDO REFVLGET · HINC SACERDOTII VNITAS EXORITVR ·', S, S / 16, S / 16 * 0.55),
  sp_floor(S) {
    let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#c9c1b3"/>`;
    const c = S / 2;
    s += `<rect x="${S * 0.02}" y="${S * 0.02}" width="${S * 0.96}" height="${S * 0.96}" fill="none" stroke="#4f4a44" stroke-width="${S * 0.025}"/>`;
    s += `<rect x="${S * 0.07}" y="${S * 0.07}" width="${S * 0.86}" height="${S * 0.86}" fill="#a39a8a"/>`;
    s += `<rect x="${S * 0.12}" y="${S * 0.12}" width="${S * 0.76}" height="${S * 0.76}" fill="#d6cfc2"/>`;
    s += `<circle cx="${c}" cy="${c}" r="${S * 0.24}" fill="#5c3a32"/><circle cx="${c}" cy="${c}" r="${S * 0.2}" fill="#cfc6b6"/><circle cx="${c}" cy="${c}" r="${S * 0.12}" fill="#7f7466"/>`;
    for (const [x, y] of [[0.12, 0.12], [0.88, 0.12], [0.12, 0.88], [0.88, 0.88]]) s += `<rect x="${x * S - S * 0.05}" y="${y * S - S * 0.05}" width="${S * 0.1}" height="${S * 0.1}" fill="#5c3a32" transform="rotate(45 ${x * S} ${y * S})"/>`;
    return s + '</svg>';
  },
  sp_pendentive(S) {
    const c = S / 2; let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#b98a3a"/>`;
    for (let i = 0; i < 70; i++) { const x = (i * 97) % S, y = (i * 61) % S; s += `<circle cx="${x}" cy="${y}" r="${S / 160}" fill="#f2d88a" opacity=".7"/>`; }
    s += `<circle cx="${c}" cy="${c}" r="${S * 0.3}" fill="#e7cf86"/><circle cx="${c}" cy="${c}" r="${S * 0.27}" fill="#2a3a63"/>`;
    for (let i = 0; i < 24; i++) { const a = i * Math.PI / 12; s += `<line x1="${c}" y1="${c}" x2="${c + Math.cos(a) * S * 0.26}" y2="${c + Math.sin(a) * S * 0.26}" stroke="#c9a24e" stroke-width="${S / 120}" opacity=".55"/>`; }
    s += `<circle cx="${c}" cy="${c}" r="${S * 0.11}" fill="#e8c46a"/><path d="M${c - S * 0.07} ${c + S * 0.2} q${S * 0.07} -${S * 0.12} ${S * 0.14} 0" fill="#d9d1bf"/>`;
    return s + '</svg>';
  },
  sp_vault(S) {     // nave coffers: large octagonal coffers with rosettes alternating with small squares (one 4x4 m tile)
    let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#cdbf9e"/>`;
    const h = S / 2;
    for (const [x, y] of [[0, 0], [h, h]]) {
      s += `<rect x="${x + S * 0.03}" y="${y + S * 0.03}" width="${h - S * 0.06}" height="${h - S * 0.06}" fill="#a87c26"/>`;
      s += `<rect x="${x + S * 0.06}" y="${y + S * 0.06}" width="${h - S * 0.12}" height="${h - S * 0.12}" fill="#ddd2b6"/>`;
      const c = [x + h / 2, y + h / 2], r = h * 0.3; let p = '';
      for (let i = 0; i < 8; i++) { const a = Math.PI / 8 + i * Math.PI / 4; p += `${c[0] + r * Math.cos(a)},${c[1] + r * Math.sin(a)} `; }
      s += `<polygon points="${p}" fill="#c9a24e"/><circle cx="${c[0]}" cy="${c[1]}" r="${h * 0.16}" fill="#d8b766"/><circle cx="${c[0]}" cy="${c[1]}" r="${h * 0.08}" fill="#9a7426"/>`;
    }
    for (const [x, y] of [[h, 0], [0, h]]) {
      s += `<rect x="${x + S * 0.05}" y="${y + S * 0.12}" width="${h - S * 0.1}" height="${h - S * 0.24}" fill="#c9a24e"/><rect x="${x + S * 0.08}" y="${y + S * 0.15}" width="${h - S * 0.16}" height="${h - S * 0.3}" fill="#f2ead6"/>`;
      s += `<circle cx="${x + h / 2}" cy="${y + h / 2}" r="${h * 0.09}" fill="#c9a24e"/>`;
    }
    return s + '</svg>';
  },
  sp_coffers: (S) => coffers(S, 6, 5), sp_coffers_small: (S) => coffers(S, 8, 4),
  sp_lantern(S) {
    const c = S / 2; let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><defs><radialGradient id="g"><stop offset="0" stop-color="#fff2c8"/><stop offset=".55" stop-color="#e2b45a"/><stop offset="1" stop-color="#7a5420"/></radialGradient></defs><rect width="${S}" height="${S}" fill="url(#g)"/>`;
    s += `<ellipse cx="${c}" cy="${c * 0.95}" rx="${S * 0.16}" ry="${S * 0.2}" fill="#d8d0c8"/><circle cx="${c}" cy="${c * 0.72}" r="${S * 0.07}" fill="#d8b89a"/><path d="M${c - S * 0.3} ${c} q${S * 0.3} -${S * 0.15} ${S * 0.6} 0" fill="none" stroke="#b9372c" stroke-width="${S * 0.05}"/>`;
    return s + '</svg>';
  },
});
const svg = (w, h, body) => Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">${body}</svg>`);
const goldDots = (W, H, n, seed = 1) => { let o = ''; let x = seed * 9301; for (let i = 0; i < n; i++) { x = (x * 9301 + 49297) % 233280; const px = x / 233280 * W; x = (x * 9301 + 49297) % 233280; const py = x / 233280 * H; o += `<rect x="${px}" y="${py}" width="${W / 300}" height="${W / 300}" fill="#f6dc8c" opacity=".55"/>`; } return o; };
async function cropImg(file, rel, w, h, opts = {}) {     // rel = [x0,y0,x1,y1] in 0..1 of the source
  const im = sharp(P + file, { limitInputPixels: false }); const md = await im.metadata();
  const l = Math.round(rel[0] * md.width), t = Math.round(rel[1] * md.height), ww = Math.round((rel[2] - rel[0]) * md.width), hh = Math.round((rel[3] - rel[1]) * md.height);
  let x = sharp(P + file, { limitInputPixels: false }).extract({ left: l, top: t, width: ww, height: hh }).resize(w, h, { fit: 'cover' });
  if (opts.flop) x = x.flop();
  if (opts.round) x = x.composite([{ input: svg(w, h, `<circle cx="${w / 2}" cy="${h / 2}" r="${w / 2}" fill="#fff"/>`), blend: 'dest-in' }]);
  return x.png().toBuffer();
}
const frameSvg = (w, h, round, col = '#e2c27a', t = 10) => svg(w, h, round ? `<circle cx="${w / 2}" cy="${h / 2}" r="${w / 2 - t / 2}" fill="none" stroke="${col}" stroke-width="${t}"/><circle cx="${w / 2}" cy="${h / 2}" r="${w / 2 - t * 1.6}" fill="none" stroke="#7a5420" stroke-width="${t / 3}"/>`
  : `<rect x="${t / 2}" y="${t / 2}" width="${w - t}" height="${h - t}" fill="none" stroke="${col}" stroke-width="${t}"/><rect x="${t * 1.6}" y="${t * 1.6}" width="${w - t * 3.2}" height="${h - t * 3.2}" fill="none" stroke="#7a5420" stroke-width="${t / 3}"/>`);
const COMP = {
  async vault_segnatura(S) {
    const bg = svg(S, S, `<rect width="${S}" height="${S}" fill="#9c7a3a"/>${goldDots(S, S, 5000)}` +
      `<path d="M0 0 L${S} ${S} M${S} 0 L0 ${S}" stroke="#e8cf8a" stroke-width="${S / 60}"/><path d="M0 0 L${S} ${S} M${S} 0 L0 ${S}" stroke="#5a3e18" stroke-width="${S / 200}"/>` +
      `<circle cx="${S / 2}" cy="${S / 2}" r="${S * 0.11}" fill="#23324f" stroke="#e8cf8a" stroke-width="${S / 80}"/>`);
    const R = Math.round(S * 0.26), comps = [{ input: bg, left: 0, top: 0 }];
    const rounds = [['Raffaello_La_Poesia_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', S / 2, S * 0.2],
      ['Raffaello_La_Giustizia_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', S / 2, S * 0.8],
      ['Raffaello_La_Filosofia_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', S * 0.8, S / 2],
      ['Volta_della_stanza_della_segnatura_04_teologia_2_.jpg', S * 0.2, S / 2]];
    for (const [f, cx, cy] of rounds) {
      const md = await sharp(P + f).metadata(); const sq = Math.min(md.width, md.height) / Math.max(md.width, md.height);
      const rel = md.width > md.height ? [(1 - sq) / 2 + 0.03, 0.03, (1 + sq) / 2 - 0.03, 0.97] : [0.03, (1 - md.width / md.height) / 2, 0.97, (1 + md.width / md.height) / 2];
      comps.push({ input: await cropImg(f, rel, R, R, { round: true }), left: Math.round(cx - R / 2), top: Math.round(cy - R / 2) });
      comps.push({ input: frameSvg(R, R, true, '#e8cf8a', S / 90), left: Math.round(cx - R / 2), top: Math.round(cy - R / 2) });
    }
    const rects = [['Raffaello_Apollo_e_Marsia_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', 0.8, 0.2],
      ['Raffaello_Giudizio_di_Salomone_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', 0.8, 0.8],
      ['Raffaello_Peccato_originale_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', 0.2, 0.2],
      ['Raffaello_Giudizio_di_Salomone_1508-11_Volta_della_Stanza_della_Segnatura_Musei_Vaticani_-FG.jpg', 0.2, 0.8]];
    const rw = Math.round(S * 0.2), rh = Math.round(S * 0.17);
    for (const [f, cx, cy] of rects) {
      comps.push({ input: await cropImg(f, [0.12, 0.1, 0.88, 0.9], rw, rh, { flop: cy > 0.5 && cx < 0.5 }), left: Math.round(cx * S - rw / 2), top: Math.round(cy * S - rh / 2) });
      comps.push({ input: frameSvg(rw, rh, false, '#e8cf8a', S / 120), left: Math.round(cx * S - rw / 2), top: Math.round(cy * S - rh / 2) });
    }
    return sharp({ create: { width: S, height: S, channels: 3, background: '#9c7a3a' } }).composite(comps).jpeg({ quality: 86 }).toBuffer();
  },
  async vault_eliodoro(S) {
    const bg = svg(S, S, `<rect width="${S}" height="${S}" fill="#2f3a56"/>${goldDots(S, S, 2500, 3)}<path d="M0 0 L${S} ${S} M${S} 0 L0 ${S}" stroke="#d8b766" stroke-width="${S / 50}"/>`);
    const comps = [{ input: bg, left: 0, top: 0 }];
    const scenes = [['Noè_esce_dall_arca_volta_della_Stanza_di_Eliodoro_Musei_Vaticani_-FG.jpg', 0.5, 0.17, false], ['Il_sacrificio_di_Isacco_volta_della_Stanza_di_Eliodoro_Musei_Vaticani_-FG.jpg', 0.5, 0.83, false],
      ['Stanza_di_eliodoro_volta_03_roveto_ardente.jpg', 0.17, 0.5, false], ['Noè_esce_dall_arca_volta_della_Stanza_di_Eliodoro_Musei_Vaticani_-FG.jpg', 0.83, 0.5, true]];
    for (const [f, cx, cy, fl] of scenes) {
      const horiz = cx === 0.5; const w = Math.round(S * (horiz ? 0.5 : 0.3)), h = Math.round(S * (horiz ? 0.3 : 0.5));
      comps.push({ input: await cropImg(f, [0.06, 0.06, 0.94, 0.94], w, h, { flop: fl }), left: Math.round(cx * S - w / 2), top: Math.round(cy * S - h / 2) });
      comps.push({ input: frameSvg(w, h, false, '#d8b766', S / 110), left: Math.round(cx * S - w / 2), top: Math.round(cy * S - h / 2) });
    }
    return sharp({ create: { width: S, height: S, channels: 3, background: '#2f3a56' } }).composite(comps).jpeg({ quality: 86 }).toBuffer();
  },
  async maps_vault(S) {     // Gallery of Maps vault: 8 real bays (CC0 photos taken straight up, cropped wall to wall) in a 2x4 atlas
    const D = '/home/kazu/work/vatican-assets/vault/', T = S / 2;
    const comps = [];
    for (const [i, id] of ART.maps_vault.bays.entries()) {
      const f = D + `Storie_edificanti_e_miracolose_sul_soffitto_della_Galleria_delle_Carte_Geografiche_1581-83_-FG${id}.jpg`;
      const md = await sharp(f).metadata();
      const [x0, x1] = [0.15, 0.85];
      const buf = await sharp(f).extract({ left: Math.round(md.width * x0), top: 0, width: Math.round(md.width * (x1 - x0)), height: md.height })
        .resize(T, T, { fit: 'fill' }).modulate({ brightness: 0.86, saturation: 0.95 }).toBuffer();
      comps.push({ input: buf, left: (i % 2) * T, top: (3 - (i >> 1)) * T });
    }
    return sharp({ create: { width: S, height: S * 2, channels: 3, background: '#d8c9a0' } }).composite(comps).jpeg({ quality: 88 }).toBuffer();
  },
};
function dado(S, win) {
  let b = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S / 2}"><rect width="${S}" height="${S / 2}" fill="#8c7652"/>`;
  for (let i = 0; i < 4; i++) b += `<rect x="${i * S / 4 + S * 0.02}" y="${S * 0.06}" width="${S / 4 - S * 0.04}" height="${S * 0.36}" fill="#a68f66" stroke="#5c4a30" stroke-width="4"/><ellipse cx="${(i + 0.5) * S / 4}" cy="${S * 0.24}" rx="${S * 0.07}" ry="${S * 0.1}" fill="#7a6545"/>`;
  b += `<rect y="0" width="${S}" height="${S * 0.03}" fill="#c9b17a"/>`;
  if (win) b += `<rect x="${S * 0.34}" y="0" width="${S * 0.32}" height="${S / 2}" fill="#4a3220"/><rect x="${S * 0.36}" y="${S * 0.02}" width="${S * 0.13}" height="${S * 0.46}" fill="#5e3f26"/><rect x="${S * 0.51}" y="${S * 0.02}" width="${S * 0.13}" height="${S * 0.46}" fill="#5e3f26"/>`;
  return b + '</svg>';
}
function coffers(S, nu, nv) {
  let s = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}"><rect width="${S}" height="${S}" fill="#d9c9a0"/>`;
  const cw = S / nu, ch = S / nv;
  for (let i = 0; i < nu; i++) for (let j = 0; j < nv; j++) {
    const x = i * cw, y = j * ch;
    s += `<rect x="${x + cw * 0.08}" y="${y + ch * 0.08}" width="${cw * 0.84}" height="${ch * 0.84}" fill="#c9a24e"/>`;
    s += `<rect x="${x + cw * 0.16}" y="${y + ch * 0.16}" width="${cw * 0.68}" height="${ch * 0.68}" fill="#efe6d0"/>`;
    s += `<circle cx="${x + cw / 2}" cy="${y + ch / 2}" r="${Math.min(cw, ch) * 0.16}" fill="#c9a24e"/>`;
  }
  return s + '</svg>';
}

async function entrance(S) {     // entrance wall composite 12.2 x 20.7 m: drapery, two frescoes, door, lunettes
  const W = S * 12.2 / 20.7 | 0, H = S, m = H / 20.7;
  const base = sharp({ create: { width: W, height: H, channels: 3, background: '#cdbb95' } });
  const comps = [];
  const drap = await sharp(Buffer.from(PROC.drapery(512))).resize(W, Math.round(5.55 * m), { fit: 'fill' }).toBuffer();
  comps.push({ input: drap, left: 0, top: H - Math.round(5.55 * m) });
  const panelH = Math.round(3.5 * m), panelW = Math.round(5.4 * m), py = H - Math.round(9.35 * m);
  comps.push({ input: await sharp(P + 'Hendrick_van_den_Broeck_-_The_resurrection_of_Christ.jpg').resize(panelW, panelH, { fit: 'fill' }).toBuffer(), left: Math.round(0.3 * m), top: py });
  comps.push({ input: await sharp(P + 'Signorelli_Luca_-_Moses_s_Testament_and_Death_-_1481-82.jpg').modulate({ saturation: 0.8 }).resize(panelW, panelH, { fit: 'fill' }).toBuffer(), left: W - panelW - Math.round(0.3 * m), top: py });
  const door = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${Math.round(2.6 * m)}" height="${Math.round(5.2 * m)}"><rect width="100%" height="100%" fill="#3a2a1c"/><rect x="6%" y="5%" width="88%" height="95%" fill="#5a4129" stroke="#2b1d10" stroke-width="8"/></svg>`);
  comps.push({ input: door, left: Math.round(W / 2 - 1.3 * m), top: H - Math.round(5.2 * m) });
  const lw = Math.round(5.6 * m), lh = Math.round(3.8 * m), ly = H - Math.round(16.9 * m);
  comps.push({ input: await sharp(P + 'Michelangelo_-_Sistine_Chapel_-_Lunette_Eleazar_and_Mathan.png').resize(lw, lh, { fit: 'fill' }).toBuffer(), left: Math.round(0.2 * m), top: ly });
  comps.push({ input: await sharp(P + 'Michelangelo_lunetta_Jacob_-_Joseph_01.jpg').resize(lw, lh, { fit: 'fill' }).toBuffer(), left: W - lw - Math.round(0.2 * m), top: ly });
  return base.composite(comps).jpeg({ quality: 86 }).toBuffer();
}

for (const [key, a] of Object.entries(ART)) {
  if (key.startsWith('_') || (only.length && !only.includes(key))) continue;
  let buf;
  if (a.src === 'keep') { buf = fs.readFileSync('ref/sp_dome_src.jpg'); }
  else if (a.src === 'proc:entrance') buf = await entrance(a.max);
  else if (a.src.startsWith('proc:')) { const im = sharp(Buffer.from(PROC[a.src.slice(5)](a.max))); buf = await (a.alpha ? im.png() : im.jpeg({ quality: 88 })).toBuffer(); }
  else if (a.src.startsWith('comp:')) buf = await COMP[a.src.slice(5)](a.max);
  else if (a.src.startsWith('maps:')) buf = await sharp('/home/kazu/work/vatican-assets/maps/' + a.src.slice(5), { limitInputPixels: false }).resize(a.max, a.max, { fit: 'inside' }).jpeg({ quality: 85 }).toBuffer();
  else buf = await sharp(P + a.src, { limitInputPixels: false }).resize(a.max, a.max, { fit: 'inside', withoutEnlargement: true }).jpeg({ quality: 86 }).toBuffer();
  const webp = await sharp(buf).webp({ quality: a.max >= 3000 ? 84 : 82, alphaQuality: 90 }).toBuffer();
  fs.writeFileSync(OUT + key + '.webp', webp);
  const st = await sharp(buf).stats();
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const meta = await sharp(buf).metadata();
  index[key] = { w: meta.width, h: meta.height, mean: st.channels.slice(0, 3).map((ch) => +lin(ch.mean).toFixed(4)), title: a.title, artist: a.artist, date: a.date, src: a.src };
  console.log(key, meta.width + 'x' + meta.height, (buf.length / 1024 | 0) + 'KB');
}
fs.writeFileSync(OUT + 'index.json', JSON.stringify(index, null, 1));
