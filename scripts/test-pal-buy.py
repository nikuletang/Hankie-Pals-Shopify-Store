"""Check "Choose your Pal".

This section does not take the money — Dawn's buy box does — so what matters
is that picking a Pal actually reaches Dawn, and that when it cannot, the
click falls through to a real link instead of doing nothing.

Dawn is not in this repo, so its three picker shapes are stood up here as
stand-ins and the suite asserts this section drives each one:

  - a radio group  (Dawn's "pill" picker)
  - a <select>     (Dawn's dropdown picker)
  - neither, just the form's hidden input[name="id"]

None of that proves Dawn's own behaviour. It proves this section keeps its
side of the bargain, which is the half that can be got wrong from here.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
SECTION = ROOT / 'sections' / 'hp-pal-buy.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

# hp-button.css is installed by hand into theme.liquid, so on a real store it
# can land after this section's rules. That is the worst case, so it is the
# one measured against.
LATE = '<link rel="stylesheet" href="' + str(ROOT / 'assets' / 'hp-button.css') + '">'

RADIOS = """
<form action="/cart/add" method="post">
  <div class="product-form__input product-form__input--pill">
    <input type="radio" name="Pal" value="Bunny" id="r1" checked><label for="r1">Bunny</label>
    <input type="radio" name="Pal" value="Cow" id="r2"><label for="r2">Cow</label>
    <input type="radio" name="Pal" value="Dog" id="r3"><label for="r3">Dog</label>
  </div>
  <input type="hidden" name="id" value="101">
</form>"""

SELECT = """
<form action="/cart/add" method="post">
  <variant-selects>
    <select name="options[Pal]">
      <option value="Bunny" selected>Bunny</option>
      <option value="Cow">Cow</option>
      <option value="Dog">Dog</option>
    </select>
  </variant-selects>
  <input type="hidden" name="id" value="101">
</form>"""

HIDDEN_ONLY = """
<form action="/cart/add" method="post">
  <input type="hidden" name="id" value="101">
</form>"""

NOTHING = ""

SNAP = """
function snap() {
  var root = document.querySelector('hp-pal-buy');
  var pills = [].map.call(document.querySelectorAll('[data-hp-pb-pill]'), function (a) {
    return { text: a.textContent.trim(), href: a.getAttribute('href'),
             current: a.getAttribute('aria-current'),
             id: a.getAttribute('data-variant-id') };
  });
  var shot = document.querySelector('[data-hp-pb-shot][data-active]');
  var said = document.querySelector('[data-hp-pb-said][data-active]');
  var stage = document.querySelector('[data-hp-pb-stage]');
  var radio = document.querySelector('input[type="radio"]:checked');
  var sel = document.querySelector('select');
  var hid = document.querySelector('input[name="id"]');
  // The element that actually holds the words, whatever the markup did with
  // them -- so a paragraph knocked out of its wrapper is measured where it
  // really landed rather than where it was meant to be.
  var blurbP = (function () {
    var said = document.querySelector('[data-hp-pb-said][data-active]');
    if (!said) return null;
    var all = said.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      if (all[i].classList.contains('hp-pb__name')) continue;
      for (var n = 0; n < all[i].childNodes.length; n++) {
        var node = all[i].childNodes[n];
        if (node.nodeType === 3 && node.textContent.trim()) return all[i];
      }
    }
    return null;
  })();
  var pill = document.querySelector('[data-hp-pb-pill]');
  var cs = pill ? getComputedStyle(pill) : null;
  return {
    pills: pills,
    blurbSize: blurbP ? getComputedStyle(blurbP).fontSize : null,
    blurbText: blurbP ? blurbP.textContent.trim().slice(0, 24) : null,
    activeShot: shot ? shot.getAttribute('data-hp-pb-shot') : null,
    activeSaid: said ? said.getAttribute('data-hp-pb-said') : null,
    accent: root ? getComputedStyle(root).getPropertyValue('--hp-pb-accent').trim() : null,
    stageBg: stage ? getComputedStyle(stage).backgroundColor : null,
    stageH: stage ? Math.round(stage.getBoundingClientRect().height) : null,
    radioChecked: radio ? radio.value : null,
    selectValue: sel ? sel.value : null,
    hiddenId: hid ? hid.value : null,
    navigated: window.__navigated || false,
    pillStyle: cs ? { radius: cs.borderTopLeftRadius, border: cs.borderTopWidth,
                      bg: cs.backgroundColor, ink: cs.color, shadow: cs.boxShadow,
                      size: cs.fontSize, padX: cs.paddingLeft } : null,
    docH: document.documentElement.scrollHeight,
    docW: document.documentElement.scrollWidth,
    winW: window.innerWidth
  };
}
"""


def run(name, dawn=RADIOS, script='', width=1280, overrides=None, late=True):
    page = TMP / f'pb-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(page)], check=True, capture_output=True)
    html = page.read_text(encoding='utf-8')
    html = html.replace('</body>',
        dawn + (LATE if late else '') + '<script>' + SNAP +
        # Any link that is allowed to run is recorded rather than followed, so
        # "did the click fall through?" is answerable without leaving the page.
        """
        document.addEventListener('click', function (e) {
          var a = e.target.closest('a');
          if (a && !e.defaultPrevented) { window.__navigated = a.getAttribute('href'); }
          if (a) e.preventDefault();
        });
        """ + script +
        "\nsetTimeout(function(){document.title='RESULT'+JSON.stringify(snap());}, 500);"
        "</script></body>")
    page.write_text(html, encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},900', '--virtual-time-budget=6000', '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


CLICK = "document.querySelectorAll('[data-hp-pb-pill]')[%d].click();"

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


# ------------------------------------------------------------- the pills ----
d = run('base')
check('one pill per Pal, named after the variant',
      [p['text'] for p in d['pills']] == ['Bunny', 'Cow', 'Dog'],
      f"{[p['text'] for p in d['pills']]}")
check('and each is a real link to its own variant',
      [p['href'] for p in d['pills']] ==
      ['/products/hankie-pals?variant=101', '/products/hankie-pals?variant=102',
       '/products/hankie-pals?variant=103'],
      f"{[p['href'] for p in d['pills']]}")
check('they carry the site button: pill, outline, hard shadow',
      d['pillStyle']['radius'] == '999px' and d['pillStyle']['border'] == '2px'
      and '0px' in d['pillStyle']['shadow'],
      f"radius {d['pillStyle']['radius']}, outline {d['pillStyle']['border']}, "
      f"shadow {d['pillStyle']['shadow']}")
check('and their size survives hp-button.css loading last',
      d['pillStyle']['size'] == '15px' and d['pillStyle']['padX'] == '24px',
      f"font {d['pillStyle']['size']}, pad-x {d['pillStyle']['padX']}")
check('the first Pal is the one showing to begin with',
      d['pills'][0]['current'] == 'true' and d['activeShot'] == '0',
      f"current {d['pills'][0]['current']}, shot {d['activeShot']}")

# ------------------------------------------------------- picking a Pal ------
pick = run('pick-cow', script=CLICK % 1)
check('picking the second Pal swaps the photo and the words together',
      pick['activeShot'] == '1' and pick['activeSaid'] == '1',
      f"shot {pick['activeShot']}, words {pick['activeSaid']}")
check('and the accent behind the photo follows it',
      rgb(pick['stageBg']) == [236, 168, 131],
      f"stage {pick['stageBg']} against the Cow's #ECA883")
check('and only the picked pill is marked current',
      [p['current'] for p in pick['pills']] == [None, 'true', None],
      f"{[p['current'] for p in pick['pills']]}")
check('swapping does not change the height of the panel',
      pick['stageH'] == d['stageH'],
      f"{d['stageH']}px before, {pick['stageH']}px after")

# ------------------------------------------------------------ reaching Dawn --
check('picking a Pal checks Dawn\'s radio for that variant',
      pick['radioChecked'] == 'Cow',
      f"radio now {pick['radioChecked']}")
check('and having reached Dawn, it does not reload the page as well',
      pick['navigated'] is False,
      f"navigated: {pick['navigated']}")

sel = run('dawn-select', dawn=SELECT, script=CLICK % 2)
check('with a dropdown instead, it sets that',
      sel['selectValue'] == 'Dog',
      f"select now {sel['selectValue']}")
check('and again does not reload',
      sel['navigated'] is False,
      f"navigated: {sel['navigated']}")

hid = run('dawn-hidden', dawn=HIDDEN_ONLY, script=CLICK % 1)
check('with no picker at all it points the form at the right variant',
      hid['hiddenId'] == '102',
      f"form id now {hid['hiddenId']}")

none = run('dawn-absent', dawn=NOTHING, script=CLICK % 1)
check('and with no product form either, the click falls through to the link',
      none['navigated'] == '/products/hankie-pals?variant=102',
      f"followed {none['navigated']}")

# --------------------------------------------------------------- contrast ---
for i, (name, hexa) in enumerate([('Bunny', '#CFE1B9'), ('Cow', '#ECA883'),
                                  ('Dog', '#B5C99A')]):
    c = contrast([47, 51, 38], rgb('rgb(%d,%d,%d)' % tuple(
        int(hexa[j:j + 2], 16) for j in (1, 3, 5))))
    check(f'the ink reads on the {name} accent', c >= 4.5, f"{c}:1")

# ------------------------------------------------------------ odd products --
SINGLE = {'title': 'Hankie Pals', 'handle': 'hankie-pals',
          'url': '/products/hankie-pals', 'available': True,
          'variants': [{'id': 301, 'title': 'Default Title', 'option1': 'Default Title',
                        'option2': None, 'option3': None, 'price': 2400,
                        'available': True, 'url': '/products/hankie-pals?variant=301'}]}
one = run('single-variant', overrides={'product': SINGLE})
check('a product with one variant does not print "Default Title" at anybody',
      all('Default Title' not in p['text'] for p in one['pills']),
      f"{[p['text'] for p in one['pills']]}")

missing = run('unknown-variant', overrides={
    'blocks': [{'type': 'pal', 'settings': {'variant_title': 'Otter', 'label': 'Otter'}}]})
check('a variant that does not exist is not linked somewhere wrong',
      missing['pills'][0]['href'] == '#' and missing['pills'][0]['id'] is None,
      f"href {missing['pills'][0]['href']}, id {missing['pills'][0]['id']}")

# -------------------------------------------------------------- the phone ---
for w in (1280, 990, 750, 500):
    ph = run(f'w{w}', width=w)
    check(f'nothing overflows at {w}px', ph['docW'] <= ph['winW'],
          f"document {ph['docW']}px in {ph['winW']}px")

# ----------------------------------------------------------- the blurb ------
# richtext brings its own <p>. Put that inside a <p> and the parser closes the
# outer one early, so the words land outside the styled element and render at
# the theme's size -- which, under Dawn's 62.5% root, is far smaller than the
# setting says. It looked wrong in a screenshot before it measured wrong.
check("the blurb is the size the setting asks for, not the theme's",
      d['blurbSize'] == '17px',
      f"blurb rendered at {d['blurbSize']} against a 17px setting")
check("and it is the Pal's own words",
      d['blurbText'] and 'Long ears' in d['blurbText'],
      f"{d['blurbText']!r}")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
