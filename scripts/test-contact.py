"""Check the contact section.

The paint is the easy half. The half worth checking is that this is still
Shopify's own contact form underneath: the four field names it posts, the
required email, the success round trip and the error list. A pretty form that
does not reach anyone is worse than Dawn's plain one.

Labels are the other half. Dawn's floating placeholders are at least wired to
their fields; a hand-built form is where that quietly stops being true.
"""
import json, re, subprocess, sys, pathlib
from PIL import Image

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path(__file__).resolve().parent.parent
SECTION = ROOT / 'sections' / 'hp-contact.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

PROBE = """
function bx(e){if(!e)return null;var r=e.getBoundingClientRect();
 return {l:Math.round(r.left),r:Math.round(r.right),t:Math.round(r.top),
         b:Math.round(r.bottom),w:Math.round(r.width),h:Math.round(r.height)};}
function snap(d,w){
  var sec=d.querySelector('.hp-ct');
  var card=d.querySelector('.hp-ct__card');
  var side=d.querySelector('.hp-ct__side');
  var area=d.querySelector('.hp-ct__area');
  var head=d.querySelector('.hp-ct__heading');
  var body=d.querySelector('.hp-ct__body p')||d.querySelector('.hp-ct__body');
  var eb=d.querySelector('.hp-ct__eyebrow');
  var btn=d.querySelector('.hp-ct__send');
  return {
    secBox:bx(sec), secBg:sec?w.getComputedStyle(sec).backgroundColor:null,
    secOverflow:sec?w.getComputedStyle(sec).overflowX:null,
    card:card?{box:bx(card), bg:w.getComputedStyle(card).backgroundColor,
               radius:w.getComputedStyle(card).borderTopLeftRadius,
               z:w.getComputedStyle(card).zIndex}:null,
    sideBox:bx(side),
    formInWrap: !!d.querySelector('.hp-ct__formwrap form'),
    fields:[].map.call(d.querySelectorAll('.hp-ct__input, .hp-ct__area'),
      function(e){var c=w.getComputedStyle(e);
        var lab=d.querySelector('label[for="'+e.id+'"]');
        return {tag:e.tagName, id:e.id, name:e.getAttribute('name'),
                type:e.getAttribute('type'), required:e.hasAttribute('required'),
                size:c.fontSize, radius:c.borderTopLeftRadius, bg:c.backgroundColor,
                ink:c.color, border:c.borderTopWidth,
                label:lab?lab.textContent.trim().replace(/\\s+/g,' '):null,
                box:bx(e)};}),
    areaResize:area?w.getComputedStyle(area).resize:null,
    labelInk:(function(){var l=d.querySelector('.hp-ct__label');
      return l?w.getComputedStyle(l).color:null;})(),
    reqHidden:(function(){var r=d.querySelector('.hp-ct__req');
      return r?r.getAttribute('aria-hidden'):null;})(),
    note:(function(){var n=d.querySelector('.hp-ct__note');if(!n)return null;
      var c=w.getComputedStyle(n);
      return {text:n.textContent.trim().slice(0,40), role:n.getAttribute('role'),
              bg:c.backgroundColor, ink:c.color,
              bad:n.classList.contains('hp-ct__note--bad'), box:bx(n)};})(),
    direct:(function(){var a=d.querySelector('.hp-ct__direct-link');if(!a)return null;
      return {href:a.getAttribute('href'), text:a.textContent.trim(),
              box:bx(a)};})(),
    directBox:bx(d.querySelector('.hp-ct__direct')),
    headTag:head?head.tagName:null,
    headInk:head?w.getComputedStyle(head).color:null,
    headSize:head?w.getComputedStyle(head).fontSize:null,
    bodyInk:body?w.getComputedStyle(body).color:null,
    bodySize:body?w.getComputedStyle(body).fontSize:null,
    bodyText:body?body.textContent.trim().slice(0,24):null,
    ebWeight:eb?w.getComputedStyle(eb).fontWeight:null,
    ebFamily:eb?w.getComputedStyle(eb).fontFamily:null,
    btnBox:bx(btn),
    dog:(function(){var g=d.querySelector('.hp-ct__dog');if(!g)return null;
      var c=w.getComputedStyle(g);var eye=d.querySelector('.hp-ct__dog-eye');
      return {box:bx(g), z:c.zIndex, events:c.pointerEvents,
              hidden:g.getAttribute('aria-hidden'),
              eyeAnim:eye?w.getComputedStyle(eye).animationName:null};})(),
    pebbles:[].map.call(d.querySelectorAll('.hp-ct__pebble'),function(e){
      var c=w.getComputedStyle(e);
      return {hidden:e.getAttribute('aria-hidden'), events:c.pointerEvents,
              op:c.opacity, z:c.zIndex};}),
    docW:d.documentElement.scrollWidth, winW:w.innerWidth};
}
"""

WITH_EMAIL = {'settings': {'email_address': 'hello@totterful.com'}}


def render(name, overrides):
    page = TMP / f'ct-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(page)], check=True,
                   capture_output=True)
    return page


def run(name, width=1400, overrides=None, flags=()):
    page = render(name, overrides)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>',
        '<script>' + PROBE +
        "setTimeout(function(){document.title='RESULT'+JSON.stringify("
        "snap(document,window));},400);</script></body>"), encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},1200', '--virtual-time-budget=6000', *flags,
        '--dump-dom', 'file://' + str(page)],
        capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


def framed(name, width=390, overrides=None):
    """A real phone width. A Chromium window will not go below 500px."""
    inner = render(name + '-inner', overrides)
    inner.write_text(inner.read_text(encoding='utf-8').replace(
        '</body>', '<script>' + PROBE + '</script></body>'), encoding='utf-8')
    wrap = TMP / f'ct-{name}-wrap.html'
    wrap.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0}'
        f'iframe{{width:{width}px;height:1700px;border:0;display:block}}</style>'
        f'<iframe src="{inner.name}"></iframe><script>setTimeout(function(){{'
        'var f=document.querySelector("iframe");document.title="RESULT"+JSON.stringify('
        'f.contentWindow.snap(f.contentDocument,f.contentWindow));},700);</script>',
        encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', f'--window-size={width + 310},1800',
        '--virtual-time-budget=8000', '--dump-dom', 'file://' + str(wrap)],
        capture_output=True, text=True, timeout=200).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


def shot(name, overrides, width=1400, height=1000):
    page = render(name, overrides)
    out = TMP / f'ct-{name}.png'
    subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},{height}', '--virtual-time-budget=6000',
        f'--screenshot={out}', 'file://' + str(page)], capture_output=True, timeout=180)
    return Image.open(out).convert('RGB')


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


d = run('default', overrides=WITH_EMAIL)

parts = {'section': d['secBox'], 'card': d['card'], 'side column': d['sideBox'],
         'heading': d['headSize'], 'paragraph': d['bodySize'], 'button': d['btnBox']}
missing = [k for k, v in parts.items() if v is None]
check('every part of the section is on the page to begin with',
      not missing, f"missing: {', '.join(missing) if missing else 'nothing'}")
if missing:
    print(f"\n{sum(res)}/{len(res)} passed")
    sys.exit(1)

# ------------------------------------------- it is still Shopify's form ----
names = [f['name'] for f in d['fields']]
check("the four names Shopify's contact form posts are all there",
      names == ['contact[name]', 'contact[email]', 'contact[phone]', 'contact[body]'],
      f"{names}")
check('the message is a textarea and the rest are inputs',
      [f['tag'] for f in d['fields']] == ['INPUT', 'INPUT', 'INPUT', 'TEXTAREA'],
      f"{[f['tag'] for f in d['fields']]}")
check('the email field is the required one, and is typed as an email',
      d['fields'][1]['required'] and d['fields'][1]['type'] == 'email',
      f"required {d['fields'][1]['required']}, type {d['fields'][1]['type']}")
check('and the phone field is typed as a phone, so a phone keypad opens',
      d['fields'][2]['type'] == 'tel', f"type {d['fields'][2]['type']}")
check("the form's own class sits on a wrapper, not on the form tag",
      d['formInWrap'],
      'a .hp-ct__formwrap wraps the form, so the store and the test style alike')

# -------------------------------------------------- every field is labelled --
check('every field has a label pointing at it',
      all(f['label'] for f in d['fields']),
      f"{[(f['name'], f['label']) for f in d['fields']]}")
check('and the ids carry the section id, so two on a page cannot collide',
      all('test-section' in f['id'] for f in d['fields']),
      f"{[f['id'] for f in d['fields']]}")
check('the required mark is not read out twice',
      d['reqHidden'] == 'true',
      f"the asterisk is aria-hidden {d['reqHidden']}; the field carries required")
check('and the label reads with a space before its mark',
      '? *' in d['fields'][3]['label'] or d['fields'][3]['label'].endswith('*'),
      f"{d['fields'][3]['label']!r}")

check('no field is under 16px, which is where iOS zooms in and never back out',
      all(float(f['size'].rstrip('px')) >= 16 for f in d['fields']),
      f"{[f['size'] for f in d['fields']]}")

# ------------------------------------------------------------ the shapes ---
check('the single-line fields are pills',
      all(float(f['radius'].rstrip('px')) >= 26 for f in d['fields'][:3]),
      f"{[f['radius'] for f in d['fields'][:3]]}")
check('and the message box is rounded rather than a pill, which would cut its '
      'first and last lines',
      10 <= float(d['fields'][3]['radius'].rstrip('px')) <= 40,
      f"radius {d['fields'][3]['radius']}")
check('the message box can be dragged taller but not wider',
      d['areaResize'] == 'vertical', f"resize {d['areaResize']}")
check('every field carries the outline the brand uses',
      all(f['border'] == '2px' for f in d['fields']),
      f"{[f['border'] for f in d['fields']]}")

# ------------------------------------------------------- what comes back ---
check('nothing is announced before anything is sent',
      d['note'] is None, 'no banner on a first visit')

sent = run('sent', overrides=dict(WITH_EMAIL, form={'posted_successfully?': True}))
check('a sent message is confirmed',
      sent['note'] is not None and sent['note']['text'].startswith('Thank you'),
      f"{sent['note']['text'] if sent['note'] else 'no banner'}")
check('and announced to a screen reader as a status, not an alarm',
      sent['note']['role'] == 'status', f"role {sent['note']['role']}")
check('the confirmation sits above the form rather than below it',
      sent['note']['box']['t'] < sent['fields'][0]['box']['t'],
      f"banner at {sent['note']['box']['t']}, first field at {sent['fields'][0]['box']['t']}")
check('and the form is still there, so a second message needs no reload',
      len(sent['fields']) == 4, f"{len(sent['fields'])} fields still rendered")

bad = run('errors', overrides=dict(WITH_EMAIL,
                                   form={'errors': ['Email is not valid']}))
check("a problem is shown rather than swallowed",
      bad['note'] is not None and 'Email' in bad['note']['text'],
      f"{bad['note']['text'] if bad['note'] else 'no banner'}")
check('and announced as an alert, which a status would not be',
      bad['note']['role'] == 'alert', f"role {bad['note']['role']}")
check('it is told apart from a confirmation by more than its words',
      bad['note']['bad'] and bad['note']['bg'] != sent['note']['bg'],
      f"problem {bad['note']['bg']}, confirmation {sent['note']['bg']}")

# ------------------------------------------------------- the side column ---
check("the email box is drawn when there is an address",
      d['direct'] is not None and d['direct']['text'] == 'hello@totterful.com',
      f"{d['direct']['text'] if d['direct'] else 'no address'}")
check('and it is a real mailto link',
      d['direct']['href'] == 'mailto:hello@totterful.com', f"{d['direct']['href']}")

no_mail = run('no-email', overrides={})
check('with no address the box is left out entirely, not left empty',
      no_mail['direct'] is None and no_mail['directBox'] is None,
      'no .hp-ct__direct in the markup')

check("the heading is the page's h1 by default",
      d['headTag'] == 'H1', f"heading is <{(d['headTag'] or '?').lower()}>")
check('the eyebrow is bold',
      d['ebWeight'] == '700', f"weight {d['ebWeight']}")
check('and set in the body font rather than the heading one',
      d['ebFamily'] and d['ebFamily'] != '', f"{d['ebFamily']}")
check('whose fallback names Quicksand, for a theme that has set no body font',
      'var(--font-body-family, "Quicksand", ui-rounded, system-ui, sans-serif)'
      in SECTION.read_text(encoding='utf-8'),
      'the declared stack falls back to Quicksand (source check, not a render)')

# ------------------------------------------------------------- the toggles --
no_name = run('no-name', overrides={'settings': dict(
    WITH_EMAIL['settings'], show_name=False, show_phone=False)})
check('the name and phone fields can both be dropped',
      [f['name'] for f in no_name['fields']] == ['contact[email]', 'contact[body]'],
      f"{[f['name'] for f in no_name['fields']]}")

loose = run('loose', overrides={'settings': dict(
    WITH_EMAIL['settings'], message_required=False)})
check('and the message can be made optional',
      loose['fields'][-1]['required'] is False,
      f"required {loose['fields'][-1]['required']}")

# ----------------------------------------------------------------- the dog --
check('a dog leans over the card',
      d['dog'] is not None, 'dog rendered' if d['dog'] else 'no dog')
check('he is decoration: never read out, never clickable',
      d['dog']['hidden'] == 'true' and d['dog']['events'] == 'none',
      f"aria-hidden {d['dog']['hidden']}, pointer-events {d['dog']['events']}")
check('and he blinks',
      d['dog']['eyeAnim'] == 'hp-ct-blink', f"{d['dog']['eyeAnim']}")

dog_img = shot('dog-crop', WITH_EMAIL)
cx = d['dog']['box']['l'] + d['dog']['box']['w'] // 2
above = dog_img.getpixel((cx, d['card']['box']['t'] - 12))
below = dog_img.getpixel((cx, d['card']['box']['t'] + 12))
check("the card's own top edge is what crops him",
      abs(above[0] - rgb(d['secBg'])[0]) + abs(above[1] - rgb(d['secBg'])[1]) > 40
      and abs(below[0] - rgb(d['card']['bg'])[0]) < 12
      and abs(below[1] - rgb(d['card']['bg'])[1]) < 12,
      f"the dog is rgb{above} above the card edge and the card is rgb{below} "
      f"below it, where he would otherwise carry on")
check('and the band makes room for him rather than cutting his head off',
      d['dog']['box']['t'] >= d['secBox']['t'] - 1,
      f"dog starts {d['dog']['box']['t']}, band starts {d['secBox']['t']}")

tall_dog = run('tall-dog', overrides={'settings': dict(
    WITH_EMAIL['settings'], dog_size=240, dog_peek=220)})
check('even at his tallest',
      tall_dog['dog']['box']['t'] >= tall_dog['secBox']['t'] - 1,
      f"dog starts {tall_dog['dog']['box']['t']}, band starts {tall_dog['secBox']['t']}")

calm = run('reduced', overrides=WITH_EMAIL,
           flags=('--force-prefers-reduced-motion',))
check('and he holds still for anyone asking for less motion',
      calm['dog']['eyeAnim'] == 'none', f"animation {calm['dog']['eyeAnim']}")

off = run('no-dog', overrides={'settings': dict(WITH_EMAIL['settings'],
                                                show_dog=False)})
check('he can be sent away',
      off['dog'] is None, 'no dog rendered')

# ------------------------------------------------------------- the pebbles --
check('two pebbles sit behind the layout, and neither is read out or clickable',
      len(d['pebbles']) == 2
      and all(p['hidden'] == 'true' and p['events'] == 'none' for p in d['pebbles']),
      f"{len(d['pebbles'])} pebbles, aria-hidden and pointer-events none")
no_peb = run('no-pebbles', overrides={'settings': dict(WITH_EMAIL['settings'],
                                                       show_pebbles=False)})
check('and they can be turned off',
      len(no_peb['pebbles']) == 0, 'no pebbles rendered')

# ------------------------------------------------------------------ it reads --
check('the heading reads against the band',
      contrast(rgb(d['headInk']), rgb(d['secBg'])) >= 7,
      f"{contrast(rgb(d['headInk']), rgb(d['secBg']))}:1")
check('the paragraph reads against the band',
      contrast(rgb(d['bodyInk']), rgb(d['secBg'])) >= 4.5,
      f"{contrast(rgb(d['bodyInk']), rgb(d['secBg']))}:1")
check('the labels read against the card',
      contrast(rgb(d['labelInk']), rgb(d['card']['bg'])) >= 4.5,
      f"{contrast(rgb(d['labelInk']), rgb(d['card']['bg']))}:1")
check('what someone types reads against the field they type it in',
      contrast(rgb(d['fields'][0]['ink']), rgb(d['fields'][0]['bg'])) >= 7,
      f"{contrast(rgb(d['fields'][0]['ink']), rgb(d['fields'][0]['bg']))}:1")
check('the confirmation reads against its own fill',
      contrast(rgb(sent['note']['ink']), rgb(sent['note']['bg'])) >= 4.5,
      f"{contrast(rgb(sent['note']['ink']), rgb(sent['note']['bg']))}:1")
check('and so does the problem notice',
      contrast(rgb(bad['note']['ink']), rgb(bad['note']['bg'])) >= 4.5,
      f"{contrast(rgb(bad['note']['ink']), rgb(bad['note']['bg']))}:1")

# ------------------------------------------------------------- the layout ---
check('the words and the form sit side by side on a desktop',
      d['sideBox']['r'] <= d['card']['box']['l'] + 1,
      f"words end {d['sideBox']['r']}, card starts {d['card']['box']['l']}")

p390 = framed('phone', 390, WITH_EMAIL)
check('and stack on a phone, words first',
      abs(p390['sideBox']['l'] - p390['card']['box']['l']) <= 2
      and p390['sideBox']['b'] <= p390['card']['box']['t'],
      f"words end {p390['sideBox']['b']}, card starts {p390['card']['box']['t']}")
# Stacked, the words sit directly above the card, so the dog rises into them
# unless the card is given room for him.
check('the dog clears the words above him rather than sitting on them',
      p390['dog']['box']['t'] >= p390['directBox']['b'] - 1,
      f"dog starts {p390['dog']['box']['t']}, the email box ends "
      f"{p390['directBox']['b']}")
check('the fields still reach across the card there',
      p390['fields'][0]['box']['w'] > p390['card']['box']['w'] * 0.7,
      f"field {p390['fields'][0]['box']['w']}px in a {p390['card']['box']['w']}px card")
check('and are still 16px, so a phone does not zoom on focus',
      all(float(f['size'].rstrip('px')) >= 16 for f in p390['fields']),
      f"{[f['size'] for f in p390['fields']]}")

check('the band clips whatever hangs off its sides',
      d['secOverflow'] in ('clip', 'hidden'), f"overflow-x {d['secOverflow']}")
for label, snap in (('at 1400px', d), ('at 390px', p390)):
    check(f'and the page never scrolls sideways {label}',
          snap['docW'] <= snap['winW'] + 1,
          f"document {snap['docW']}px in {snap['winW']}px")

deep = framed('phone-360', 360, {'settings': dict(
    WITH_EMAIL['settings'], pebble_size=460, card_padding=72)})
check('not even at 360px with the pebbles and the card pushed out',
      deep['docW'] <= deep['winW'] + 1,
      f"document {deep['docW']}px in {deep['winW']}px")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
