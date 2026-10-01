/* Notre-Dame static package adapter. Godot's generated engine is unchanged. */
(() => {
  'use strict';
  const manifest = window.__ND_STATIC_MANIFEST__;
  if (!manifest || manifest.formatVersion !== 1) {
    throw new Error('The Notre-Dame static package manifest is missing or unsupported.');
  }
  const originalFetch = window.fetch.bind(window);
  const base = new URL('.', document.baseURI);
  const pckURL = new URL(manifest.pck.logicalFile, base).href;
  const wasmURL = new URL(manifest.wasm.logicalFile, base).href;

  function assetURL(name) {
    const resolved = new URL(name, base);
    if (resolved.origin !== base.origin || !resolved.pathname.startsWith(base.pathname)
        || resolved.search || resolved.hash) {
      throw new Error('Static package asset escapes its versioned directory.');
    }
    return resolved.href;
  }

  function aborted(signal) {
    if (signal.aborted) {
      throw signal.reason || new DOMException('The operation was aborted.', 'AbortError');
    }
  }

  async function checkedBytes(file, request) {
    aborted(request.signal);
    const response = await originalFetch(assetURL(file.file), {
      method: 'GET', signal: request.signal, credentials: request.credentials,
      cache: request.cache, mode: 'same-origin', redirect: 'follow'
    });
    if (!response.ok) {
      throw new Error(`Cannot load ${file.file}: HTTP ${response.status}.`);
    }
    const bytes = new Uint8Array(await response.arrayBuffer());
    aborted(request.signal);
    return {bytes, headers: response.headers};
  }

  async function verify(bytes, expected, label) {
    if (bytes.byteLength !== expected.bytes) {
      throw new Error(`${label} has an unexpected size (${bytes.byteLength}, expected ${expected.bytes}).`);
    }
    if (!window.crypto || !window.crypto.subtle) {
      throw new Error('Static package verification requires Web Crypto in an HTTPS context.');
    }
    const digest = await window.crypto.subtle.digest('SHA-256', bytes);
    const actual = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
    if (actual !== expected.sha256) {
      throw new Error(`${label} failed SHA-256 verification. Reload the current package.`);
    }
  }

  function responseHeaders(type, length) {
    return {'Content-Type': type, 'Content-Length': String(length)};
  }

  function packageResponse(request) {
    let next = 0;
    let cancelled = false;
    const localAbort = new AbortController();
    const forwardAbort = () => localAbort.abort(request.signal.reason);
    request.signal.addEventListener('abort', forwardAbort, {once: true});
    const assetRequest = new Request(request, {signal: localAbort.signal});
    const stream = new ReadableStream({
      async pull(controller) {
        try {
          aborted(request.signal);
          if (next >= manifest.pck.chunks.length) {
            request.signal.removeEventListener('abort', forwardAbort);
            controller.close();
            return;
          }
          const chunk = manifest.pck.chunks[next];
          const {bytes} = await checkedBytes(chunk, assetRequest);
          await verify(bytes, chunk, chunk.file);
          if (cancelled) return;
          next += 1;
          controller.enqueue(bytes);
        } catch (error) {
          request.signal.removeEventListener('abort', forwardAbort);
          if (!cancelled) controller.error(error);
        }
      },
      cancel(reason) {
        cancelled = true;
        request.signal.removeEventListener('abort', forwardAbort);
        localAbort.abort(reason);
      }
    }, {highWaterMark: 0});
    return new Response(stream, {status: 200,
      headers: responseHeaders('application/octet-stream', manifest.pck.bytes)});
  }

  async function wasmResponse(request) {
    const {bytes, headers} = await checkedBytes(manifest.wasm.gzip, request);
    const isGzip = bytes[0] === 0x1f && bytes[1] === 0x8b;
    const isWasm = bytes[0] === 0 && bytes[1] === 0x61 && bytes[2] === 0x73 && bytes[3] === 0x6d;
    let stream;
    if (isGzip) {
      await verify(bytes, manifest.wasm.gzip, manifest.wasm.gzip.file);
      if (typeof DecompressionStream === 'undefined') {
        throw new Error('This browser needs DecompressionStream gzip support for the Web engine.');
      }
      stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    } else if (isWasm && /gzip/i.test(headers.get('Content-Encoding') || '')) {
      // A host may apply Content-Encoding to the .gz file. Fetch already decoded it.
      await verify(bytes, manifest.wasm, 'HTTP-decoded WebAssembly');
      stream = new Blob([bytes]).stream();
    } else {
      throw new Error('The static WebAssembly asset is neither gzip nor HTTP-decoded WASM.');
    }
    return new Response(stream, {status: 200,
      headers: responseHeaders('application/wasm', manifest.wasm.bytes)});
  }

  window.fetch = function staticPackageFetch(input, init) {
    let url;
    try {
      url = new URL(input instanceof Request ? input.url : input, document.baseURI).href;
    } catch (_) {
      return originalFetch(input, init);
    }
    const method = String(init && init.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
    if (method !== 'GET' || (url !== pckURL && url !== wasmURL)) {
      return originalFetch(input, init);
    }
    try {
      const request = input instanceof Request ? new Request(input, init) : new Request(url, init);
      aborted(request.signal);
      return url === pckURL ? Promise.resolve(packageResponse(request)) : wasmResponse(request);
    } catch (error) {
      return Promise.reject(error);
    }
  };
})();
