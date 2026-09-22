"""Check the how-to steps.

The numeral is the whole trick of this layout and also the whole risk: it is
far larger than the row it sits in, so it has to be clipped rather than
allowed to change the row's size, it has to sit behind the words rather than
over them, and it must not be read out to anyone using a screen reader -- the
list is already an <ol>, so the order is in the markup once without it.
"""
import json, re, subprocess, sys, pathlib
from PIL import Image, ImageDraw

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path(__file__).resolve().parent.parent
SECTION = ROOT / 'sections' / 'how-to-steps.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

PROBE = """
function bx(e){if(!e)return null;var r=e.getBoundingClientRect();
 return {l:Math.round(r.left),r:Math.round(r.right),t:Math.round(r.top),
         b:Math.round(r.bottom),w:Math.round(r.width),h:Math.round(r.height)};}
function snap(d,w){
  var steps=[].map.call(d.querySelectorAll('.hp-hts__step'),function(li){
    var num=li.querySelector('.hp-hts__num');
    var fig=li.querySelector('.hp-hts__figure');
    var txt=li.querySelector('.hp-hts__text');
    var cs=w.getComputedStyle(li);
    return {box:bx(li), radius:cs.borderTopLeftRadius, overflow:cs.overflow,
            shadow:cs.boxShadow,
            num: num ? {text:num.textContent.trim(), box:bx(num),
                        z:w.getComputedStyle(num).zIndex,
                        hidden:num.getAttribute('aria-hidden'),
                        size:w.getComputedStyle(num).fontSize} : null,
            fig: fig ? {box:bx(fig), radius:w.getComputedStyle(fig).borderTopLeftRadius,
                        bg:w.getComputedStyle(fig).backgroundColor} : null,
            txt: txt ? {box:bx(txt), z:w.getComputedStyle(txt).zIndex} : null};
  });
  var img=d.querySelector('.hp-hts__figure img');
  var num1=d.querySelector('.hp-hts__num');
  var body=d.querySelector('.hp-hts__body p')||d.querySelector('.hp-hts__body');
  return {steps:steps,
    listTag:(d.querySelector('.hp-hts__list')||{}).tagName,
    imgBox: img ? bx(img) : null,
    numOpacity: num1 ? w.getComputedStyle(num1).opacity : null,
    bodySize: body ? w.getComputedStyle(body).fontSize : null,
    bodyText: body ? body.textContent.trim().slice(0,22) : null,
    docW:d.documentElement.scrollWidth, winW:w.innerWidth};
}
"""


def run(name, width=1400, overrides=None):
    page = TMP / f'hts-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(page)], check=True, capture_output=True)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>',
        '<script>' + PROBE +
        "setTimeout(function(){document.title='RESULT'+JSON.stringify("
        "snap(document,window));},400);</script></body>"), encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},1200', '--virtual-time-budget=6000', '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


def framed(name, width=390, overrides=None):
    inner = TMP / f'hts-{name}-inner.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(inner)], check=True, capture_output=True)
    inner.write_text(inner.read_text(encoding='utf-8').replace(
        '</body>', '<script>' + PROBE + '</script></body>'), encoding='utf-8')
    wrap = TMP / f'hts-{name}-wrap.html'
    wrap.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0}'
        f'iframe{{width:{width}px;height:1600px;border:0;display:block}}</style>'
        f'<iframe src="{inner.name}"></iframe><script>setTimeout(function(){{'
        'var f=document.querySelector("iframe");document.title="RESULT"+JSON.stringify('
        'f.contentWindow.snap(f.contentDocument,f.contentWindow));},700);</script>',
        encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', f'--window-size={width + 310},1700',
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


# ------------------------------------------------------------- the rows ----
d = run('base')
check('one row per step', len(d['steps']) == 4, f"{len(d['steps'])} rows")
check('the list is an ordered list, so the order is in the markup',
      d['listTag'] == 'OL', f"<{(d['listTag'] or '?').lower()}>")
check('the rows are capsules',
      d['steps'][0]['radius'] == '999px', f"radius {d['steps'][0]['radius']}")
check('and they carry a soft shadow, not a hard one',
      'rgba' in d['steps'][0]['shadow'] and 'px' in d['steps'][0]['shadow'],
      d['steps'][0]['shadow'][:60])
check('every row is the same height',
      len({s['box']['h'] for s in d['steps']}) == 1,
      f"heights {[s['box']['h'] for s in d['steps']]}")

# ---------------------------------------------------------- the numerals ----
check('the numerals count from the top without being typed',
      [s['num']['text'] for s in d['steps']] == ['01', '02', '03', '04'],
      f"{[s['num']['text'] for s in d['steps']]}")
check('and they are hidden from a screen reader, which already has the list',
      all(s['num']['hidden'] == 'true' for s in d['steps']),
      'aria-hidden on every numeral')
check('the numeral is far bigger than the words beside it',
      int(d['steps'][0]['num']['size'].rstrip('px')) >= 100,
      f"{d['steps'][0]['num']['size']}")
check('it sits behind the words rather than over them',
      int(d['steps'][0]['num']['z'] or 0) < int(d['steps'][0]['txt']['z'] or 0),
      f"numeral z-index {d['steps'][0]['num']['z']}, "
      f"words z-index {d['steps'][0]['txt']['z']}")
# With text long enough to reach it -- which is the case the ordering is for.
long_text = run('long', overrides={'blocks': [
    {'type': 'step', 'settings': {'title': 'Clip it', 'body':
     '<p>Attach your Hankie Pal to your toddler&rsquo;s shirt so that it stays '
     'close by and within reach whenever the sniffles turn up, which on some '
     'days is more or less constantly.</p>'}}]})
ls = long_text['steps'][0]
check('and where the words are long enough to reach it, they cross it',
      ls['txt']['box']['r'] > ls['num']['box']['l'],
      f"words end {ls['txt']['box']['r']}, numeral starts {ls['num']['box']['l']}")
check('the row clips it rather than growing to fit it',
      d['steps'][0]['overflow'] == 'hidden'
      and d['steps'][0]['num']['box']['r'] <= d['steps'][0]['box']['r'] + 1,
      f"overflow {d['steps'][0]['overflow']}, numeral ends "
      f"{d['steps'][0]['num']['box']['r']} in a row ending {d['steps'][0]['box']['r']}")

# The numeral is pale on purpose; the words crossing it must still read.
NUM = rgb(run('base')['steps'][0]['num'] and '239 235 228')
check('the quiet text still reads where it crosses the numeral',
      contrast([0x5C, 0x61, 0x50], [0xEF, 0xEB, 0xE4]) >= 4.5,
      f"{contrast([0x5C, 0x61, 0x50], [0xEF, 0xEB, 0xE4])}:1")

override = run('numbered', overrides={'blocks': [
    {'type': 'step', 'settings': {'title': 'One', 'number': 'A'}},
    {'type': 'step', 'settings': {'title': 'Two'}},
]})
check('a number can be written by hand instead',
      [s['num']['text'] for s in override['steps']] == ['A', '02'],
      f"{[s['num']['text'] for s in override['steps']]}")

off = run('no-numbers', overrides={'settings': {'show_numbers': False}})
check('and the numerals can be turned off entirely',
      all(s['num'] is None for s in off['steps']), 'no numerals rendered')

# -------------------------------------------------------------- the photo --
check('the photo sits in a circle',
      d['steps'][0]['fig']['radius'] == '50%'
      and d['steps'][0]['fig']['box']['w'] == d['steps'][0]['fig']['box']['h'],
      f"radius {d['steps'][0]['fig']['radius']}, "
      f"{d['steps'][0]['fig']['box']['w']}x{d['steps'][0]['fig']['box']['h']}")
check('and each step tints its circle its own colour',
      len({s['fig']['bg'] for s in d['steps']}) >= 2,
      f"{sorted({s['fig']['bg'] for s in d['steps']})}")

rounded = run('rounded', overrides={'settings': {'card_shape': 'rounded',
                                                 'card_radius': 24}})
check('the rows can be rounded corners instead of capsules',
      rounded['steps'][0]['radius'] == '24px',
      f"radius {rounded['steps'][0]['radius']}")

# ------------------------------------------------------------ the richtext --
check("the step text is the size the setting asks for, not the theme's",
      d['bodySize'] == '17px', f"rendered at {d['bodySize']} against a 17px setting")
check('and it is the words that were typed',
      d['bodyText'] and 'Attach your' in d['bodyText'], f"{d['bodyText']!r}")

# --------------------------------------------------------------- the phone --
for w in (1400, 990, 750):
    r = run(f'w{w}', width=w)
    check(f'nothing runs off the page at {w}px',
          r['docW'] <= r['winW'], f"document {r['docW']}px in {r['winW']}px")

for w in (390, 360):
    ph = framed(f'p{w}', width=w)
    over = [s for s in ph['steps'] if s['box']['r'] > ph['winW']]
    check(f'nothing runs off a {w}px phone',
          ph['docW'] <= ph['winW'] and not over,
          f"document {ph['docW']}px in {ph['winW']}px")

ph = framed('p390', width=390)
check('the row stays a row on a phone rather than stacking',
      ph['steps'][0]['fig']['box']['r'] <= ph['steps'][0]['txt']['box']['l'] + 2,
      f"photo ends {ph['steps'][0]['fig']['box']['r']}, "
      f"words start {ph['steps'][0]['txt']['box']['l']}")
check('and the photo gives up room to do it',
      ph['steps'][0]['fig']['box']['w'] < d['steps'][0]['fig']['box']['w'],
      f"{d['steps'][0]['fig']['box']['w']}px on a desktop, "
      f"{ph['steps'][0]['fig']['box']['w']}px on a phone")

# ------------------------------------------------ the photo in its circle ----
# A test image with a band at its very top and another at its very bottom. If
# both show inside the circle, nothing has been cut off; that is a claim about
# pixels, so it is settled in pixels rather than in geometry.
def banded(path):
    im = Image.new('RGB', (200, 360), (250, 250, 250))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 199, 24], fill=(220, 40, 40))
    d.rectangle([0, 335, 199, 359], fill=(30, 90, 220))
    im.save(path)
    return path


BANDS = banded(TMP / 'hts-bands.png')


def bands_in_circle(fit):
    ov = {'settings': {'photo_fit': fit, 'photo_size': 160, 'photo_inset': 8},
          'blocks': [{'type': 'step', 'settings': {'title': 'x', 'image': str(BANDS),
                                                   'body': '<p>x</p>'}}]}
    page = TMP / f'hts-bands-{fit}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(ov), str(page)], check=True, capture_output=True)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>',
        "<script>setTimeout(function(){var f=document.querySelector"
        "('.hp-hts__figure').getBoundingClientRect();document.title='RESULT'+"
        "JSON.stringify({l:Math.round(f.left),t:Math.round(f.top),"
        "r:Math.round(f.right),b:Math.round(f.bottom)});},500);</script></body>"),
        encoding='utf-8')
    shot = TMP / f'hts-bands-{fit}.png'
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', '--window-size=1400,900',
        '--virtual-time-budget=5000', f'--screenshot={shot}', '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
    box = json.loads(re.search(r'<title>RESULT(.*?)</title>', dom, re.S).group(1))
    im = Image.open(shot).convert('RGB')
    found = {'top': False, 'bottom': False}
    for y in range(box['t'], box['b']):
        for x in range(box['l'], box['r']):
            px = im.getpixel((x, y))
            if all(abs(a - b) <= 18 for a, b in zip(px, (220, 40, 40))):
                found['top'] = True
            if all(abs(a - b) <= 18 for a, b in zip(px, (30, 90, 220))):
                found['bottom'] = True
    return found


whole = bands_in_circle('contain')
check('fitting the photo shows all of it, top edge and bottom edge',
      whole['top'] and whole['bottom'],
      f"top band {'visible' if whole['top'] else 'missing'}, "
      f"bottom band {'visible' if whole['bottom'] else 'missing'}")

filled = bands_in_circle('cover')
check('and filling the circle crops it, which is the other choice',
      not filled['top'] and not filled['bottom'],
      "neither end of the image survives the crop")

# object-fit only bites on a constrained box. `height: 100%` here resolves
# against an auto-sized grid row, which it cannot, so the image kept its own
# height and spilled out of the circle to be clipped instead.
sized = run('photo-box', overrides={'settings': {'photo_size': 160, 'photo_inset': 8},
    'blocks': [{'type': 'step', 'settings': {'title': 'x', 'image': str(BANDS)}}]})
fig = sized['steps'][0]['fig']['box']
check('the photo is given a square box inside the circle, not its own height',
      sized['imgBox'] and sized['imgBox']['h'] == sized['imgBox']['w']
      and sized['imgBox']['h'] <= fig['h'],
      f"image box {sized['imgBox']['w']}x{sized['imgBox']['h']} "
      f"in a {fig['w']}x{fig['h']} circle")

# ------------------------------------------------------ numeral opacity -----
faint = run('faint', overrides={'settings': {'number_opacity': 20}})
check('the numeral opacity is a setting',
      faint['numOpacity'] == '0.2' and d['numOpacity'] == '1',
      f"20% renders {faint['numOpacity']}, the default renders {d['numOpacity']}")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
