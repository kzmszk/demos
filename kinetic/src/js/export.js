/* Kinetic Manifesto — export: rebuild this very page with new content.
   Standalone pages read their own inline <style id="k-css"> and <script id="k-js">;
   the dev page (index.html) fetches the linked source files in order. */
(function (root) {
  'use strict';
  const K = root.K;
  const doc = document;

  K.exporter = {
    sources() {
      const css = doc.getElementById('k-css'), js = doc.getElementById('k-js');
      if (css && js) return Promise.resolve({ css: css.textContent.trim(), js: js.textContent.trim() });
      const links = Array.from(doc.querySelectorAll('link[data-k-src]'), (l) => l.getAttribute('href'));
      const scripts = Array.from(doc.querySelectorAll('script[data-k-src]'), (s) => s.getAttribute('src'));
      const get = (u) =>
        fetch(u, { cache: 'no-cache' }).then((r) => {
          if (!r.ok) throw new Error(u);
          return r.text();
        });
      return Promise.all([Promise.all(links.map(get)), Promise.all(scripts.map(get))]).then(([c, j]) => ({
        css: c.join('\n').trim(),
        js: j.map((t, i) => `/* ---- ${scripts[i]} ---- */\n${t.trim()}`).join('\n'),
      }));
    },
    html(content, opts) {
      return this.sources().then((s) => K.template.page({ content, css: s.css, js: s.js, lock: opts && opts.lock }));
    },
    download(name, text, type) {
      const url = URL.createObjectURL(new Blob([text], { type: type + ';charset=utf-8' }));
      const a = K.h('a', { href: url, download: name, hidden: true });
      doc.body.appendChild(a);
      a.click();
      setTimeout(() => {
        URL.revokeObjectURL(url);
        a.remove();
      }, 1500);
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
