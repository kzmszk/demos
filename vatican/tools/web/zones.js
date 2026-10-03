// Loader for packed zones (tools/pack.mjs): meshopt-compressed streams per chunk.
import * as THREE from 'three';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

export async function loadZone(name, base, getMaterial, onProgress) {
  await MeshoptDecoder.ready;
  const man = await (await fetch(`${base}/${name}.json`)).json();
  const buf = new Uint8Array(man.bytes); let got = 0;
  const PART = 20 * 1024 * 1024;
  await Promise.all(Array.from({ length: man.parts || 1 }, async (_, i) => {
    const res = await fetch(`${base}/${name}.${i}.bin`);
    let w = i * PART;
    if (res.body) {
      const reader = res.body.getReader();
      for (;;) { const { done, value } = await reader.read(); if (done) break; buf.set(value, w); w += value.length; got += value.length; onProgress && onProgress(got / man.bytes); }
    } else { const a = new Uint8Array(await res.arrayBuffer()); buf.set(a, w); got += a.length; onProgress && onProgress(got / man.bytes); }
  }));
  const group = new THREE.Group(); group.name = name;
  for (const ch of man.chunks) {
    const vc = ch.vc;
    const dec = (r, size) => { const t = new Uint8Array(vc * size); MeshoptDecoder.decodeVertexBuffer(t, vc, size, buf.subarray(r[0], r[0] + r[1])); return t; };
    const pos = new Uint16Array(dec(ch.pos, 8).buffer);
    const nrm = new Int8Array(dec(ch.nrm, 4).buffer);
    const irr = dec(ch.irr, 4);
    const col = dec(ch.col, 4);
    const idx = new Uint32Array(ch.ic);
    MeshoptDecoder.decodeIndexBuffer(new Uint8Array(idx.buffer), ch.ic, 4, buf.subarray(ch.idx[0], ch.idx[0] + ch.idx[1]));
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 4, true));   // xyz in [0,1] of the chunk cube
    const na = new THREE.BufferAttribute(nrm, 4, true);
    g.setAttribute('normal', na);   // xyz = normal (w ignored by three's vec3 declaration)
    g.setAttribute('texid', na);    // same buffer; w = detail texture id / 127
    g.setAttribute('irr', new THREE.BufferAttribute(irr, 4, true));        // RGBM (x8)
    g.setAttribute('col', new THREE.BufferAttribute(col, 4, true));
    if (ch.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(dec(ch.uv, 8).buffer), 2));
    g.setIndex(new THREE.BufferAttribute(idx, 1));
    const E = ch.E;
    g.boundingBox = new THREE.Box3(new THREE.Vector3(0, 0, 0), new THREE.Vector3((ch.bmax[0] - ch.bmin[0]) / E, (ch.bmax[1] - ch.bmin[1]) / E, (ch.bmax[2] - ch.bmin[2]) / E));
    g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
    const mesh = new THREE.Mesh(g, getMaterial(ch.cls));
    mesh.position.set(ch.bmin[0], ch.bmin[1], ch.bmin[2]); mesh.scale.setScalar(E); mesh.updateMatrix();
    mesh.castShadow = true; mesh.receiveShadow = true;
    mesh.matrixAutoUpdate = false;
    mesh.userData.cls = ch.cls;
    group.add(mesh);
  }
  return group;
}
