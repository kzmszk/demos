/* Dev preview only (not part of built pages): index.html?c=<name> loads content/<name>.json
   and always allows editing. Drafts are kept per content file. */
(function () {
  'use strict';
  const name = (new URLSearchParams(location.search).get('c') || 'move-ja').replace(/[^\w-]/g, '');
  fetch(`content/${name}.json`, { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
    .catch(() => ({}))
    .then((raw) => K.app.start(raw, { dev: true, key: `${location.pathname}?c=${name}` }));
})();
