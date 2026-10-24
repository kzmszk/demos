// Loading of the packed data files. Every file is a gzip stream with a 4-byte little-endian JSON header length,
// the JSON header, then raw typed arrays. World axes: the data is x east, y north, z up (metres); three.js is y-up,
// so world = (x, z, -y) throughout the viewer.

export async function fetchBin(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url + ' ' + r.status);
  let buf = await r.arrayBuffer();
  const h = new Uint8Array(buf, 0, 2);
  if (h[0] === 0x1f && h[1] === 0x8b) buf = await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const n = new DataView(buf).getUint32(0, true);
  const head = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, n)));
  return { head, buf, offset: 4 + n };
}

export async function loadTerrain(url) {
  const { head, buf, offset } = await fetchBin(url);
  let o = offset;
  const rings = head.rings.map((r) => {
    const n = r.nx * r.ny, q = new Int16Array(buf.slice(o, o + n * 2)); o += n * 2;
    const h = new Float32Array(n); for (let i = 0; i < n; i++) h[i] = q[i] / 10;
    return { ...r, h };
  });
  return rings;
}

export function terrainSampler(rings) {
  // on the finest ring that contains the point (x east, y north)
  return (x, y) => {
    for (const r of rings) {
      const fx = (x - r.x0) / r.s, fy = (y - r.y0) / r.s;
      if (fx < 0 || fy < 0 || fx >= r.nx - 1 || fy >= r.ny - 1) continue;
      const c = Math.floor(fx), w = Math.floor(fy), u = fx - c, v = fy - w, i = w * r.nx + c, h = r.h;
      // the triangles exactly as terrain.js draws them (each cell split along its (c+1, w)-(c, w+1) diagonal), so feet,
      // cars and rails sit on the drawn ground rather than on a bilinear surface up to ~20 cm off it
      if (u + v <= 1) return h[i] + u * (h[i + 1] - h[i]) + v * (h[i + r.nx] - h[i]);
      const h11 = h[i + r.nx + 1]; return h11 + (1 - u) * (h[i + r.nx] - h11) + (1 - v) * (h[i + 1] - h11);
    }
    return 0;
  };
}

export async function loadRoof(url) {
  const { head, buf, offset } = await fetchBin(url);
  const q = new Int16Array(buf.slice(offset, offset + head.w * head.h * 2));
  const top = (x, y) => {
    // the highest building surface at a point, or -Infinity where there is none
    const c = Math.floor((x - head.x0) / head.res), r = Math.floor((y - head.y0) / head.res);
    if (c < 0 || r < 0 || c >= head.w || r >= head.h) return -Infinity;
    const v = q[r * head.w + c];
    return v === -32768 ? -Infinity : v / 10;
  };
  return { ...head, q, top };
}

// where buildings stand, at 1 m (gen/foot.py): solid(x, y) in data axes
export async function loadFoot(url) {
  const { head, buf, offset } = await fetchBin(url);
  const bits = new Uint8Array(buf, offset, head.stride * head.h);
  const solid = (x, y) => {
    const c = Math.floor((x - head.x0) / head.res), r = Math.floor((y - head.y0) / head.res);
    if (c < 0 || r < 0 || c >= head.w || r >= head.h) return false;
    return (bits[r * head.stride + (c >> 3)] >> (7 - (c & 7))) & 1;
  };
  return { ...head, solid };
}
