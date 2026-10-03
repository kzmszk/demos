// Material table shared by the packer: linear albedo, roughness, metal flag, detail texture id.
// Texture ids index the detail-texture array in the viewer (0 = none).
export const TEX = { none: 0, travertine: 1, marble: 2, plaster: 3, cobble: 4, tile: 5, lead: 6, brick: 7, granite: 8, grass: 9, gravel: 10, bronze: 11, facade: 12 };
const M = {
  travertine: [[0.50, 0.44, 0.33], 0.75, 0, 'travertine'], travertine_dark: [[0.36, 0.31, 0.23], 0.8, 0, 'travertine'],
  travertine_light: [[0.58, 0.53, 0.43], 0.75, 0, 'travertine'], stucco: [[0.70, 0.62, 0.48], 0.85, 0, 'plaster'],
  plaster_ochre: [[0.62, 0.45, 0.25], 0.9, 0, 'plaster'], plaster_red: [[0.48, 0.24, 0.14], 0.9, 0, 'plaster'],
  plaster_yellow: [[0.70, 0.55, 0.30], 0.9, 0, 'plaster'], plaster_white: [[0.75, 0.72, 0.65], 0.9, 0, 'plaster'],
  facade_ochre: [[0.60, 0.42, 0.24], 0.9, 0, 'facade'], facade_red: [[0.50, 0.26, 0.16], 0.9, 0, 'facade'], facade_yellow: [[0.68, 0.53, 0.30], 0.9, 0, 'facade'], facade_white: [[0.70, 0.66, 0.58], 0.9, 0, 'facade'], facade_trav: [[0.55, 0.50, 0.40], 0.85, 0, 'facade'],
  brick: [[0.42, 0.22, 0.13], 0.9, 0, 'brick'], lead: [[0.30, 0.31, 0.32], 0.55, 0, 'lead'], lead_dome: [[0.30, 0.33, 0.36], 0.5, 0, 'lead'], lead_rib: [[0.46, 0.47, 0.47], 0.55, 0, 'lead'],
  roof_tile: [[0.50, 0.24, 0.13], 0.85, 0, 'tile'], roof_flat: [[0.40, 0.36, 0.32], 0.9, 0, 'gravel'],
  marble_white: [[0.80, 0.78, 0.74], 0.25, 0, 'marble'], marble_grey: [[0.50, 0.50, 0.50], 0.3, 0, 'marble'], marble_int: [[0.42, 0.30, 0.26], 0.25, 0, 'marble'], marble_dark: [[0.22, 0.12, 0.10], 0.22, 0, 'marble'], marble_pil: [[0.58, 0.55, 0.52], 0.28, 0, 'marble'], stucco_white: [[0.66, 0.62, 0.54], 0.8, 0, 'plaster'], gold_dull: [[0.45, 0.33, 0.13], 0.45, 0, 'none'], gloria: [[1.0, 0.85, 0.45], 0.9, 0, 'none'], mosaic_blue: [[0.06, 0.08, 0.16], 0.5, 0, 'none'],
  bronze: [[0.16, 0.11, 0.06], 0.45, 0, 'bronze'], gold: [[0.62, 0.45, 0.16], 0.35, 0, 'none'], glass: [[0.05, 0.06, 0.07], 0.08, 0, 'none'],
  granite: [[0.35, 0.32, 0.30], 0.6, 0, 'granite'], sampietrini: [[0.28, 0.27, 0.26], 0.8, 0, 'cobble'], asphalt: [[0.10, 0.10, 0.10], 0.9, 0, 'gravel'],
  grass: [[0.12, 0.20, 0.06], 1.0, 0, 'grass'], water_fall: [[0.55, 0.6, 0.62], 0.3, 0, 'none'], water: [[0.02, 0.04, 0.05], 0.05, 0, 'none'], foliage: [[0.07, 0.12, 0.04], 0.9, 0, 'grass'], foliage_dark: [[0.04, 0.08, 0.03], 0.9, 0, 'grass'], foliage_light: [[0.09, 0.15, 0.05], 0.9, 0, 'grass'], bark: [[0.16, 0.11, 0.08], 0.95, 0, 'none'], bark_light: [[0.32, 0.29, 0.22], 0.95, 0, 'none'], ground: [[0.30, 0.27, 0.22], 1.0, 0, 'gravel'], lawn: [[0.10, 0.17, 0.05], 1.0, 0, 'grass'],
  gravel: [[0.45, 0.42, 0.36], 1.0, 0, 'gravel'], iron: [[0.05, 0.05, 0.05], 0.5, 0, 'none'], wood: [[0.25, 0.14, 0.07], 0.8, 0, 'none'],
  white: [[0.8, 0.8, 0.8], 0.9, 0, 'none'], statue: [[0.56, 0.53, 0.47], 0.6, 0, 'marble'], statue_marble: [[0.78, 0.76, 0.72], 0.35, 0, 'marble'], obelisk: [[0.42, 0.30, 0.25], 0.45, 0, 'granite'], porphyry: [[0.25, 0.07, 0.07], 0.25, 0, 'granite'], gilt_bronze: [[0.62, 0.45, 0.16], 0.35, 0, 'bronze'], bronze_green: [[0.12, 0.16, 0.12], 0.5, 0, 'bronze'], stucco_ochre: [[0.62, 0.45, 0.26], 0.9, 0, 'plaster'], velarium: [[0.92, 0.9, 0.85], 0.9, 0, 'none'], terracotta: [[0.5, 0.22, 0.12], 0.85, 0, 'none'], glass_pane: [[0.02, 0.025, 0.03], 0.05, 0, 'none'], glass_dome: [[0.55, 0.62, 0.66], 0.2, 0, 'none'], momo_wall: [[0.62, 0.58, 0.5], 0.8, 0, 'plaster'], marble_grey2: [[0.5,0.5,0.5],0.3,0,'marble'],
};
export function matInfo(name) {
  if (name.startsWith('art:')) return { albedo: [1, 1, 1], rough: 0.88, metal: 0, tex: 0 };
  const base = name.split(':')[0];
  const m = M[name] || M[base] || [[0.6, 0.6, 0.6], 0.85, 0, 'none'];
  return { albedo: m[0], rough: m[1], metal: m[2], tex: TEX[m[3]] ?? 0 };
}
// which draw class a material belongs to: 'base' (uber material), or its own (paintings, water)
export function drawClass(name) {
  if (name.startsWith('art:')) return name;
  if (name === 'water') return 'water';
  if (name === 'water_fall') return 'water_fall';
  if (name === 'gloria') return 'gloria';
  if (name === 'glass_pane') return 'glass_pane';
  return 'base';
}
export function albedoTable() { const o = {}; for (const k in M) o[k] = M[k][0]; return o; }
