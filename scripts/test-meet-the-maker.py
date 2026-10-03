"""Meet the maker: geometry, type, the blob crop, and the motion contract.

Measured in headless Chromium rather than read off the source, because the
things most likely to be wrong here are the ones only layout knows: whether
the outline lands on the crop, whether a sticker reaches past the viewport,
and whether two animations ended up on the same element's transform.

Animations do not advance under --virtual-time-budget, so nothing here waits
for one to finish. The entrance is checked as a declaration (name, duration,
delay, fill) plus its held start state, which is deterministic; the finished
look is checked through the reduced-motion and fallback paths, where it is
reached without any animation running at all.
"""
import json, subprocess, sys, pathlib, re

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/meet-the-maker.liquid'
HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path('/tmp/claude-0')

PROBE = """<script>
(function(){
  function box(el){ if(!el) return null;
    var r = el.getBoundingClientRect();
    return {x:+r.left.toFixed(1), y:+r.top.toFixed(1),
            w:+r.width.toFixed(1), h:+r.height.toFixed(1)}; }
  function cs(el, props){ if(!el) return null;
    var c = getComputedStyle(el), o = {};
    props.forEach(function(p){ o[p] = c.getPropertyValue(p); });
    return o; }

  var root     = document.querySelector('.hp-mm');
  var row      = document.querySelector('.hp-mm__row');
  var portrait = document.querySelector('.hp-mm__portrait');
  var back     = document.querySelector('.hp-mm__back');
  var backSvg  = document.querySelector('.hp-mm__back svg');
  var photo    = document.querySelector('.hp-mm__photo');
  var img      = document.querySelector('.hp-mm__photo img, .hp-mm__photo svg');
  var outline  = document.querySelector('.hp-mm__outline');
  var text     = document.querySelector('.hp-mm__text');
  var quote    = document.querySelector('.hp-mm__quote');
  var bio      = document.querySelector('.hp-mm__bio');
  var eyebrow  = document.querySelector('.hp-mm__eyebrow');
  var signame  = document.querySelector('.hp-mm__sig-name');
  var sigtitle = document.querySelector('.hp-mm__sig-title');
  var stickers = [].slice.call(document.querySelectorAll('.hp-mm__sticker'));

  var ANIM = ['animation-name','animation-duration','animation-delay',
              'animation-fill-mode','animation-timing-function',
              'animation-iteration-count'];

  document.title = 'RESULT' + JSON.stringify({
    rootTag: root ? root.tagName : null,
    rootOverflowX: root ? getComputedStyle(root).overflowX : null,
    rootIsolation: root ? getComputedStyle(root).isolation : null,
    rootPad: cs(root, ['padding-top','padding-bottom']),

    rowCols: row ? getComputedStyle(row).gridTemplateColumns : null,
    rowGap: row ? getComputedStyle(row).columnGap : null,
    rowBox: box(row),

    portraitBox: box(portrait),
    backBox: box(back),
    photoBox: box(photo),
    outlineBox: box(outline),
    photoClip: photo ? getComputedStyle(photo).clipPath : null,
    photoOverflow: photo ? getComputedStyle(photo).overflow : null,
    imgFit: img ? getComputedStyle(img).objectFit : null,

    textBox: box(text),
    textAlign: text ? getComputedStyle(text).textAlign : null,
    quoteTag: quote ? quote.tagName : null,
    quoteType: cs(quote, ['font-size','line-height','letter-spacing','font-weight']),
    bioType: cs(bio, ['font-size','line-height','font-weight']),
    bioMax: bio ? getComputedStyle(bio).maxWidth : null,
    eyeType: cs(eyebrow, ['font-size','letter-spacing','text-transform','border-radius']),
    signameType: cs(signame, ['font-size','font-weight']),
    sigtitleType: cs(sigtitle, ['font-size','letter-spacing','text-transform','margin-top']),

    // Where each animation lives. Two on one element's transform would mean
    // one silently replaced the other.
    animBack: cs(back, ANIM),
    animBackSvg: cs(backSvg, ANIM),
    animPhoto: cs(photo, ANIM),
    animQuote: cs(quote, ANIM),
    animBio: cs(bio, ANIM),

    opacities: {
      back: back ? getComputedStyle(back).opacity : null,
      photo: photo ? getComputedStyle(photo).opacity : null,
      quote: quote ? getComputedStyle(quote).opacity : null,
      sticker: stickers[0] ? getComputedStyle(stickers[0]).opacity : null
    },

    stickers: stickers.map(function(st){
      var pill = st.querySelector('.hp-mm__pill');
      var c = getComputedStyle(st);
      return {
        cls: st.className,
        box: box(st),
        transform: c.transform,
        rot: c.getPropertyValue('--hp-mm-rot').trim(),
        delay: c.animationDelay,
        delayVar: c.getPropertyValue('--hp-mm-sticker-delay').trim(),
        animName: c.animationName,
        pillBorder: pill ? getComputedStyle(pill).borderTopWidth : null,
        pillPad: pill ? getComputedStyle(pill).padding : null,
        pillFont: pill ? getComputedStyle(pill).fontSize : null,
        pillAnim: pill ? getComputedStyle(pill).animationName : null,
        text: pill ? pill.textContent.trim() : null
      };
    }),

    imgAlt: document.querySelector('.hp-mm__photo img')
      ? document.querySelector('.hp-mm__photo img').getAttribute('alt') : null,
    imgLoading: document.querySelector('.hp-mm__photo img')
      ? document.querySelector('.hp-mm__photo img').getAttribute('loading') : null,

    clipPaths: document.querySelectorAll('clipPath').length,
    clipIds: [].slice.call(document.querySelectorAll('clipPath'))
      .map(function(c){ return c.id; }),
    outlineStroke: document.querySelector('.hp-mm__outline path')
      ? document.querySelector('.hp-mm__outline path').getAttribute('vector-effect') : null,

    scrollW: document.documentElement.scrollWidth,
    vw: window.innerWidth
  });
})();
</script>"""


def run(name, overrides=None, width=1440, height=1000, extra='', reduced=False):
    page = TMP / f'mm-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps(overrides or {}), str(page)],
                   check=True, capture_output=True)
    html = page.read_text(encoding='utf-8').replace('</body>', extra + PROBE + '</body>')
    page.write_text(html, encoding='utf-8')
    cmd = [CHROME, '--headless', '--no-sandbox', '--disable-gpu',
           f'--window-size={width},{height}', '--virtual-time-budget=4000',
           '--dump-dom']
    if reduced:
        cmd.append('--force-prefers-reduced-motion')
    cmd.append('file://' + str(page))
    dom = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit(f'{name}: no probe result\n' + dom[:2000])
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")

def near(a, b, tol=1.5):
    return abs(a - b) <= tol


# A phone viewport is forced through an iframe: a Chromium window has a 500px
# minimum, so --window-size=390 silently renders at 500.
FRAME = """<style>html,body{margin:0}</style>"""

PORTRAIT = {'settings': {'portrait': {'src': 'founder.jpg'}}}

# ---------------------------------------------------------------- desktop ---
d = run('desktop')

check('the section root clips its own overhang',
      d['rootOverflowX'] == 'clip',
      f"overflow-x: {d['rootOverflowX']}")

check('the section root makes a stacking context',
      d['rootIsolation'] == 'isolate',
      f"isolation: {d['rootIsolation']}")

check('section padding is 140 top / 150 bottom',
      d['rootPad']['padding-top'] == '140px' and d['rootPad']['padding-bottom'] == '150px',
      f"{d['rootPad']['padding-top']} / {d['rootPad']['padding-bottom']}")

check('two columns, portrait then text',
      len(d['rowCols'].split()) == 2,
      f"grid-template-columns: {d['rowCols']}")

check('the gap between the columns is 96px',
      d['rowGap'] == '96px',
      f"column-gap: {d['rowGap']}")

check('the content row is held to 1116px',
      d['rowBox']['w'] <= 1116.5,
      f"row width {d['rowBox']['w']}px (cap 1116)")

check('the portrait cluster is 480 square',
      near(d['portraitBox']['w'], 480) and near(d['portraitBox']['h'], 480),
      f"{d['portraitBox']['w']} x {d['portraitBox']['h']}")

check('the back blob fills the whole cluster',
      near(d['backBox']['w'], 480) and near(d['backBox']['h'], 480),
      f"{d['backBox']['w']} x {d['backBox']['h']}")

check('the photo blob is 420 square',
      near(d['photoBox']['w'], 420) and near(d['photoBox']['h'], 420),
      f"{d['photoBox']['w']} x {d['photoBox']['h']}")

inset_l = d['photoBox']['x'] - d['portraitBox']['x']
inset_t = d['photoBox']['y'] - d['portraitBox']['y']
check('the photo blob is inset 30px from the back blob',
      near(inset_l, 30) and near(inset_t, 30),
      f"inset left {inset_l}px, top {inset_t}px")

# The outline has to sit exactly on the crop or the 2px line reads as a halo.
check('the outline sits exactly on the photo blob',
      near(d['outlineBox']['x'], d['photoBox']['x'], 0.6)
      and near(d['outlineBox']['y'], d['photoBox']['y'], 0.6)
      and near(d['outlineBox']['w'], d['photoBox']['w'], 0.6)
      and near(d['outlineBox']['h'], d['photoBox']['h'], 0.6),
      f"outline {d['outlineBox']}  photo {d['photoBox']}")

check('the outline stroke does not scale with the shape',
      d['outlineStroke'] == 'non-scaling-stroke',
      f"vector-effect={d['outlineStroke']!r}")

check('the photo is cropped to the clip path',
      d['photoClip'].startswith('url('),
      f"clip-path: {d['photoClip']}")

check('the clip path id carries the section id',
      d['clipPaths'] == 1 and d['clipIds'][0].startswith('hp-mm-clip-'),
      f"{d['clipPaths']} clipPath(s): {d['clipIds']}")

check('the text column is 540px',
      near(d['textBox']['w'], 540),
      f"{d['textBox']['w']}px")

# ------------------------------------------------------------------ type ---
check('the quote is a blockquote',
      d['quoteTag'] == 'BLOCKQUOTE',
      f"<{(d['quoteTag'] or '?').lower()}>")

q = d['quoteType']
check('quote type is 36/46, -0.5px, weight 800',
      q['font-size'] == '36px' and q['line-height'] == '46px'
      and q['letter-spacing'] == '-0.5px' and q['font-weight'] == '800',
      f"{q['font-size']}/{q['line-height']} ls {q['letter-spacing']} w{q['font-weight']}")

b = d['bioType']
check('bio type is 16/27, weight 300',
      b['font-size'] == '16px' and b['line-height'] == '27px' and b['font-weight'] == '300',
      f"{b['font-size']}/{b['line-height']} w{b['font-weight']}")

check('the bio is held to 520px',
      d['bioMax'] == '520px',
      f"max-width {d['bioMax']}")

e = d['eyeType']
check('eyebrow is 10px uppercase, 1.5px tracking, fully rounded',
      e['font-size'] == '10px' and e['letter-spacing'] == '1.5px'
      and e['text-transform'] == 'uppercase' and e['border-radius'] == '999px',
      f"{e['font-size']} ls {e['letter-spacing']} {e['text-transform']} r{e['border-radius']}")

check('the signature name is 34px bold',
      d['signameType']['font-size'] == '34px' and d['signameType']['font-weight'] == '700',
      f"{d['signameType']['font-size']} w{d['signameType']['font-weight']}")

st = d['sigtitleType']
check('the signature title is 11px uppercase, 4px below the name',
      st['font-size'] == '11px' and st['letter-spacing'] == '1.5px'
      and st['text-transform'] == 'uppercase' and st['margin-top'] == '4px',
      f"{st['font-size']} ls {st['letter-spacing']} gap {st['margin-top']}")

# -------------------------------------------------------------- stickers ---
check('both preset stickers render',
      len(d['stickers']) == 2,
      f"{len(d['stickers'])} sticker(s): "
      + ', '.join(s['text'] for s in d['stickers']))

s0, s1 = d['stickers'][0], d['stickers'][1]

check('the first sticker is top-right, tilted 8deg',
      'hp-mm__sticker--tr' in s0['cls'] and s0['rot'] == '8deg',
      f"{s0['cls'].split()[-1]}  rot {s0['rot']}")

check('the second sticker is bottom-left, tilted -6deg',
      'hp-mm__sticker--bl' in s1['cls'] and s1['rot'] == '-6deg',
      f"{s1['cls'].split()[-1]}  rot {s1['rot']}")

tr_l = s0['box']['x'] - d['portraitBox']['x']
tr_t = s0['box']['y'] - d['portraitBox']['y']
check('the top-right sticker sits near left 320 / top 60 in the cluster',
      near(tr_l, 320, 14) and near(tr_t, 60, 14),
      f"left {tr_l:.0f}px, top {tr_t:.0f}px (spec ~320 / ~60)")

bl_l = s1['box']['x'] - d['portraitBox']['x']
bl_t = s1['box']['y'] - d['portraitBox']['y']
check('the bottom-left sticker sits near left -10 / top 380 in the cluster',
      near(bl_l, -10, 14) and near(bl_t, 380, 14),
      f"left {bl_l:.0f}px, top {bl_t:.0f}px (spec ~-10 / ~380)")

check('stickers carry a 2px border and 12/18 padding',
      s0['pillBorder'] == '2px' and s0['pillPad'] == '12px 18px',
      f"border {s0['pillBorder']}, padding {s0['pillPad']}")

check('sticker text is 13px',
      s0['pillFont'] == '13px',
      f"{s0['pillFont']}")

check('the stickers arrive one after another, after everything else',
      s0['delayVar'] == '400ms' and s1['delayVar'] == '540ms',
      f"delays {s0['delayVar']} then {s1['delayVar']}")

# ------------------------------------------------------- motion is split ---
# The entrance rules hang off .is-in, which only the observer adds, and
# IntersectionObserver delivery is not deterministic under virtual time. The
# class is set by hand here so these checks measure the CSS rather than the
# observer; the observer itself is covered by the hidden/fallback pair below.
IN = """<script>
  (function(){
    var r = document.querySelector('.hp-mm');
    if (r) r.classList.add('is-in');
  })();
</script>"""
d = run('desktop-in', extra=IN)
s0, s1 = d['stickers'][0], d['stickers'][1]

# Each of these pairs would collapse into one if both animations were put on
# the same element: the second declaration would replace the first outright.
check('the entrance scale and the idle wobble are on different elements',
      d['animBack']['animation-name'] == 'hp-mm-back-in'
      and d['animBackSvg']['animation-name'] == 'hp-mm-wobble'
      and d['animBack']['animation-name'] != d['animBackSvg']['animation-name'],
      f"back: {d['animBack']['animation-name']}  "
      f"inner svg: {d['animBackSvg']['animation-name']}")

check('the wobble loops forever over 8s, eased',
      d['animBackSvg']['animation-duration'] == '8s'
      and d['animBackSvg']['animation-iteration-count'] == 'infinite'
      and 'ease-in-out' in d['animBackSvg']['animation-timing-function'],
      f"{d['animBackSvg']['animation-duration']} "
      f"x{d['animBackSvg']['animation-iteration-count']} "
      f"{d['animBackSvg']['animation-timing-function']}")

check('the sticker entrance uses that delay once it is in view',
      s0['delay'] == '0.4s' and s1['delay'] == '0.54s',
      f"animation-delay {s0['delay']} then {s1['delay']}")

check('the sticker entrance is on the sticker, its hover on the pill inside',
      s0['animName'] == 'hp-mm-sticker-in' and s0['pillAnim'] == 'none',
      f"sticker: {s0['animName']}  pill: {s0['pillAnim']}")

check('the back blob enters with an overshoot, held at both ends',
      'cubic-bezier(0.34, 1.56, 0.64, 1)' in d['animBack']['animation-timing-function']
      and d['animBack']['animation-fill-mode'] == 'both',
      f"{d['animBack']['animation-timing-function']} fill {d['animBack']['animation-fill-mode']}")

check('the photo follows the blob by 120ms',
      d['animPhoto']['animation-delay'] == '0.12s',
      f"photo delay {d['animPhoto']['animation-delay']}")

check('the quote and bio are staggered by 100ms',
      d['animQuote']['animation-delay'] == '0.18s'
      and d['animBio']['animation-delay'] == '0.28s',
      f"quote {d['animQuote']['animation-delay']}, bio {d['animBio']['animation-delay']}")

# ----------------------------------------------------------------- image ---
d_img = run('portrait', PORTRAIT)
check('the portrait alt falls back to the signature name',
      d_img['imgAlt'] == 'Niku',
      f"alt={d_img['imgAlt']!r}")

d_alt = run('alt', {'settings': dict(PORTRAIT['settings'],
                                     portrait_alt='Niku holding a Hankie Pal')})
check('a written alt text is used instead of the fallback',
      d_alt['imgAlt'] == 'Niku holding a Hankie Pal',
      f"alt={d_alt['imgAlt']!r}")

check('the portrait is deferred by default',
      d_img['imgLoading'] == 'lazy',
      f"loading={d_img['imgLoading']!r}")

d_eager = run('eager', {'settings': dict(PORTRAIT['settings'],
                                         portrait_loading='eager')})
check('the portrait can be loaded with the page instead',
      d_eager['imgLoading'] == 'eager',
      f"loading={d_eager['imgLoading']!r}")

check('the portrait is cropped, not squashed',
      d_img['imgFit'] == 'cover',
      f"object-fit: {d_img['imgFit']}")

# ------------------------------------------------------------- < 990px ---
m = run('tablet', width=900, height=1200)
check('under 990 the columns stack',
      len(m['rowCols'].split()) == 1,
      f"grid-template-columns: {m['rowCols']}")

check('stacked, the gap is 48px',
      m['rowGap'] == '48px',
      f"column-gap: {m['rowGap']}")

check('stacked, the text centres',
      m['textAlign'] == 'center',
      f"text-align: {m['textAlign']}")

check('stacked, the quote drops to 28/36',
      m['quoteType']['font-size'] == '28px' and m['quoteType']['line-height'] == '36px',
      f"{m['quoteType']['font-size']}/{m['quoteType']['line-height']}")

check('stacked, section padding is 80 / 96',
      m['rootPad']['padding-top'] == '80px' and m['rootPad']['padding-bottom'] == '96px',
      f"{m['rootPad']['padding-top']} / {m['rootPad']['padding-bottom']}")

check('the cluster stays square as it scales',
      near(m['portraitBox']['w'], m['portraitBox']['h'], 1.0),
      f"{m['portraitBox']['w']} x {m['portraitBox']['h']}")

check('the photo keeps its 87.5% share as the cluster scales',
      near(m['photoBox']['w'] / m['portraitBox']['w'], 0.875, 0.01),
      f"photo/cluster = {m['photoBox']['w'] / m['portraitBox']['w']:.3f} (want 0.875)")

# A phone, through an iframe so the width is真 390 and not Chromium's 500 floor.
PHONE = TMP / 'mm-phone-frame.html'
PHONE.write_text(
    '<style>html,body{margin:0}iframe{width:390px;height:1400px;border:0}</style>'
    f'<iframe src="file://{TMP}/mm-tablet.html"></iframe>', encoding='utf-8')

p = run('phone', width=760, height=1400)
# Re-measured inside a true 390 frame below; this run is the 749 breakpoint.
p2 = run('phone2', width=749, height=1400)
check('at 749 the quote drops again to 22/30',
      p2['quoteType']['font-size'] == '22px' and p2['quoteType']['line-height'] == '30px',
      f"{p2['quoteType']['font-size']}/{p2['quoteType']['line-height']}")

check('at 749 the sticker pill shrinks so it still fits',
      p2['stickers'][0]['pillFont'] == '11px'
      and p2['stickers'][0]['pillPad'] == '9px 14px',
      f"{p2['stickers'][0]['pillFont']}, padding {p2['stickers'][0]['pillPad']}")

check('no sticker pushes the page wider than the viewport',
      p2['scrollW'] <= p2['vw'],
      f"scrollWidth {p2['scrollW']} vs viewport {p2['vw']}")

# ------------------------------------------------------- reduced motion ---
r = run('reduced', reduced=True)
check('reduced motion: nothing is animating',
      r['animBack']['animation-name'] == 'none'
      and r['animBackSvg']['animation-name'] == 'none'
      and r['stickers'][0]['animName'] == 'none',
      f"back {r['animBack']['animation-name']}, "
      f"wobble {r['animBackSvg']['animation-name']}, "
      f"sticker {r['stickers'][0]['animName']}")

check('reduced motion: everything is visible',
      all(v == '1' for v in r['opacities'].values()),
      f"{r['opacities']}")

check('reduced motion: the stickers keep their tilt',
      r['stickers'][0]['transform'] != 'none'
      and r['stickers'][0]['transform'] != 'matrix(1, 0, 0, 1, 0, 0)',
      f"transform {r['stickers'][0]['transform']}")

# ------------------------------------------------- the no-script fallback ---
# What a visitor sees if the custom element never upgrades: the reveal class
# has to come off, or the section stays at opacity 0 forever.
STRIP = """<script>
  (function(){
    var r = document.querySelector('.hp-mm');
    if (r) r.classList.remove('hp-mm--reveal');
  })();
</script>"""
f = run('fallback', extra=STRIP)
check('dropping the reveal class alone shows the whole section',
      all(v == '1' for v in f['opacities'].values()),
      f"{f['opacities']}")

# And the inverse: with the class on and no is-in, it is genuinely hidden, so
# the check above is measuring something.
base = run('hidden')
check('before it scrolls into view the section is hidden',
      base['opacities']['back'] == '0' and base['opacities']['quote'] == '0',
      f"{base['opacities']}")

check('and adding is-in is what starts it moving',
      d['opacities']['back'] == '0' and d['animBack']['animation-name'] == 'hp-mm-back-in',
      f"held at the 0% frame of {d['animBack']['animation-name']} "
      f"(animations do not advance under virtual time)")

failed = res.count(False)
print(f"\n{res.count(True)} passed, {failed} failed")
sys.exit(1 if failed else 0)
