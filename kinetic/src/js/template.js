/* Kinetic Manifesto — the standalone page template. Shared by the in-browser
   "Save HTML" export and by build.mjs, so both produce byte-identical pages.
   DOM-free. */
(function (root) {
  'use strict';
  const K = root.K;
  const T = K.text;
  const esc = K.escapeHTML;
  /* "<" inside inline JSON / JS must not close the script element */
  const LT = '\\' + 'u003c';

  K.template = {
    page(opts) {
      const c = K.normalize(opts.content);
      if (opts.lock) c.options.editable = false;
      const json = JSON.stringify(c, null, 2).replace(/</g, LT);
      const js = String(opts.js || '').replace(/<\/script/gi, '<\\/script');
      const css = String(opts.css || '').replace(/<\/style/gi, '<\\/style');
      const statements = c.scenes.map((s) => `    <li>${esc(T.plain(s))}</li>`).join('\n');
      const P = c.palette;
      return [
        '<!DOCTYPE html>',
        `<html lang="${c.lang}" style="--bg:${P.bg};--fg:${P.fg};--accent:${P.accent}">`,
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        `<title>${esc(c.meta.title)}</title>`,
        `<meta name="description" content="${esc(c.meta.description)}">`,
        `<meta name="theme-color" content="${P.bg}">`,
        `<meta name="generator" content="Kinetic Manifesto ${K.VERSION}">`,
        "<script>document.documentElement.classList.add('k-js')</script>",
        '<style id="k-css">',
        css,
        '</style>',
        '</head>',
        '<body>',
        '<main id="k-root" class="k-fallback">',
        `  <h1>${esc(c.meta.title)}</h1>`,
        c.intro.kicker ? `  <p>${esc(c.intro.kicker)}</p>` : '',
        '  <ol>',
        statements,
        '  </ol>',
        c.finale.text ? `  <p><strong>${esc(c.finale.text)}</strong></p>` : '',
        '</main>',
        '<script type="application/json" id="k-content">',
        json,
        '</script>',
        '<script id="k-js">',
        js,
        '</script>',
        '<script>K.boot()</script>',
        '</body>',
        '</html>',
        '',
      ]
        .filter((l) => l !== '')
        .join('\n') + '\n';
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
