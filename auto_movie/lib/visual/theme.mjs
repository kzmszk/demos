// Look and geometry of the video: a sketchbook page. Graphite line, highlighter yellow, red pencil, warm paper.
export const W = 1920, H = 1080;
export const COLORS = { paper: '#fbf7ee', ink: '#3d3d3d', marker: '#fff176', red: '#d64545', inkSoft: 'rgba(61,61,61,.8)', rule: 'rgba(61,61,61,.28)' };

// Layout (canvas pixels)
export const HEADER = { x: 60, y: 42, w: W - 120, h: 44 };
export const HEADLINE = { x: 380, y: 100, w: 1160, h: 76 };
export const STAGE = { x: 380, y: 184, w: 1160, h: 650 };       // illustration / chart area (16:9-ish)
export const CAPTION = { x: 380, y: 852, w: 1160, h: 196 };
export const AVATAR = { w: 330, h: 418, gap: 16, bottom: -26 };  // each side; bottom<0 crops the torso at the frame edge

export function themeCSS() {
  const { paper, ink, marker, red } = COLORS;
  return `
:root{--paper:${paper};--ink:${ink};--marker:${marker};--red:${red}}
*{margin:0;padding:0;box-sizing:border-box}
html,body{margin:0;width:${W}px;height:${H}px;overflow:hidden;background:${paper}}
#root{position:relative;width:100%;height:100%;overflow:hidden;background:${paper};color:${ink};
  font-family:"AM Sans",sans-serif;font-weight:700;font-feature-settings:"palt";
  -webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;line-break:strict;word-break:auto-phrase}
.clip{position:absolute}
.abs{position:absolute}
.paper{position:absolute;inset:0;background:
  radial-gradient(ellipse at 50% 42%,rgba(255,255,255,.55),rgba(255,255,255,0) 62%),
  radial-gradient(ellipse at 50% 50%,rgba(0,0,0,0) 58%,rgba(120,96,60,.10) 100%),${paper}}
.grain{position:absolute;inset:0;background:url(assets/paper.png);background-size:512px 512px;opacity:.5;mix-blend-mode:multiply}

/* header */
.hud{position:absolute;left:${HEADER.x}px;top:${HEADER.y}px;width:${HEADER.w}px;height:${HEADER.h}px;display:flex;align-items:center;justify-content:space-between;
  font-size:22px;letter-spacing:.18em;color:${COLORS.inkSoft}}
.hud b{font-weight:900;color:${ink};letter-spacing:.14em}
.hud .no{margin-left:18px;font-weight:500}
.hud .prog{position:relative;width:340px;height:2px;background:${COLORS.rule}}
.hud .prog i{position:absolute;left:0;top:-1px;height:4px;width:100%;background:${ink};transform-origin:0 50%;transform:scaleX(0)}
.hud .prog s{position:absolute;top:-5px;width:2px;height:12px;background:${COLORS.rule}}
.hud .sc{font-weight:500;margin-right:26px}
.rule{position:absolute;left:${HEADER.x}px;top:${HEADER.y + HEADER.h + 10}px;width:${HEADER.w}px;height:2px;background:${COLORS.rule};transform-origin:0 50%}

/* scenes */
.scene{position:absolute;left:0;top:0;width:${W}px;height:${H}px}
.scene .inner{position:absolute;inset:0}
.headline{position:absolute;left:${HEADLINE.x}px;top:${HEADLINE.y}px;width:${HEADLINE.w}px;height:${HEADLINE.h}px;font-size:56px;font-weight:900;letter-spacing:-.02em;line-height:${HEADLINE.h}px;white-space:nowrap}
.headline span{position:relative;display:inline-block;padding:0 .18em;margin-left:-.18em;isolation:isolate}
.headline span::before{content:"";position:absolute;left:0;right:0;bottom:.06em;height:.42em;background:${marker};z-index:-1;border-radius:2px 6px 3px 7px;transform-origin:0 50%;transform:scaleX(var(--mk,1)) rotate(-.5deg);mix-blend-mode:multiply}
.stage{position:absolute;left:${STAGE.x}px;top:${STAGE.y}px;width:${STAGE.w}px;height:${STAGE.h}px}
.stage svg{position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible}
.ill svg{transform-origin:50% 50%}

/* callouts & stamps */
.callout{position:absolute;font-size:34px;font-weight:900;color:${red};letter-spacing:-.01em;white-space:nowrap;line-height:1.1}
.callout u{text-decoration:none;position:relative;display:inline-block}
.callout u::after{content:"";position:absolute;left:-2%;right:-2%;bottom:-.14em;height:.11em;background:${red};border-radius:4px;opacity:.85;transform-origin:0 50%;transform:scaleX(var(--ul,1)) rotate(-.6deg)}
.stamp{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) rotate(-5deg);font-size:150px;font-weight:900;letter-spacing:-.04em;color:${red};white-space:nowrap;
  border:9px solid ${red};border-radius:14px 22px 12px 24px;padding:.04em .3em .1em;mix-blend-mode:multiply}

/* captions */
.cap{position:absolute;left:${CAPTION.x}px;top:${CAPTION.y}px;width:${CAPTION.w}px;height:${CAPTION.h}px;display:flex;flex-direction:column;align-items:center;justify-content:center}
.cap .who{font-size:24px;font-weight:900;letter-spacing:.18em;margin-bottom:8px;position:relative;padding:0 .3em;isolation:isolate}
.cap .who::after{content:"";position:absolute;left:0;right:0;bottom:1px;height:.42em;border-radius:3px 5px 3px 6px;z-index:-1}
.cap.host .who::after{background:${marker};mix-blend-mode:multiply}
.cap.guest .who::after{background:none;border-bottom:3px solid ${red};height:0;bottom:-2px}
.cap p{font-size:54px;line-height:1.3;font-weight:700;text-align:center;letter-spacing:-.005em;text-wrap:balance;max-width:${CAPTION.w}px}
.cap p mark{background:linear-gradient(transparent 60%,${marker} 60%);color:inherit;padding:0 .04em;mix-blend-mode:multiply}

/* avatars */
.avatar{position:absolute;width:${AVATAR.w}px;height:${AVATAR.h}px;bottom:${AVATAR.bottom}px}
.avatar .halo{position:absolute;left:50%;top:6%;width:${Math.round(AVATAR.w * 0.86)}px;height:${Math.round(AVATAR.w * 0.86)}px;margin-left:${-Math.round(AVATAR.w * 0.43)}px;opacity:0;transform-origin:50% 50%}
.avatar svg{position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible}
.avatar .nm{position:absolute;left:0;right:0;bottom:${-AVATAR.bottom + 14}px;text-align:center;font-size:22px;letter-spacing:.3em;font-weight:900;color:${ink};opacity:.85}
.avatar .nm small{display:block;font-size:14px;letter-spacing:.24em;font-weight:500;opacity:.7;margin-top:2px}

/* intro / outro */
.card{position:absolute;inset:0;background:${paper}}
.card .big{position:absolute;left:150px;top:300px;font-size:214px;font-weight:900;letter-spacing:-.055em;line-height:1.12;white-space:nowrap}
.card .big span{position:relative;display:inline-block;isolation:isolate}
.card .big .mk{position:absolute;left:-.04em;right:-.05em;bottom:.08em;height:.36em;background:${marker};z-index:-1;border-radius:4px 10px 5px 12px;transform-origin:0 50%;mix-blend-mode:multiply;transform:rotate(-.6deg)}
.card .kicker{position:absolute;left:158px;top:236px;font-size:30px;letter-spacing:.32em;font-weight:500;color:${COLORS.inkSoft}}
.card .kicker b{font-weight:900;color:${ink}}
.card .ttl{position:absolute;left:156px;top:590px;font-size:92px;font-weight:900;letter-spacing:-.035em;line-height:1.1;white-space:nowrap}
.card .sub{position:absolute;left:160px;top:730px;font-size:38px;font-weight:500;letter-spacing:.02em;color:${COLORS.inkSoft};white-space:nowrap}
.card .bar{position:absolute;left:156px;top:560px;width:1608px;height:4px;background:${ink};transform-origin:0 50%}
.credits{position:absolute;left:0;right:0;bottom:70px;text-align:center;font-size:24px;font-weight:500;letter-spacing:.1em;color:${COLORS.inkSoft};line-height:1.8}
.credits b{font-weight:900;color:${ink}}
`;
}
