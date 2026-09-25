"""Check the footer: that its links are real links, that it reads at every
width, and that it can only be installed where it renders on every page.

The last one is the whole point of the section. A footer that looks right but
was added to one template is the failure this is built to prevent, and it is
invisible from the page itself — so it is checked in the schema.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
SECTION = ROOT / 'sections' / 'hp-footer.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

# main-menu has three links in the renderer's stub, footer has two.
THREE = {'blocks': [
    {'type': 'menu', 'settings': {'title': 'Shop', 'menu': 'main-menu'}},
    {'type': 'menu', 'settings': {'title': 'Help', 'menu': 'footer'}},
    {'type': 'menu', 'settings': {'title': 'About', 'menu': 'main-menu'}}]}
EXPECTED_MENU_LINKS = 3 + 2 + 3
EXPECTED_POLICIES = 3

PROBE = """<script>
function box(el) {
  var r = el.getBoundingClientRect();
  return { l: Math.round(r.left), r: Math.round(r.right),
           t: Math.round(r.top), b: Math.round(r.bottom),
           w: Math.round(r.width), h: Math.round(r.height) };
}

setTimeout(function () {
  var ft = document.querySelector('.hp-ft');
  var cols = document.querySelector('.hp-ft__cols');
  var brand = document.querySelector('.hp-ft__brand');
  var legal = document.querySelector('.hp-ft__legal');
  var copy = document.querySelector('.hp-ft__copy');
  var links = [].map.call(document.querySelectorAll('.hp-ft__cols .hp-ft__link'),
    function (a) { return { href: a.getAttribute('href'), text: a.textContent.trim(),
                            box: box(a) }; });

  document.title = 'RESULT' + JSON.stringify({
    menuLinks: links,
    policyLinks: legal ? [].map.call(legal.querySelectorAll('a'), function (a) {
      return a.getAttribute('href'); }) : null,
    emptyLists: document.querySelectorAll('.hp-ft__list:empty').length,
    pay: document.querySelectorAll('.hp-ft__pay').length,
    colCount: cols ? getComputedStyle(cols).gridTemplateColumns.split(' ').length : 0,
    colTracks: cols ? getComputedStyle(cols).gridTemplateColumns : null,
    brand: brand ? box(brand) : null,
    cols: cols ? box(cols) : null,
    copy: copy ? box(copy) : null,
    legalBox: legal ? box(legal) : null,
    bg: getComputedStyle(ft).backgroundColor,
    linkInk: links.length ? getComputedStyle(
      document.querySelector('.hp-ft__cols .hp-ft__link')).color : null,
    titleInk: getComputedStyle(document.querySelector('.hp-ft__col-title')).color,
    copyInk: copy ? getComputedStyle(copy).color : null,
    pebbles: [].map.call(document.querySelectorAll('.hp-ft__pebble'), function (e) {
      var c = getComputedStyle(e);
      return { display: c.display, bg: c.backgroundColor, op: c.opacity,
               radius: c.borderTopLeftRadius, z: c.zIndex, box: box(e) };
    }),
    pebbleLayer: (function () {
      var w = document.querySelector('.hp-ft__pebbles');
      var inner = document.querySelector('.hp-ft__inner');
      if (!w || !inner) return null;
      return { wrap: getComputedStyle(w).zIndex,
               inner: getComputedStyle(inner).zIndex,
               events: getComputedStyle(w).pointerEvents };
    })(),
    ftOverflow: getComputedStyle(ft).overflowX,
    ftImage: getComputedStyle(ft).backgroundImage,
    ftSize: getComputedStyle(ft).backgroundSize,
    ftRepeat: getComputedStyle(ft).backgroundRepeat,
    social: [].map.call(document.querySelectorAll('.hp-ft__social-link'), function (e) {
      return { tag: e.tagName, href: e.getAttribute('href'),
               name: (e.querySelector('.hp-ft__sr') || {}).textContent || null,
               hidden: e.getAttribute('aria-hidden'),
               border: getComputedStyle(e).borderTopWidth,
               ink: getComputedStyle(e).color,
               box: box(e) };
    }),
    socialBox: (function () {
      var u = document.querySelector('.hp-ft__social');
      return u ? box(u) : null;
    })(),
    bottomBox: (function () {
      var b = document.querySelector('.hp-ft__bottom');
      return b ? box(b) : null;
    })(),
    docW: document.documentElement.scrollWidth,
    winW: window.innerWidth
  });
}, 500);
</script>"""


def run(overrides, name, width=1280):
    page = TMP / f'ft-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>'),
                    encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},900', '--virtual-time-budget=3000', '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def rgb(s):
    return [int(x) for x in re.findall(r'\d+', s)[:3]]


def contrast(a, b):
    def lum(c):
        c = [x / 255 for x in c]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return round((l1 + 0.05) / (l2 + 0.05), 2)


# ------------------------------------------------- where it can be installed --
src = SECTION.read_text(encoding='utf-8')
schema = json.loads(re.search(r'{% schema %}(.*?){% endschema %}', src, re.S).group(1))
check('it can only be added to the footer group, so it cannot end up on one page',
      schema.get('enabled_on', {}).get('groups') == ['footer'],
      f"enabled_on: {schema.get('enabled_on')}")
check('and it has a preset, or the editor will not offer it at all',
      bool(schema.get('presets')),
      f"{len(schema.get('presets', []))} preset(s): "
      f"{[p.get('name') for p in schema.get('presets', [])]}")
check('the links come from Shopify menus rather than being typed in here',
      all(r['type'] == 'link_list' for b in schema['blocks'] for r in b['settings']
          if r['id'] == 'menu'),
      'the block takes a link_list, edited in Content → Menus')

# ------------------------------------------------------------------ links ----
d = run(THREE, 'wide')
check('every menu link renders, with a real href',
      len(d['menuLinks']) == EXPECTED_MENU_LINKS
      and all(l['href'] and l['text'] for l in d['menuLinks']),
      f"{len(d['menuLinks'])} links: "
      + ', '.join(f"{l['text']} → {l['href']}" for l in d['menuLinks'][:4]) + ' …')
check('the policy links come through on their own',
      d['policyLinks'] and len(d['policyLinks']) == EXPECTED_POLICIES
      and all('/policies/' in h for h in d['policyLinks']),
      f"{d['policyLinks']}")
off = run(dict(THREE, settings={'show_policies': False}), 'nopolicy')
check('and can be turned off',
      not off['policyLinks'], f"legal row present: {off['policyLinks'] is not None}")
check('payment icons stay off unless asked for',
      d['pay'] == 0, f"{d['pay']} icon rows")
empty = run({'blocks': [{'type': 'menu', 'settings': {'title': 'Shop'}}]}, 'emptymenu')
check('a column with no menu chosen yet renders no empty list',
      empty['emptyLists'] == 0 and len(empty['menuLinks']) == 0,
      f"{empty['emptyLists']} empty lists")

# ----------------------------------------------------------------- layout ----
check('the brand sits left of the link columns',
      d['brand']['r'] <= d['cols']['l'],
      f"brand ends {d['brand']['r']}, columns start {d['cols']['l']}")
check('one column track per block',
      d['colCount'] == 3, f"{d['colTracks']}")
two = run({'blocks': THREE['blocks'][:2]}, 'two')
check('and two blocks give two, not a gap where the third was',
      two['colCount'] == 2, f"{two['colTracks']}")
check('the bottom row does not overlap itself',
      d['copy']['r'] <= d['legalBox']['l'] or d['copy']['b'] <= d['legalBox']['t'],
      f"copyright {d['copy']['l']}–{d['copy']['r']}, policies {d['legalBox']['l']}–"
      f"{d['legalBox']['r']}")

for w in (1440, 1280, 990, 750, 500):
    n = run(THREE, f'w{w}', width=w)
    over = n['docW'] - n['winW']
    check(f'nothing runs off the edge at {w}px',
          over <= 0, f"document {n['docW']}px in {n['winW']}px")

phone = run(THREE, 'phone', width=500)
check('the columns go two up on a phone rather than however many blocks there are',
      phone['colCount'] == 2, f"{phone['colTracks']}")
check('the brand stacks above them',
      phone['brand']['b'] <= phone['cols']['t'],
      f"brand ends {phone['brand']['b']}, columns start {phone['cols']['t']}")
# 24px is the minimum target size in WCAG 2.5.8, and an inline link is the
# height of its text — so this is a real risk in any footer, not a formality.
check('links are at least a 24px target to tap',
      min(l['box']['h'] for l in phone['menuLinks']) >= 24,
      f"smallest link is {min(l['box']['h'] for l in phone['menuLinks'])}px tall")

# --------------------------------------------------------------- contrast ----
bg = rgb(d['bg'])
for label, key, floor in (('links', 'linkInk', 4.5), ('column headings', 'titleInk', 4.5),
                          ('the copyright line', 'copyInk', 4.5)):
    c = contrast(rgb(d[key]), bg)
    check(f'{label} clear {floor}:1 on the background', c >= floor, f"{c}:1")

# ------------------------------------------------------------- the pebbles --
d = run({}, 'pebbles')
check('two pebbles sit in the band',
      len(d['pebbles']) == 2, f"{len(d['pebbles'])} pebbles")
check('and they wear the brand shape, not a circle',
      all('%' in p['radius'] for p in d['pebbles']),
      f"radius {d['pebbles'][0]['radius']}")
check('each takes its own colour',
      d['pebbles'][0]['bg'] != d['pebbles'][1]['bg'],
      f"{d['pebbles'][0]['bg']} and {d['pebbles'][1]['bg']}")
check('they are faint by default, so the words stay first',
      all(float(p['op']) <= 0.5 for p in d['pebbles']),
      f"opacity {[p['op'] for p in d['pebbles']]}")
check('and they sit behind the content, ignoring the mouse',
      d['pebbleLayer']['wrap'] == '0' and d['pebbleLayer']['inner'] == '1'
      and d['pebbleLayer']['events'] == 'none',
      f"pebbles z{d['pebbleLayer']['wrap']}, content z{d['pebbleLayer']['inner']}, "
      f"pointer-events {d['pebbleLayer']['events']}")

faint = run({'settings': {'pebble_opacity': 10}}, 'faint')
check('the opacity is a setting',
      all(abs(float(p['op']) - 0.1) < 0.001 for p in faint['pebbles']),
      f"10% renders {faint['pebbles'][0]['op']}")

hue = run({'settings': {'pebble_color_1': '#D88B6D'}}, 'hue')
check('and so is the colour',
      rgb(hue['pebbles'][0]['bg']) == [216, 139, 109],
      f"{hue['pebbles'][0]['bg']}")

check('the band clips whatever hangs off its sides',
      d['ftOverflow'] in ('clip', 'hidden'), f"overflow-x {d['ftOverflow']}")
check('so a pebble hanging off the edge never widens the page',
      d['docW'] <= d['winW'], f"document {d['docW']}px in {d['winW']}px")

off = run({'settings': {'show_pebbles': False}}, 'no-pebbles')
check('they can be turned off',
      len(off['pebbles']) == 0, 'no pebbles rendered')

small = run({}, 'pebbles-phone', width=500)
check('and they stand down where the columns reach the edges',
      all(p['display'] == 'none' for p in small['pebbles']),
      f"display {[p['display'] for p in small['pebbles']]} at 500px")

# -------------------------------------------------------------- the social --
check('with no link filled in, not one icon shows',
      len(d['social']) == 0, f"{len(d['social'])} icons rendered")
check('and the row itself is gone, not left empty',
      d['socialBox'] is None, 'no .hp-ft__social in the markup')

filled = run({'settings': {'social_instagram': 'https://instagram.com/totterful',
                           'social_tiktok': 'https://tiktok.com/@totterful'}}, 'social')
check('the two links filled in show, and the four blank ones do not',
      len(filled['social']) == 2, f"{len(filled['social'])} icons rendered")
check('and every icon that shows is a real link',
      all(s['tag'] == 'A' and s['href'] and s['hidden'] is None
          for s in filled['social']),
      f"{[(s['tag'], s['href'], s['hidden']) for s in filled['social']]}")
check('and each is named for a screen reader',
      [s['name'] for s in filled['social']] == ['Instagram', 'TikTok'],
      f"{[s['name'] for s in filled['social']]}")
check('they sit at the far end of the bottom row',
      filled['socialBox']['r'] >= filled['bottomBox']['r'] - 2,
      f"social ends {filled['socialBox']['r']}, row ends {filled['bottomBox']['r']}")
check('the icons ride in a circle by default',
      filled['social'][0]['border'] == '1px',
      f"outline {filled['social'][0]['border']}")

plain = run({'settings': {'social_style': 'plain',
                          'social_instagram': 'https://instagram.com/x'}}, 'social-plain')
check('and can be bare glyphs instead',
      plain['social'][0]['border'] == '0px',
      f"outline {plain['social'][0]['border']}")

check('the social icons read against the footer',
      contrast(rgb(filled['social'][0]['ink']), rgb(filled['bg'])) >= 3,
      f"{contrast(rgb(filled['social'][0]['ink']), rgb(filled['bg']))}:1")

hidden = run({'settings': {'show_social': False}}, 'no-social')
check('and the whole row can be turned off',
      len(hidden['social']) == 0, 'no social icons rendered')

# ------------------------------------------------------ the background image --
plain_bg = run({}, 'bg-none')
check('with no image the band draws none',
      plain_bg['ftImage'] == 'none', f"background-image {plain_bg['ftImage']}")

IMG = str(TMP / 'hts-bands.png') if (TMP / 'hts-bands.png').exists() else str(TMP / 'tall.png')
withimg = run({'settings': {'background_image': IMG}}, 'bg-tile')
check('an uploaded image is drawn behind the footer',
      'url(' in withimg['ftImage'], f"{withimg['ftImage'][:60]}")
check('under a wash of the background colour, so the words keep their contrast',
      withimg['ftImage'].count('linear-gradient') == 1,
      'one gradient layer over the picture')
# An opacity that reads nil is the real case: a section saved before the
# setting existed. Passing null makes the renderer hand over nil instead of
# quietly substituting the schema default, which is the only way this can be
# told apart from a working one.
nil_op = run({'settings': {'background_image': IMG, 'background_opacity': None}},
             'bg-nil')
check('an opacity that reads nil shows the image rather than burying it',
      ', 0)' in nil_op['ftImage'] or ', 0.0)' in nil_op['ftImage'],
      f"wash {nil_op['ftImage'].split('url(')[0].strip()[:46]}")

dimmed = run({'settings': {'background_image': IMG, 'background_opacity': 0}}, 'bg-hidden')
check('taking it to 0% puts the background colour back over it',
      dimmed['ftImage'] != withimg['ftImage'],
      'the wash changed with the setting')

check('tiled by default, at the size asked for',
      'repeat' in withimg['ftRepeat'], f"repeat {withimg['ftRepeat']}")

cover = run({'settings': {'background_image': IMG, 'background_fit': 'cover'}}, 'bg-cover')
check('and it can fill the band instead',
      'cover' in cover['ftSize'] and 'no-repeat' in cover['ftRepeat'],
      f"size {cover['ftSize']}, repeat {cover['ftRepeat']}")

check('an image never lets the footer widen the page',
      cover['docW'] <= cover['winW'],
      f"document {cover['docW']}px in {cover['winW']}px")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
