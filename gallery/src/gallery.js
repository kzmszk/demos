/* DEMOS — gallery behaviour.
   1. The wordmark is fitted to the full measure.
   2. Covers are storyboards: moving the pointer across a cover scrubs through its frames;
      on touch screens (and while a cover has keyboard focus) the frames play on their own
      while the cover is in view. Frames beyond the first load on first interest. */
(function () {
  'use strict';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const noHover = matchMedia('(hover: none)').matches;

  /* ---------- wordmark ---------- */
  const mark = document.querySelector('.wordmark span');
  function fit() {
    if (!mark) return;
    mark.style.fontSize = '100px';
    const w = mark.getBoundingClientRect().width;
    const avail = mark.parentElement.clientWidth;
    /* at 100px: the left margin pulls in 4.5px, and the last glyph's ink runs 6.8px past the
       box because the negative tracking after it shortens the box */
    if (w > 0) mark.style.fontSize = ((100 * avail) / (w - 4.5 + 6.8)).toFixed(2) + 'px';
  }
  fit();
  let t = 0;
  addEventListener('resize', () => {
    clearTimeout(t);
    t = setTimeout(fit, 80);
  });
  if (document.fonts) document.fonts.ready.then(fit);

  /* ---------- storyboard covers ---------- */
  document.querySelectorAll('.cover[data-frames]').forEach((cover) => {
    let frames;
    try {
      frames = JSON.parse(cover.dataset.frames);
    } catch (e) {
      return;
    }
    if (!frames || frames.length < 2) return;
    const box = cover.querySelector('.frames');
    const segs = Array.from(cover.querySelectorAll('.scrub i'));
    let imgs = null, cur = 0, timer = 0, visible = false, focused = false;

    const load = () => {
      if (imgs) return;
      imgs = [box.querySelector('img')];
      frames.slice(1).forEach((src) => {
        const im = new Image();
        im.alt = '';
        im.decoding = 'async';
        im.src = src;
        box.appendChild(im);
        imgs.push(im);
      });
    };
    const show = (i) => {
      if (i === cur) return;
      load();
      if (cur) imgs[cur].classList.remove('is-on');
      if (i) imgs[i].classList.add('is-on');
      if (segs[cur]) segs[cur].classList.remove('is-on');
      if (segs[i]) segs[i].classList.add('is-on');
      cur = i;
    };
    const play = (on) => {
      clearInterval(timer);
      cover.classList.toggle('is-auto', on);
      if (on && !reduce) {
        load();
        timer = setInterval(() => show((cur + 1) % frames.length), 1500);
      } else if (!on) show(0);
    };

    cover.addEventListener('pointerenter', (e) => {
      if (e.pointerType === 'mouse' || e.pointerType === 'pen') load();
    });
    cover.addEventListener('pointermove', (e) => {
      if (e.pointerType !== 'mouse' && e.pointerType !== 'pen') return;
      const r = cover.getBoundingClientRect();
      cover.classList.add('is-scrubbing');
      show(Math.max(0, Math.min(frames.length - 1, Math.floor(((e.clientX - r.left) / r.width) * frames.length))));
    });
    cover.addEventListener('pointerleave', (e) => {
      if (e.pointerType !== 'mouse' && e.pointerType !== 'pen') return;
      cover.classList.remove('is-scrubbing');
      show(0);
    });
    cover.addEventListener('focus', () => {
      focused = true;
      play(true);
    });
    cover.addEventListener('blur', () => {
      focused = false;
      play(noHover && visible);
    });

    if (noHover && 'IntersectionObserver' in window) {
      new IntersectionObserver(
        (es) =>
          es.forEach((e) => {
            visible = e.isIntersecting;
            if (!focused) play(visible);
          }),
        { threshold: 0.6 }
      ).observe(cover);
    }
  });
})();
