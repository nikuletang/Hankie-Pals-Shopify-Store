"""Check the overrides for Shopify's own buttons, against a stand-in for Dawn.

The theme is not in this repo and the store is not reachable from here, so this
builds a page with Dawn's product-form markup and a stylesheet that behaves the
way Dawn's does — including the part that actually broke: Shopify injects the
styles for Buy it now *at runtime*, so they land after anything the theme loads,
however early it loads. The page injects them the same way.

That makes this a test of the override mechanics — specificity and load order —
not a test of Dawn itself. It would not catch a Dawn version that renames a
class. Both of the bugs it was written for are failures of mechanics.
"""
import json, subprocess, sys, pathlib, re

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
TMP = pathlib.Path('/tmp/claude-0')

# Dawn's own button, near enough: a min height, its own radius variable, and the
# border drawn as a pseudo element rather than a real border.
DAWN_CSS = """
  :root { --buttons-radius: 0px; --buttons-border-width: 1px; }
  .button {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 12rem;
    min-height: 4.5rem;
    padding: 0 3rem;
    border: 0;
    border-radius: var(--buttons-radius);
    background-color: rgba(0, 0, 0, 0);
    color: #121212;
    font-size: 1.5rem;
    text-decoration: none;
    cursor: pointer;
  }
  .button::after {
    content: '';
    position: absolute;
    top: 0; right: 0; bottom: 0; left: 0;
    box-shadow: 0 0 0 var(--buttons-border-width) #121212;
    border-radius: var(--buttons-radius);
  }
  .button--primary { background-color: #121212; color: #fff; }
  .button--secondary { background-color: rgba(0, 0, 0, 0); }
  .button--full-width { width: 100%; }
  .shopify-payment-button__button--unbranded {
    display: block;
    width: 100%;
    min-height: 4.5rem;
    padding: 1rem 1.5rem;
    border: 0;
    border-radius: 0;
    background-color: #121212;
    color: #fff;
    font-size: 1.5rem;
    cursor: pointer;
  }
"""

# Dawn's product form: Add to cart is button--secondary as soon as the dynamic
# checkout button is on, which is the whole reason it came out as an outline.
MARKUP = """
  <div class="product-form">
    <button type="submit" id="atc"
            class="product-form__submit button button--full-width button--secondary">
      Add to cart
    </button>
    <div class="product-form__buttons">
      <shopify-accelerated-checkout>
        <div class="shopify-payment-button">
          <button id="buy" class="shopify-payment-button__button shopify-payment-button__button--unbranded">
            Buy it now
          </button>
        </div>
      </shopify-accelerated-checkout>
    </div>
  </div>
  <div class="drawer">
    <button id="checkout" class="button button--primary">Check out</button>
    <a id="viewcart" class="button button--secondary">View cart</a>
    <button id="soldout" class="button" disabled>Sold out</button>
  </div>
"""

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>
  html { font-size: 62.5%; }
  body { margin: 0; padding: 20px; background: #fff;
         --font-heading-family: Futura, "Century Gothic", system-ui, sans-serif;
         --font-heading-weight: 700; }
""" + DAWN_CSS + """
</style>
<link rel="stylesheet" href="file://""" + str(ROOT / 'assets' / 'hp-button-dawn.css') + """">
</head><body>
""" + MARKUP + """
<script>
  // Shopify's accelerated checkout styles arrive with its script, after the
  // page's own stylesheets. This is the part the first version missed.
  var late = document.createElement('style');
  late.textContent =
    '.shopify-payment-button__button--unbranded {' +
    '  background-color: #000; color: #fff; border-radius: 4px;' +
    '  min-height: 4.4rem; border: none;' +
    '}';
  document.head.appendChild(late);

  setTimeout(function () {
    function read(id) {
      var el = document.getElementById(id), c = getComputedStyle(el);
      return { id: id, bg: c.backgroundColor, ink: c.color, radius: c.borderTopLeftRadius,
               borderW: c.borderTopWidth, shadow: c.boxShadow, transform: c.textTransform,
               padY: c.paddingTop, after: getComputedStyle(el, '::after').display };
    }
    document.title = 'RESULT' + JSON.stringify({
      atc: read('atc'), buy: read('buy'), checkout: read('checkout'),
      viewcart: read('viewcart'), soldout: read('soldout')
    });
  }, 500);
</script>
</body></html>"""

page = TMP / 'dawn-buttons.html'
page.write_text(PAGE, encoding='utf-8')
dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
    '--window-size=900,700', '--virtual-time-budget=4000', '--allow-file-access-from-files',
    '--dump-dom', 'file://' + str(page)], capture_output=True, text=True, timeout=120).stdout
m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
if not m:
    raise SystemExit('no measurement')
d = json.loads(m.group(1))

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

TERRACOTTA = [216, 139, 109]
CREAM = [252, 251, 246]

check('Add to cart is filled, not the empty outline Dawn asks for',
      rgb(d['atc']['bg']) == TERRACOTTA,
      f"background {d['atc']['bg']} (Dawn marks it button--secondary)")
check('Buy it now beats the styles Shopify injects after the page loads',
      rgb(d['buy']['bg']) == CREAM and d['buy']['radius'] == '999px',
      f"background {d['buy']['bg']}, radius {d['buy']['radius']} "
      f"(the injected rule asks for black at 4px)")
check('both product buttons are pills with a real outline',
      d['atc']['radius'] == '999px' and d['atc']['borderW'] == '2px'
      and d['buy']['borderW'] == '2px',
      f"add to cart {d['atc']['radius']}/{d['atc']['borderW']}, "
      f"buy it now {d['buy']['radius']}/{d['buy']['borderW']}")
check('both carry the hard shadow',
      '0px 4px 0px 0px' in d['atc']['shadow'] and '0px 4px 0px 0px' in d['buy']['shadow'],
      f"add to cart {d['atc']['shadow'].split(') ')[-1]}, "
      f"buy it now {d['buy']['shadow'].split(') ')[-1]}")
check("Dawn's pseudo-element border is switched off, so nothing doubles up",
      d['atc']['after'] == 'none' and d['checkout']['after'] == 'none',
      f"::after display {d['atc']['after']}")
check('the two stacked actions do not look like the same button',
      rgb(d['atc']['bg']) != rgb(d['buy']['bg']),
      f"add to cart {d['atc']['bg']}, buy it now {d['buy']['bg']}")
check('the quiet buttons stay quiet',
      rgb(d['viewcart']['bg'])[:3] == rgb(d['checkout']['bg'])[:3] or
      d['viewcart']['bg'] == 'rgba(0, 0, 0, 0)',
      f"view cart {d['viewcart']['bg']}, check out {d['checkout']['bg']}")
check('every label clears 4.5:1 on its fill',
      all(contrast(rgb(d[k]['ink']), rgb(d[k]['bg'])) >= 4.5
          for k in ('atc', 'buy', 'checkout', 'soldout')),
      ', '.join(f"{k} {contrast(rgb(d[k]['ink']), rgb(d[k]['bg']))}"
                for k in ('atc', 'buy', 'checkout', 'soldout')))
check('a sold-out button has no shadow to press',
      d['soldout']['shadow'] == 'none',
      f"shadow {d['soldout']['shadow']}")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
