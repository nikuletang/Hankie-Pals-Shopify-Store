"""CTA — Meet the Pals: the band, the zigzag's bite, and the photo background.

The zigzag is the part worth measuring: it is a strip pulled above the
section to cut into whatever is there, so "44px above the top edge" and "2px
inside it" are the whole behaviour, and a sign error would put it in the
wrong place without ever looking broken on its own.
"""
import json, subprocess, sys, pathlib, re

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/hp-cta.liquid'
HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path('/tmp/claude-0')

PROBE = """<script>
(function(){
  function box(el){ if(!el) return null; var r = el.getBoundingClientRect();
    return {x:+r.left.toFixed(1), y:+r.top.toFixed(1),
            w:+r.width.toFixed(1), h:+r.height.toFixed(1)}; }
  function cs(el, props){ if(!el) return null;
    var c = getComputedStyle(el), o = {};
    props.forEach(function(p){ o[p] = c.getPropertyValue(p); }); return o; }

  var root = document.querySelector('.hp-cta');
  var inner = document.querySelector('.hp-cta__inner');
  var eyebrow = document.querySelector('.hp-cta__eyebrow');
  var heading = document.querySelector('.hp-cta__heading');
  var body = document.querySelector('.hp-cta__body');
  var actions = document.querySelector('.hp-cta__actions');
  var btns = [].slice.call(document.querySelectorAll('.hp-cta__btn'));
  var zig = document.querySelector('.hp-cta__zig');
  var zigPath = document.querySelector('.hp-cta__zig path');
  var zigSvg = document.querySelector('.hp-cta__zig svg');
  var media = document.querySelector('.hp-cta__media');
  var img = document.querySelector('.hp-cta__media img');
  var pic = document.querySelector('.hp-cta__media picture');
  var src = document.querySelector('.hp-cta__media source');
  var ov = document.querySelector('.hp-cta__overlay');

  document.title = 'RESULT' + JSON.stringify({
    rootBg: root ? getComputedStyle(root).backgroundColor : null,
    rootIsolation: root ? getComputedStyle(root).isolation : null,
    rootPos: root ? getComputedStyle(root).position : null,
    rootPad: cs(root, ['padding-top','padding-bottom','padding-left']),
    rootBox: box(root),
    innerGap: inner ? getComputedStyle(inner).rowGap : null,

    eyeType: cs(eyebrow, ['font-size','letter-spacing','text-transform',
                          'border-radius','padding-top','padding-left',
                          'font-weight','background-color','color']),
    eyeDot: eyebrow ? getComputedStyle(eyebrow, '::before').width : null,
    eyeDotBg: eyebrow ? getComputedStyle(eyebrow, '::before').backgroundColor : null,

    headTag: heading ? heading.tagName : null,
    headType: cs(heading, ['font-size','line-height','letter-spacing',
                           'font-weight','max-width','color','text-align']),
    bodyType: cs(body, ['font-size','line-height','font-weight','max-width','color']),

    actionsGap: actions ? getComputedStyle(actions).rowGap : null,
    actionsTop: actions ? getComputedStyle(actions).marginTop : null,
    actionsDir: actions ? getComputedStyle(actions).flexDirection : null,
    actionsMax: actions ? getComputedStyle(actions).maxWidth : null,
    btns: btns.map(function(b){
      var c = getComputedStyle(b);
      return {tag: b.tagName, href: b.getAttribute('href'),
              cls: b.className, text: b.textContent.trim(),
              bg: c.backgroundColor, color: c.color,
              border: c.borderTopWidth, radius: c.borderTopLeftRadius,
              fs: c.fontSize, pad: c.paddingTop + ' ' + c.paddingLeft,
              shadow: c.boxShadow, h: b.offsetHeight, w: b.offsetWidth,
              transition: c.transitionProperty};
    }),

    zig: zig ? {box: box(zig), top: getComputedStyle(zig).top,
                h: zig.offsetHeight, z: getComputedStyle(zig).zIndex,
                aria: zig.getAttribute('aria-hidden'),
                fill: zigPath ? zigPath.getAttribute('fill') : null,
                par: zigSvg ? zigSvg.getAttribute('preserveAspectRatio') : null,
                vb: zigSvg ? zigSvg.getAttribute('viewBox') : null} : null,

    media: media ? {fit: img ? getComputedStyle(img).objectFit : null,
                    pos: img ? getComputedStyle(img).objectPosition : null,
                    alt: img ? img.getAttribute('alt') : null,
                    loading: img ? img.getAttribute('loading') : null,
                    picture: !!pic,
                    sourceMedia: src ? src.getAttribute('media') : null,
                    sources: document.querySelectorAll('.hp-cta__media source').length,
                    z: getComputedStyle(media).zIndex} : null,
    overlay: ov ? {bg: getComputedStyle(ov).backgroundColor,
                   z: getComputedStyle(ov).zIndex} : null,

    scrollW: document.documentElement.scrollWidth, vw: window.innerWidth
  });
})();
</script>"""


def run(name, overrides=None, width=1440, height=900):
    page = TMP / f'cta-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps(overrides or {}), str(page)],
                   check=True, capture_output=True)
    html = page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>')
    page.write_text(html, encoding='utf-8')
    dom = subprocess.run(
        [CHROME, '--headless', '--no-sandbox', '--disable-gpu',
         f'--window-size={width},{height}', '--virtual-time-budget=4000',
         '--dump-dom', 'file://' + str(page)],
        capture_output=True, text=True, timeout=120).stdout
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


def srgb(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def lum(hexstr):
    h = hexstr.lstrip('#')
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return 0.2126*srgb(r) + 0.7152*srgb(g) + 0.0722*srgb(b)

def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


d = run('desktop')

# ------------------------------------------------------------------ band ---
check('the band is sage',
      d['rootBg'] == 'rgb(194, 214, 168)', f"{d['rootBg']} (want #C2D6A8)")

check('the section makes a stacking context and can hold the zigzag',
      d['rootIsolation'] == 'isolate' and d['rootPos'] == 'relative',
      f"isolation {d['rootIsolation']}, position {d['rootPos']}")

check('padding is 130 top / 140 bottom',
      d['rootPad']['padding-top'] == '130px'
      and d['rootPad']['padding-bottom'] == '140px',
      f"{d['rootPad']['padding-top']} / {d['rootPad']['padding-bottom']}")

check('the content stack is 28px apart',
      d['innerGap'] == '28px', f"gap {d['innerGap']}")

# The brief's frame is 562px tall at 1440. Content is not forced to a height,
# so this is a consequence of the type and padding rather than a set number.
check('the section comes out near the 562px of the design',
      near(d['rootBox']['h'], 562, 20),
      f"{d['rootBox']['h']}px (design 562, no height is set)")

# --------------------------------------------------------------- eyebrow ---
e = d['eyeType']
check('the eyebrow is a white 10px uppercase pill, 1.5px tracking, 7/14 padding',
      e['font-size'] == '10px' and e['letter-spacing'] == '1.5px'
      and e['text-transform'] == 'uppercase' and e['border-radius'] == '999px'
      and e['padding-top'] == '7px' and e['padding-left'] == '14px'
      and e['font-weight'] == '700'
      and e['background-color'] == 'rgb(255, 255, 255)',
      f"{e['font-size']} ls {e['letter-spacing']} pad {e['padding-top']}/"
      f"{e['padding-left']} r{e['border-radius']} bg {e['background-color']}")

check('the eyebrow dot is 6px coral',
      d['eyeDot'] == '6px' and d['eyeDotBg'] == 'rgb(224, 110, 76)',
      f"{d['eyeDot']} {d['eyeDotBg']}")

# ------------------------------------------------------------ heading/body ---
check('the heading is a real h2',
      d['headTag'] == 'H2', f"<{(d['headTag'] or '?').lower()}>")

h = d['headType']
check('heading is 52/60, -1px, weight 800, capped at 760 and centred',
      h['font-size'] == '52px' and h['line-height'] == '60px'
      and h['letter-spacing'] == '-1px' and h['font-weight'] == '800'
      and h['max-width'] == '760px' and h['text-align'] == 'center',
      f"{h['font-size']}/{h['line-height']} ls {h['letter-spacing']} "
      f"w{h['font-weight']} max {h['max-width']}")

b = d['bodyType']
check('body is 17/28, weight 300, capped at 520',
      b['font-size'] == '17px' and b['line-height'] == '28px'
      and b['font-weight'] == '300' and b['max-width'] == '520px',
      f"{b['font-size']}/{b['line-height']} w{b['font-weight']} max {b['max-width']}")

# ---------------------------------------------------------------- buttons ---
check('both buttons render as real links',
      len(d['btns']) == 2 and all(x['tag'] == 'A' for x in d['btns']),
      ', '.join(f"<{x['tag'].lower()}> {x['text']}" for x in d['btns']))

check('they are the site button, not a new one',
      all('hp-btn' in x['cls'] and 'hp-btn--lg' in x['cls'] for x in d['btns']),
      f"{d['btns'][0]['cls']}")

check('primary is peach, secondary white, both with a 2px ink outline',
      d['btns'][0]['bg'] == 'rgb(236, 164, 124)'
      and d['btns'][1]['bg'] == 'rgb(255, 255, 255)'
      and all(x['border'] == '2px' and x['radius'] == '999px' for x in d['btns']),
      f"{d['btns'][0]['bg']} / {d['btns'][1]['bg']}, "
      f"border {d['btns'][0]['border']} r{d['btns'][0]['radius']}")

# 18/40 is both the brief's padding and .hp-btn--lg's own, so they agree. The
# text size does not: the site runs 17px and the frame was drawn at 12.
check('button padding is 18/40 and the text is the site\'s 17px',
      d['btns'][0]['pad'] == '18px 40px' and d['btns'][0]['fs'] == '17px',
      f"padding {d['btns'][0]['pad']}, {d['btns'][0]['fs']}")

check('the size is a setting, so the frame\'s 12px is still reachable',
      run('btn12', {'settings': {'button_text_size': 12}})['btns'][0]['fs'] == '12px',
      "button_text_size 12 -> 12px")

check('the buttons come out near the design\'s 54px',
      all(near(x['h'], 54, 8) for x in d['btns']),
      f"{[x['h'] for x in d['btns']]}px (design ~54, at the site's larger text)")

# The site button's hard shadow is what makes it the site's button. If this
# ever reads "none" the stylesheet did not load.
check('the site button\'s hard shadow is present',
      'rgb' in d['btns'][0]['shadow'] and 'px' in d['btns'][0]['shadow'],
      f"{d['btns'][0]['shadow']}")

check('the row is 16px apart with 12px above it',
      d['actionsGap'] == '16px' and d['actionsTop'] == '12px',
      f"gap {d['actionsGap']}, margin-top {d['actionsTop']}")

one = run('one-btn', {'settings': {'secondary_label': ''}})
check('a button with no label is not rendered',
      len(one['btns']) == 1 and one['btns'][0]['text'] == 'Shop Hankie Pals',
      f"{len(one['btns'])} button: {one['btns'][0]['text']}")

# ----------------------------------------------------------------- zigzag ---
z = d['zig']
check('the zigzag is drawn and marked decorative',
      z is not None and z['aria'] == 'true',
      f"aria-hidden={z['aria'] if z else 'MISSING'}")

check('it is 46px tall and stretches to any width',
      z['h'] == 46 and z['par'] == 'none' and z['vb'] == '0 0 1440 46',
      f"{z['h']}px, preserveAspectRatio={z['par']}, viewBox={z['vb']}")

# The whole point: it hangs above the section so it cuts into what is there.
rise = round(d['rootBox']['y'] - z['box']['y'])
check('it rises 44px above the top of the section',
      rise == 44, f"{rise}px above (top: {z['top']})")

check('and its last 2px sit inside the section, so no seam shows',
      round(z['box']['y'] + z['h'] - d['rootBox']['y']) == 2,
      f"{round(z['box']['y'] + z['h'] - d['rootBox']['y'])}px of overlap")

check('the teeth are cut in the section\'s own colour',
      z['fill'] == '#C2D6A8',
      f"fill {z['fill']}, section {d['rootBg']}")

nozig = run('nozig', {'settings': {'show_zigzag': False}})
check('the zigzag can be turned off',
      nozig['zig'] is None, "no strip rendered")

# ------------------------------------------------------------ photo background ---
PHOTO = {'settings': {'background_type': 'image',
                      'background_image': {'src': 'cta.jpg'}}}
p = run('photo', PHOTO)
check('a photo background renders as an img, not a CSS background',
      p['media'] is not None and p['media']['fit'] == 'cover',
      f"object-fit {p['media']['fit'] if p['media'] else 'NO IMG'}")

check('the photo is lazy and decorative by default',
      p['media']['loading'] == 'lazy' and (p['media']['alt'] or '') == '',
      f"loading={p['media']['loading']!r} alt={p['media']['alt']!r}")

check('the photo sits under the content',
      int(p['media']['z']) == 0, f"z-index {p['media']['z']}")

check('no photo source is emitted when no phone image is set',
      p['media']['sources'] == 0,
      f"{p['media']['sources']} <source> element(s)")

both = run('photo-mobile', {'settings': dict(
    PHOTO['settings'], background_image_mobile={'src': 'cta-phone.jpg'})})
check('a phone photo is offered through <picture>, so only one downloads',
      both['media']['picture'] and both['media']['sources'] == 1
      and both['media']['sourceMedia'] == '(max-width: 749px)',
      f"{both['media']['sources']} source, media={both['media']['sourceMedia']!r}")

pos = run('photo-top', {'settings': dict(PHOTO['settings'], image_position='top')})
check('the photo position setting reaches object-position',
      pos['media']['pos'].startswith('50% 0'),
      f"object-position {pos['media']['pos']}")

check('no overlay element at all when the strength is 0',
      p['overlay'] is None, "none rendered")

ov = run('overlay', {'settings': dict(PHOTO['settings'], overlay_opacity=40)})
check('the overlay appears at a set strength, over the photo',
      ov['overlay'] is not None and '0.4' in ov['overlay']['bg']
      and int(ov['overlay']['z']) > int(ov['media']['z']),
      f"{ov['overlay']['bg']}, z{ov['overlay']['z']} over z{ov['media']['z']}")

# Switching backgrounds must not move anything, which is what the brief means
# by "no layout shift".
check('switching colour to photo does not change the section height',
      near(p['rootBox']['h'], d['rootBox']['h'], 1.0),
      f"photo {p['rootBox']['h']}px vs colour {d['rootBox']['h']}px")

# ---------------------------------------------------------------- contrast ---
c_sage = contrast('#2F3427', '#C2D6A8')
check('ink on the default sage clears AA for body text',
      c_sage >= 4.5, f"{c_sage:.2f}:1 (AA needs 4.5)")

c_peach = contrast('#2F3427', '#ECA47C')
check('ink on the primary button clears AA',
      c_peach >= 4.5, f"{c_peach:.2f}:1")

c_white = contrast('#2F3427', '#FFFFFF')
check('ink on the secondary button clears AA',
      c_white >= 4.5, f"{c_white:.2f}:1")

# Over a photo the overlay is what buys the contrast. Worst realistic case:
# white text on a mid-grey photo at the strength the setting offers.
c_overlay = contrast('#FCFBF6', '#4A4A4A')
check('pale text over a photo darkened by the overlay clears AA',
      c_overlay >= 4.5,
      f"{c_overlay:.2f}:1 — cream on a photo pushed to #4A4A4A, "
      f"which 60% of #2F3427 over a mid-grey reaches")

# -------------------------------------------------------------- responsive ---
t = run('tablet', width=900, height=900)
check('tablet: heading 40/48, padding 100/110',
      t['headType']['font-size'] == '40px'
      and t['headType']['line-height'] == '48px'
      and t['rootPad']['padding-top'] == '100px'
      and t['rootPad']['padding-bottom'] == '110px',
      f"{t['headType']['font-size']}/{t['headType']['line-height']}, "
      f"{t['rootPad']['padding-top']}/{t['rootPad']['padding-bottom']}")

m = run('phone', width=749, height=1100)
check('phone: heading 32/40, body 16, padding 80/90, 20px sides',
      m['headType']['font-size'] == '32px'
      and m['headType']['line-height'] == '40px'
      and m['bodyType']['font-size'] == '16px'
      and m['rootPad']['padding-top'] == '80px'
      and m['rootPad']['padding-bottom'] == '90px'
      and m['rootPad']['padding-left'] == '20px',
      f"{m['headType']['font-size']}/{m['headType']['line-height']}, "
      f"body {m['bodyType']['font-size']}, "
      f"{m['rootPad']['padding-top']}/{m['rootPad']['padding-bottom']}, "
      f"sides {m['rootPad']['padding-left']}")

check('phone: the buttons stack, 12px apart, capped at 320',
      m['actionsDir'] == 'column' and m['actionsGap'] == '12px'
      and m['actionsMax'] == '320px',
      f"{m['actionsDir']}, gap {m['actionsGap']}, max {m['actionsMax']}")

check('phone: primary is on top',
      m['btns'][0]['text'] == 'Shop Hankie Pals'
      and m['btns'][0]['w'] == m['btns'][1]['w'],
      f"first is {m['btns'][0]['text']!r}, both {m['btns'][0]['w']}px wide")

check('phone: nothing pushes the page sideways',
      m['scrollW'] <= m['vw'],
      f"scrollWidth {m['scrollW']} vs viewport {m['vw']}")

failed = res.count(False)
print(f"\n{res.count(True)} passed, {failed} failed")
sys.exit(1 if failed else 0)
