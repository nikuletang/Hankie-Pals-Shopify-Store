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

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
