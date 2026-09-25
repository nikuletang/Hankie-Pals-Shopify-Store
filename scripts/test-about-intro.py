"""Check the About intro.

The overlap is the layout. It is built from grid tracks rather than absolute
positioning, which is what keeps the row as tall as its tallest child -- so the
claims worth settling in pixels are that the photograph really does reach back
over the panel, that it really does stand proud of the panel at both ends, and
that neither of those two facts ever costs the page a sideways scrollbar.

The pills are placed by percentage of the photograph's own box, so their place
has to hold at 1400px and at 390px alike.

The section fades in, which every measurement of where something sits has to
be held clear of: under a virtual time budget an animation advances some
unpredictable way into its first frames, so a box measured while it is running
is a box measured at neither end of it. Every geometry check below therefore
renders with the reveal disabled -- the state a reduced-motion visitor gets,
and the state the animation finishes in -- and the animation itself is
measured separately, after it has had the time to finish.
"""
import json, re, subprocess, sys, pathlib
from PIL import Image, ImageDraw

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path(__file__).resolve().parent.parent
SECTION = ROOT / 'sections' / 'about-intro.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

STILL = """<style>
  .hp-ai--reveal [data-reveal],
  .hp-ai--reveal [data-reveal].is-in {
    opacity: 1 !important;
    animation: none !important;
    transform: none !important;
  }
  .hp-ai--reveal .hp-ai__pill,
  .hp-ai--reveal .hp-ai__pill.is-in {
    transform: translate(-50%, -50%) rotate(var(--tx)) !important;
  }
</style>"""

PROBE = """
function bx(e){if(!e)return null;var r=e.getBoundingClientRect();
 return {l:Math.round(r.left),r:Math.round(r.right),t:Math.round(r.top),
         b:Math.round(r.bottom),w:Math.round(r.width),h:Math.round(r.height)};}
function snap(d,w){
  var sec=d.querySelector('.hp-ai');
  var panel=d.querySelector('.hp-ai__panel');
  var fig=d.querySelector('.hp-ai__figure');
  var media=d.querySelector('.hp-ai__media');
  var img=d.querySelector('.hp-ai__media img');
  var head=d.querySelector('.hp-ai__heading');
  var eb=d.querySelector('.hp-ai__eyebrow');
  var body=d.querySelector('.hp-ai__body p')||d.querySelector('.hp-ai__body');
  return {
    secBox:bx(sec), secOverflow:sec?w.getComputedStyle(sec).overflowX:null,
    secBg:sec?w.getComputedStyle(sec).backgroundColor:null,
    panel:panel?{box:bx(panel), bg:w.getComputedStyle(panel).backgroundColor,
                 radius:w.getComputedStyle(panel).borderTopLeftRadius,
                 padEnd:w.getComputedStyle(panel).paddingInlineEnd,
                 z:w.getComputedStyle(panel).zIndex,
                 pos:w.getComputedStyle(panel).position}:null,
    fig:fig?{box:bx(fig), pos:w.getComputedStyle(fig).position}:null,
    media:media?{box:bx(media), radius:w.getComputedStyle(media).borderTopLeftRadius,
                 overflow:w.getComputedStyle(media).overflow,
                 bg:w.getComputedStyle(media).backgroundColor,
                 z:w.getComputedStyle(media).zIndex,
                 shadow:w.getComputedStyle(media).boxShadow}:null,
    img:img?{box:bx(img), fit:w.getComputedStyle(img).objectFit,
             pos:w.getComputedStyle(img).objectPosition,
             alt:img.getAttribute('alt')}:null,
    headTag:head?head.tagName:null,
    headSize:head?w.getComputedStyle(head).fontSize:null,
    headInk:head?w.getComputedStyle(head).color:null,
    headBrs:head?head.querySelectorAll('br').length:0,
    ebBox:bx(eb), ebRadius:eb?w.getComputedStyle(eb).borderTopLeftRadius:null,
    ebText:eb?eb.textContent.trim():null,
    ebDot:bx(d.querySelector('.hp-ai__eyebrow-dot')),
    ebWords:bx(eb?eb.querySelector('span:last-child'):null),
    ebLine:eb?w.getComputedStyle(eb).lineHeight:null,
    bodySize:body?w.getComputedStyle(body).fontSize:null,
    bodyInk:body?w.getComputedStyle(body).color:null,
    bodyText:body?body.textContent.trim().slice(0,30):null,
    pebbles:[].map.call(d.querySelectorAll('.hp-ai__pebble'),function(e){
      var c=w.getComputedStyle(e);
      return {box:bx(e), op:c.opacity, bg:c.backgroundColor, z:c.zIndex,
              events:c.pointerEvents, hidden:e.getAttribute('aria-hidden')};}),
    pills:[].map.call(d.querySelectorAll('.hp-ai__pill'),function(e){
      return {box:bx(e), text:e.textContent.trim(),
              z:w.getComputedStyle(e).zIndex};}),
    hasButton: !!d.querySelector('.hp-ai a, .hp-ai button'),
    revealClass: sec?sec.classList.contains('hp-ai--reveal'):null,
    revealed:[].map.call(d.querySelectorAll('[data-reveal]'),function(e){
      return {cls:e.className.replace(/hp-ai__/g,''), isIn:e.classList.contains('is-in'),
              op:w.getComputedStyle(e).opacity,
              tf:w.getComputedStyle(e).transform};}),
    docW:d.documentElement.scrollWidth, winW:w.innerWidth};
}
"""


def render(name, overrides, still=True):
    page = TMP / f'ai-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(page)], check=True,
                   capture_output=True)
    if still:
        page.write_text(page.read_text(encoding='utf-8').replace(
            '</body>', STILL + '</body>'), encoding='utf-8')
    return page


SETTLE = ("document.getAnimations().forEach(function(a){"
          "try{a.finish();}catch(e){}});")


def run(name, width=1400, overrides=None, still=True, wait=400, budget=6000,
        flags=(), settle=False, sabotage=None):
    page = render(name, overrides, still)
    html = page.read_text(encoding='utf-8')
    if sabotage:
        # Runs before the section's own script, so the section meets the
        # broken browser rather than being broken after the fact.
        html = html.replace('<body>', f'<body><script>{sabotage}</script>', 1)
    html = html.replace('</body>',
        '<script>' + PROBE +
        "setTimeout(function(){" + (SETTLE if settle else '') +
        "document.title='RESULT'+JSON.stringify("
        f"snap(document,window));}},{wait});</script></body>")
    page.write_text(html, encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},1400', f'--virtual-time-budget={budget}', *flags,
        '--dump-dom', 'file://' + str(page)],
        capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


def framed(name, width=390, overrides=None):
    """A real phone width. A Chromium window will not go below 500px, so the
    section is measured inside an iframe that can."""
    inner = render(name + '-inner', overrides)
    inner.write_text(inner.read_text(encoding='utf-8').replace(
        '</body>', '<script>' + PROBE + '</script></body>'), encoding='utf-8')
    wrap = TMP / f'ai-{name}-wrap.html'
    wrap.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0}'
        f'iframe{{width:{width}px;height:1800px;border:0;display:block}}</style>'
        f'<iframe src="{inner.name}"></iframe><script>setTimeout(function(){{'
        'var f=document.querySelector("iframe");document.title="RESULT"+JSON.stringify('
        'f.contentWindow.snap(f.contentDocument,f.contentWindow));},700);</script>',
        encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', f'--window-size={width + 310},1900',
        '--virtual-time-budget=8000', '--dump-dom', 'file://' + str(wrap)],
        capture_output=True, text=True, timeout=200).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def rgb(v):
    return [int(x) for x in re.findall(r'\d+', v)[:3]]


def contrast(a, b):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    def lum(c):
        return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


# A photo with a band at the very top and another at the very bottom, so a
# claim about cropping is settled in pixels rather than in geometry.
def banded(path):
    im = Image.new('RGB', (600, 900), (250, 250, 250))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 599, 40], fill=(220, 40, 40))
    d.rectangle([0, 859, 599, 899], fill=(30, 90, 220))
    im.save(path)
    return path


PHOTO = banded(TMP / 'ai-photo.png')
WITH_PHOTO = {'settings': {'image': str(PHOTO), 'image_alt': 'A toddler holding a Hankie Pal'}}

d = run('default', overrides=WITH_PHOTO)

# Everything below reads a measurement off one of these. A None satisfies
# several of the comparisons that follow ('not in', '>='), so a missing element
# would read as a pass rather than a failure; this settles it once, up front.
parts = {'section': d['secBox'], 'panel': d['panel'], 'figure': d['fig'],
         'photo box': d['media'], 'photo': d['img'], 'heading': d['headSize'],
         'eyebrow': d['ebBox'], 'paragraph': d['bodySize']}
missing = [k for k, v in parts.items() if v is None]
check('every part of the section is on the page to begin with',
      not missing, f"missing: {', '.join(missing) if missing else 'nothing'}")
if missing:
    print(f"\n{sum(res)}/{len(res)} passed")
    sys.exit(1)

# ------------------------------------------------------------- the overlap --
check('the photo reaches back over the panel, it does not sit beside it',
      d['fig']['box']['l'] < d['panel']['box']['r'],
      f"figure starts {d['fig']['box']['l']}, panel ends {d['panel']['box']['r']}")

ov = d['panel']['box']['r'] - d['fig']['box']['l']
check('and it reaches back by the distance the setting asks for',
      abs(ov - 72) <= 2, f"overlap {ov}px, setting 72px")

check('the photo stands proud of the panel at the top',
      d['media']['box']['t'] < d['panel']['box']['t'],
      f"photo top {d['media']['box']['t']}, panel top {d['panel']['box']['t']}")
check('and at the bottom, so it reads as a window over the panel',
      d['media']['box']['b'] > d['panel']['box']['b'],
      f"photo bottom {d['media']['box']['b']}, panel bottom {d['panel']['box']['b']}")

top_gap = d['panel']['box']['t'] - d['media']['box']['t']
bot_gap = d['media']['box']['b'] - d['panel']['box']['b']
check('the overhang is even at both ends, so nothing looks dropped',
      abs(top_gap - bot_gap) <= 2, f"{top_gap}px above, {bot_gap}px below")

check('the overlap comes from grid tracks, not from taking anything out of flow',
      d['fig']['pos'] in ('static', 'relative')
      and d['panel']['pos'] in ('static', 'relative')
      and d['fig']['box']['h'] > 0 and d['panel']['box']['h'] > 0,
      f"figure {d['fig']['pos']} {d['fig']['box']['h']}px tall, "
      f"panel {d['panel']['pos']} {d['panel']['box']['h']}px tall")

check('the panel holds its words clear of the overlap',
      float(d['panel']['padEnd'].rstrip('px')) >= 72,
      f"end padding {d['panel']['padEnd']} against a 72px overlap")

check('the photo paints over the panel rather than under it',
      d['media']['box']['t'] < d['panel']['box']['b'] and d['media']['box']['l']
      < d['panel']['box']['r'], 'the two boxes really do intersect')

# --------------------------------------------------------- the panel width --
inner_w = d['panel']['box']['w'] + (d['fig']['box']['r'] - d['panel']['box']['r'])
check('the panel takes the share of the row the setting asks for',
      abs(round(100 * d['panel']['box']['w'] / inner_w) - 56) <= 2,
      f"panel {d['panel']['box']['w']}px of {inner_w}px")

wide = run('wide-panel', overrides={'settings': dict(WITH_PHOTO['settings'],
                                                     panel_width=70, overlap=120)})
check('widening the panel and deepening the overlap both land',
      wide['panel']['box']['w'] > d['panel']['box']['w']
      and (wide['panel']['box']['r'] - wide['fig']['box']['l']) > ov,
      f"panel {d['panel']['box']['w']}->{wide['panel']['box']['w']}px, "
      f"overlap {ov}->{wide['panel']['box']['r'] - wide['fig']['box']['l']}px")

flat = run('no-overlap', overrides={'settings': dict(WITH_PHOTO['settings'], overlap=0)})
check('and taking the overlap to zero butts them up without a gap',
      abs(flat['fig']['box']['l'] - flat['panel']['box']['r']) <= 1,
      f"figure starts {flat['fig']['box']['l']}, panel ends {flat['panel']['box']['r']}")

# --------------------------------------------------------------- the photo --
check('the photo fills its shape rather than stretching to it',
      d['img']['fit'] == 'cover', f"object-fit {d['img']['fit']}")
check('the shape is an arch by default, not a rectangle',
      isinstance(d['media']['radius'], str) and '%' in d['media']['radius'],
      f"top-left radius {d['media']['radius']}")
check('the shape clips the photo inside it',
      d['media']['overflow'] == 'hidden', f"overflow {d['media']['overflow']}")
check('the photo box has a height object-fit can resolve against',
      d['img']['box']['h'] > 0 and abs(d['img']['box']['h'] - 460) <= 2,
      f"{d['img']['box']['w']}x{d['img']['box']['h']}px against a 460px setting")
check('the alt text you type is the alt text that ships',
      d['img']['alt'] == 'A toddler holding a Hankie Pal', f"alt {d['img']['alt']!r}")
check('the photo carries a shadow, so it lifts off the panel',
      isinstance(d['media']['shadow'], str)
      and d['media']['shadow'] not in ('none', ''),
      f"{str(d['media']['shadow'])[:44]}")

no_photo = run('no-photo', overrides={})
check('before a photo is chosen the shape still holds its place',
      no_photo['media']['box']['h'] > 400 and no_photo['img'] is None,
      f"empty media box {no_photo['media']['box']['w']}x{no_photo['media']['box']['h']}px")

focus = run('focus-top', overrides={'settings': dict(WITH_PHOTO['settings'],
                                                     photo_focus='top')})
check('and which part of it survives the crop is yours to choose',
      focus['img']['pos'].startswith('50% 0') or focus['img']['pos'] == 'center top',
      f"object-position {focus['img']['pos']}")

# ---------------------------------------------------------------- the words --
check("the heading is the page's h1 by default",
      d['headTag'] == 'H1', f"heading is <{(d['headTag'] or '?').lower()}>")
h3 = run('h3', overrides={'settings': dict(WITH_PHOTO['settings'], heading_tag='h3')})
check('and can step down when something above it owns the h1',
      h3['headTag'] == 'H3', f"heading is <{(h3['headTag'] or '?').lower()}>")

check('the eyebrow is a plain line by default, not a capsule',
      d['ebRadius'] in ('0px', ''), f"eyebrow radius {d['ebRadius']}")
cap = run('capsule', overrides={'settings': dict(WITH_PHOTO['settings'],
                                                 eyebrow_style='capsule')})
check('and becomes a capsule when you ask for one',
      cap['ebRadius'] is not None and cap['ebRadius'].endswith('px')
      and float(cap['ebRadius'].rstrip('px')) >= 12,
      f"eyebrow radius {cap['ebRadius']}")

breaks = run('breaks', overrides={'settings': dict(
    WITH_PHOTO['settings'], heading="Here's to\nthe wobble.")})
check('a line break you type in the heading is a line break on the page',
      breaks['headBrs'] == 1, f"{breaks['headBrs']} <br> in the heading")

check('the paragraph keeps the size it was given, so it is not a <p> in a <p>',
      d['bodySize'] == '17px', f"paragraph renders at {d['bodySize']}")
check('and the words in it are the words you typed',
      d['bodyText'].startswith('Totterful makes'), f"{d['bodyText']!r}")

check('there is no call to action competing with the statement',
      d['hasButton'] is False, 'no link or button in the section')

# -------------------------------------------------------------- the pebbles --
check('two pebbles sit behind the layout',
      len(d['pebbles']) == 2, f"{len(d['pebbles'])} pebbles")
check('they are decorative: never read out, never clickable',
      all(p['hidden'] == 'true' and p['events'] == 'none' for p in d['pebbles']),
      'aria-hidden and pointer-events none on both')
check('the photo pebble sits behind the panel, not on its face',
      int(d['pebbles'][1]['z'] or 0) < int(d['panel']['z'] or 0)
      and int(d['panel']['z'] or 0) < int(d['media']['z'] or 0),
      f"pebble z {d['pebbles'][1]['z']}, panel z {d['panel']['z']}, "
      f"photo z {d['media']['z']}")
check('their opacity is the setting, not a guess',
      all(abs(float(p['op']) - 0.55) < 0.01 for p in d['pebbles']),
      f"opacity {[p['op'] for p in d['pebbles']]}")

off = run('no-pebbles', overrides={'settings': dict(WITH_PHOTO['settings'],
                                                    show_pebbles=False)})
check('and they can be turned off',
      len(off['pebbles']) == 0, 'no pebbles rendered')

# Behind the panel and the photo both, a pebble is easy to place somewhere it
# can never be seen -- which reads as a broken setting rather than as a choice.
photo_peb = d['pebbles'][1]['box']
check('the photo pebble is actually visible where it starts out',
      photo_peb['b'] > d['media']['box']['b'] + 8
      and photo_peb['r'] > d['panel']['box']['r'],
      f"pebble {photo_peb['l']}-{photo_peb['r']} x {photo_peb['t']}-{photo_peb['b']}, "
      f"photo bottom {d['media']['box']['b']}, panel ends {d['panel']['box']['r']}")
check('and it stays inside the band rather than leaning on the next section',
      photo_peb['b'] <= d['secBox']['b'],
      f"pebble ends {photo_peb['b']}, band ends {d['secBox']['b']}")

# ---------------------------------------------------------------- the pills --
check('the preset ships two pill labels on the photo',
      len(d['pills']) == 2, f"{len(d['pills'])} pills")
check('each pill sits over the photo, not beside it',
      all(p['box']['l'] >= d['media']['box']['l'] - 60
          and p['box']['r'] <= d['media']['box']['r'] + 60 for p in d['pills']),
      f"photo spans {d['media']['box']['l']}-{d['media']['box']['r']}")
check('and over it rather than under it',
      all(int(p['z']) > 1 for p in d['pills']), f"pill z {[p['z'] for p in d['pills']]}")

moved = run('pill-moved', overrides={'settings': WITH_PHOTO['settings'], 'blocks': [
    {'type': 'pill', 'settings': {'text': 'Crinkle ears', 'x': 20, 'y': 80, 'rotate': 0}}]})
check('a pill goes exactly where its two numbers put it',
      abs(moved['pills'][0]['box']['l'] + moved['pills'][0]['box']['w'] / 2
          - (moved['media']['box']['l'] + 0.20 * moved['media']['box']['w'])) <= 3
      and abs(moved['pills'][0]['box']['t'] + moved['pills'][0]['box']['h'] / 2
              - (moved['media']['box']['t'] + 0.80 * moved['media']['box']['h'])) <= 3,
      f"centre {round(moved['pills'][0]['box']['l'] + moved['pills'][0]['box']['w'] / 2)},"
      f"{round(moved['pills'][0]['box']['t'] + moved['pills'][0]['box']['h'] / 2)} "
      f"against 20%/80% of the photo")

empty_pill = run('pill-blank', overrides={'settings': WITH_PHOTO['settings'], 'blocks': [
    {'type': 'pill', 'settings': {'text': ''}}]})
check('a pill with no words on it renders nothing at all',
      len(empty_pill['pills']) == 0, 'no empty capsule left on the photo')

# --------------------------------------------------------------- it reads ---
check('the heading reads against the panel',
      contrast(rgb(d['headInk']), rgb(d['panel']['bg'])) >= 7,
      f"{contrast(rgb(d['headInk']), rgb(d['panel']['bg']))}:1")
check('and so does the paragraph, at body size',
      contrast(rgb(d['bodyInk']), rgb(d['panel']['bg'])) >= 4.5,
      f"{contrast(rgb(d['bodyInk']), rgb(d['panel']['bg']))}:1")
check('the panel is distinguishable from the page behind it',
      rgb(d['panel']['bg']) != rgb(d['secBg']),
      f"panel {d['panel']['bg']} on {d['secBg']}")

# ------------------------------------------------------------- on a phone ---
p390 = framed('phone', 390, WITH_PHOTO)
check('stacked on a phone, the words and the photo are in one column',
      abs(p390['panel']['box']['l'] - p390['fig']['box']['l']) <= 2,
      f"panel at {p390['panel']['box']['l']}, figure at {p390['fig']['box']['l']}")
check('the words come first and the photo follows',
      p390['panel']['box']['t'] < p390['media']['box']['t'],
      f"panel top {p390['panel']['box']['t']}, photo top {p390['media']['box']['t']}")
check('the overlap survives the breakpoint, running up and down instead',
      p390['fig']['box']['t'] < p390['panel']['box']['b'],
      f"figure starts {p390['fig']['box']['t']}, panel ends {p390['panel']['box']['b']}")
check('the photo takes its shape from the ratio rather than the desktop height',
      abs(p390['media']['box']['h'] / p390['media']['box']['w'] - 1.5) <= 0.06,
      f"{p390['media']['box']['w']}x{p390['media']['box']['h']}px, "
      f"ratio {round(p390['media']['box']['h'] / p390['media']['box']['w'], 2)} against 2:3")
check('the heading steps down to its mobile size',
      p390['headSize'] == '34px', f"heading {p390['headSize']}")

# The eyebrow is a sentence, so on a phone it wraps -- and a bullet that has
# drifted to the middle of a wrapped block no longer reads as a bullet.
lines = round(p390['ebWords']['h'] / float(p390['ebLine'].rstrip('px')))
dot_mid = p390['ebDot']['t'] + p390['ebDot']['h'] / 2
line1_mid = p390['ebWords']['t'] + float(p390['ebLine'].rstrip('px')) / 2
check('the eyebrow really does wrap at phone width',
      lines >= 2, f"{lines} lines of {p390['ebLine']}")
check('and its dot stays on the first line rather than drifting to the middle',
      abs(dot_mid - line1_mid) <= 2,
      f"dot centre {round(dot_mid)}, first line centre {round(line1_mid)}")
check('every pill stays on the photo at phone width',
      all(p['box']['l'] >= p390['media']['box']['l'] - 30
          and p['box']['r'] <= p390['media']['box']['r'] + 30 for p in p390['pills']),
      f"pills {[(p['box']['l'], p['box']['r']) for p in p390['pills']]} "
      f"against photo {p390['media']['box']['l']}-{p390['media']['box']['r']}")

above = framed('phone-above', 390, {'settings': dict(WITH_PHOTO['settings'],
                                                     mobile_layout='photo_above')})
check('and the photo can be put above the words instead',
      above['media']['box']['t'] < above['panel']['box']['t'],
      f"photo top {above['media']['box']['t']}, panel top {above['panel']['box']['t']}")
check('with the overlap flipped to match, so the words are not sat on',
      above['panel']['box']['t'] < above['fig']['box']['b'],
      f"panel starts {above['panel']['box']['t']}, figure ends {above['fig']['box']['b']}")

# --------------------------------------------------- it never widens the page --
check('the band clips whatever hangs off its sides',
      d['secOverflow'] in ('clip', 'hidden'), f"overflow-x {d['secOverflow']}")
for label, snap in (('at 1400px', d), ('at 390px', p390), ('at 390px, photo first', above)):
    check(f'and the page never scrolls sideways {label}',
          snap['docW'] <= snap['winW'] + 1,
          f"document {snap['docW']}px in {snap['winW']}px")

deep = framed('phone-deep', 360, {'settings': dict(WITH_PHOTO['settings'],
                                                   overlap=180, pebble_size=420,
                                                   pebble_x=60)})
check('not even with the overlap and the pebbles pushed to their limits',
      deep['docW'] <= deep['winW'] + 1,
      f"document {deep['docW']}px in {deep['winW']}px")

# ------------------------------------------------------------ the blob ----
# Two organic shapes in one menu are only worth having if they are told apart,
# so the blob has to be a different shape from the pebble rather than a second
# name for it.
shapes = {}
for shape_name in ('arch', 'blob', 'pebble', 'soft', 'circle'):
    shapes[shape_name] = run(f'shape-{shape_name}', overrides={'settings': dict(
        WITH_PHOTO['settings'], photo_shape=shape_name)})['media']['radius']
check('each photo shape is a different shape',
      len(set(shapes.values())) == 5,
      '; '.join(f"{k} {v}" for k, v in shapes.items()))
check('and the blob is lopsided, where the pebble is nearly even',
      shapes['blob'] != shapes['pebble']
      and abs(float(shapes['blob'].split()[0].rstrip('%')) - 50)
      > abs(float(shapes['pebble'].split()[0].rstrip('%')) - 50),
      f"blob {shapes['blob']}, pebble {shapes['pebble']}")

# ------------------------------------------------------ the section arrives --
# The animation's only unacceptable failure is words that never appear, so
# most of what follows is the same question asked of a different way for the
# script not to run.
anim = run('anim', overrides=WITH_PHOTO, still=False, wait=1200, budget=12000,
           settle=True)
order = [r['cls'].split()[0] for r in anim['revealed']]
check('every piece of the section is marked to arrive',
      len(anim['revealed']) == 6, f"{len(anim['revealed'])} pieces: {order}")
check('the words arrive first, then the photo, then the labels on it',
      order == ['eyebrow', 'heading', 'body', 'media', 'pill', 'pill'], f"{order}")
check('the script marks every piece as arrived',
      all(r['isIn'] for r in anim['revealed']),
      f"is-in on {sum(r['isIn'] for r in anim['revealed'])} of {len(anim['revealed'])}")
check('and the animation ends with not one piece left invisible',
      all(float(r['op']) > 0.99 for r in anim['revealed']),
      f"opacity {[r['op'] for r in anim['revealed']]}")
check('a pill lands back on its mark rather than in the photo corner',
      abs(anim['pills'][0]['box']['l'] + anim['pills'][0]['box']['w'] / 2
          - (anim['media']['box']['l'] + 0.74 * anim['media']['box']['w'])) <= 4,
      f"pill centre {round(anim['pills'][0]['box']['l'] + anim['pills'][0]['box']['w'] / 2)}"
      f" against 74% of {anim['media']['box']['l']}-{anim['media']['box']['r']}")

none = run('anim-none', overrides={'settings': dict(WITH_PHOTO['settings'],
                                                    reveal='none')}, still=False)
check('turning the animation off removes the hidden start state entirely',
      none['revealClass'] is False
      and all(float(r['op']) > 0.99 for r in none['revealed']),
      f"reveal class {none['revealClass']}, opacity {[r['op'] for r in none['revealed']]}")

reduced = run('anim-reduced', overrides=WITH_PHOTO, still=False,
              flags=('--force-prefers-reduced-motion',))
check('someone who has asked for less motion gets the section already in place',
      all(float(r['op']) > 0.99 for r in reduced['revealed']),
      f"opacity {[r['op'] for r in reduced['revealed']]}")

# The check above passes through the script's own matchMedia branch, so on its
# own it says nothing about the stylesheet. Taking customElements away stops
# the script before it defines anything, which leaves the CSS as the only
# thing standing between a reduced-motion visitor and an empty panel.
css_only = run('anim-reduced-css', overrides=WITH_PHOTO, still=False,
               flags=('--force-prefers-reduced-motion',),
               sabotage='delete window.customElements;')
check('and gets it from the stylesheet even if the script never runs at all',
      css_only['revealClass'] is True
      and all(float(r['op']) > 0.99 for r in css_only['revealed']),
      f"reveal class still {css_only['revealClass']}, "
      f"opacity {[r['op'] for r in css_only['revealed']]}")
check('and the pills keep the transform that is their position, not their motion',
      abs(reduced['pills'][0]['box']['l'] + reduced['pills'][0]['box']['w'] / 2
          - (reduced['media']['box']['l'] + 0.74 * reduced['media']['box']['w'])) <= 4,
      f"pill centre "
      f"{round(reduced['pills'][0]['box']['l'] + reduced['pills'][0]['box']['w'] / 2)}"
      f" against 74% of the photo")

blind = run('anim-blind', overrides=WITH_PHOTO, still=False,
            sabotage='delete window.IntersectionObserver;')
check('a browser with no IntersectionObserver gets the words, not an empty panel',
      blind['revealClass'] is False
      and all(float(r['op']) > 0.99 for r in blind['revealed']),
      f"reveal class {blind['revealClass']}, "
      f"opacity {[r['op'] for r in blind['revealed']]}")

broken = run('anim-broken', overrides=WITH_PHOTO, still=False,
             sabotage='Object.defineProperty(window,"IntersectionObserver",'
                      '{get:function(){throw new Error("boom");}});')
check('and so does one where setting the observer up throws',
      broken['revealClass'] is False
      and all(float(r['op']) > 0.99 for r in broken['revealed']),
      f"reveal class {broken['revealClass']}, "
      f"opacity {[r['op'] for r in broken['revealed']]}")
check('the section lays out the same way when the animation stands down',
      blind['fig']['box']['l'] < blind['panel']['box']['r']
      and blind['media']['box']['t'] < blind['panel']['box']['t'],
      f"figure starts {blind['fig']['box']['l']}, panel ends {blind['panel']['box']['r']}")

# The noscript block cannot be measured in a browser that runs the probe, so
# this is a check on the file, and says so.
source = SECTION.read_text(encoding='utf-8')
check('and the file carries a noscript rule for a browser that runs no script',
      '<noscript>' in source
      and '.hp-ai--reveal [data-reveal] { opacity: 1; }' in source,
      'noscript restores opacity on [data-reveal] (source check, not a render)')

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
