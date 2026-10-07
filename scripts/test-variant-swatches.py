"""Variant swatches: what it renders, and whether clicking one reaches Dawn.

The second half is the point. The swatches do not own the selection -- Dawn's
buy box does -- so the only question that matters is whether a click actually
sets Dawn's own control. That is driven here against a stand-in for Dawn's
pill picker, not asserted from the source.

The snippet carries no schema, because a Custom liquid block has no settings.
The renderer wants one, so a hollow schema is appended to a copy at test time
and never to the file that ships.
"""
import json, subprocess, sys, pathlib, re

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SNIPPET = pathlib.Path('/home/user/hankie-pals-shopify-store/snippets/hp-variant-swatches.liquid')
HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path('/tmp/claude-0')

# Three Pals, each with a variant image, Bunny and Cow sold out -- the shape
# the real product is in today.
def product(images=True, available=(False, False, True), values=None):
    vals = values or ['Bunny', 'Cow', 'Dog']
    vs = []
    for i, name in enumerate(vals):
        vs.append({'id': 101 + i, 'title': name, 'option1': name,
                   'option2': None, 'option3': None, 'price': 2299,
                   'compare_at_price': 2299, 'available': available[i],
                   'featured_image': None,
                   'image': f'{name.lower()}.jpg' if images else None,
                   'url': f'/products/hankie-pals?variant={101 + i}'})
    return {'title': 'Hankie Pals', 'handle': 'hankie-pals',
            'url': '/products/hankie-pals', 'available': True, 'variants': vs,
            'options_with_values': [
                {'name': 'Character', 'position': 1, 'values': vals}],
            'selected_or_first_available_variant': vs[-1],
            'featured_image': None}


def render(name, prod=None):
    """The snippet, given a schema it does not ship with."""
    wrapped = TMP / f'sw-src-{name}.liquid'
    wrapped.write_text(SNIPPET.read_text(encoding='utf-8')
                       + '\n{% schema %}{}{% endschema %}\n', encoding='utf-8')
    out = TMP / f'sw-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(wrapped),
                    json.dumps({'product': prod or product()}), str(out)],
                   check=True, capture_output=True)
    return out.read_text(encoding='utf-8')


res = []
def check(label, ok, detail):
    res.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


html = render('base')

items = re.findall(r'<li\s+class="hp-sw__item".*?</li>', html, re.S)
check('one swatch per option value',
      len(items) == 3, f"{len(items)} swatches")

check('each swatch links to its own variant, so it works with no JavaScript',
      [re.search(r'href="([^"]+)"', i).group(1) for i in items]
      == ['/products/hankie-pals?variant=101',
          '/products/hankie-pals?variant=102',
          '/products/hankie-pals?variant=103'],
      ', '.join(re.search(r'variant=(\d+)', i).group(1) for i in items))

check('each swatch carries the value it will hand Dawn',
      [re.search(r'data-hp-sw-pick="([^"]*)"', i).group(1) for i in items]
      == ['Bunny', 'Cow', 'Dog'],
      ', '.join(re.search(r'data-hp-sw-pick="([^"]*)"', i).group(1) for i in items))

# findall, not search().group(): a swatch with no <img> at all has to read
# as a clean mismatch here, not blow the suite up with an AttributeError.
srcs = [(re.findall(r'<img[^>]*src="([^"]*)"', i) or ['NO IMAGE'])[0]
        for i in items]
check('the picture comes from the variant, not from a setting',
      srcs == ['bunny.jpg', 'cow.jpg', 'dog.jpg'],
      ', '.join(srcs))

# Two of three are at zero right now, so this is the common case here.
check('a value with nothing in stock is marked sold out',
      [re.search(r'data-sold="(\w+)"', i).group(1) for i in items]
      == ['true', 'true', 'false'],
      'Bunny and Cow sold out, Dog not')

check('and says so to a screen reader rather than only dimming',
      items[0].count('sold out') == 1 and 'sold out' not in items[2],
      re.search(r'aria-label="([^"]*)"', items[0]).group(1))

check('the available one is marked as current',
      'aria-current="true"' in items[2]
      and 'aria-current' not in items[0],
      'Dog is current, Bunny is not')

# A value whose variant has no image still has to be a target.
noimg = render('noimg', product(images=False))
nitems = re.findall(r'<li\s+class="hp-sw__item".*?</li>', noimg, re.S)
check('a variant with no image falls back to its initial, not an empty hole',
      '<img' not in nitems[0] and 'hp-sw__initial' in nitems[0]
      and '>B<' in nitems[0].replace(' ', '').replace('\n', ''),
      'shows the first letter of the value')

# One option value is not a choice, so nothing should render at all.
one = render('one', product(available=(True,), values=['Dog']))
check('a product with a single value renders nothing',
      'hp-sw__row' not in one, 'no swatches for a one-value option')

check("Dawn's own picker is hidden, so the two are not shown side by side",
      re.search(r'variant-radios,\s*variant-selects\s*{\s*display:\s*none',
                html) is not None,
      'variant-radios and variant-selects hidden')

# --- does a click actually reach Dawn? --------------------------------------
# A stand-in for Dawn's pill picker: the radios the real one renders, plus a
# listener that records what it was told, the way Dawn's would re-render.
DAWN = """
<variant-radios>
  <fieldset class="product-form__input">
    <input type="radio" name="Character" value="Bunny" id="r1">
    <input type="radio" name="Character" value="Cow" id="r2">
    <input type="radio" name="Character" value="Dog" id="r3" checked>
  </fieldset>
</variant-radios>
<form action="/cart/add"><input name="id" value="103"></form>
<script>
  window.__told = [];
  document.querySelectorAll('variant-radios input').forEach(function (r) {
    r.addEventListener('change', function () { window.__told.push(r.value); });
  });
</script>
"""

DRIVE = """
<script>
window.addEventListener('load', function () {
  var out = {navigated: false};
  // A real navigation would end the test, so record the attempt and cancel
  // it -- but ONLY for the swatch link. A blanket preventDefault also
  // cancels the programmatic click tellDawn makes on Dawn's radio, which
  // made this harness quietly break the thing it is measuring.
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-hp-sw-pick]');
    if (!a) return;
    if (!e.defaultPrevented) out.navigated = true;
    e.preventDefault();
  });
  document.querySelector('[data-hp-sw-pick="Bunny"]').click();
  out.told = window.__told;
  out.checked = [].slice.call(document.querySelectorAll('variant-radios input'))
                  .filter(function (r) { return r.checked; })
                  .map(function (r) { return r.value; });
  out.current = [].slice.call(document.querySelectorAll('.hp-sw__item'))
                  .filter(function (li) { return li.getAttribute('aria-current') === 'true'; })
                  .map(function (li) {
                    return li.querySelector('[data-hp-sw-pick]').getAttribute('data-hp-sw-pick');
                  });
  out.label = document.querySelector('[data-hp-sw-current]').textContent.trim();
  document.title = 'RESULT' + JSON.stringify(out);
});
</script>
"""

page = TMP / 'sw-drive.html'
page.write_text(html.replace('</body>', DAWN + DRIVE + '</body>'), encoding='utf-8')
dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                      '--window-size=900,900', '--virtual-time-budget=4000',
                      '--dump-dom', 'file://' + str(page)],
                     capture_output=True, text=True, timeout=120).stdout
d = json.loads(re.search(r'<title>RESULT(.*?)</title>', dom, re.S).group(1))

check("clicking a swatch checks Dawn's own radio for that value",
      d['checked'] == ['Bunny'], f"Dawn now has {d['checked']} checked")

check('and Dawn is told about it, so it can re-render price and gallery',
      d['told'] == ['Bunny'], f"change fired for {d['told']}")

check('the click is swallowed once Dawn has taken it, so the page does not reload',
      d['navigated'] is False,
      'default prevented, no navigation to ?variant=')

check('the chosen swatch moves to the one just clicked',
      d['current'] == ['Bunny'], f"current is {d['current']}")

check('and the label above reads the new choice',
      d['label'] == 'Bunny', f"reads {d['label']!r}")

# With no Dawn on the page at all, the click must NOT be swallowed -- the href
# is the only thing that can still select the variant.
bare = TMP / 'sw-bare.html'
bare.write_text(html.replace('</body>', DRIVE + '</body>'), encoding='utf-8')
dom2 = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                       '--window-size=900,900', '--virtual-time-budget=4000',
                       '--dump-dom', 'file://' + str(bare)],
                      capture_output=True, text=True, timeout=120).stdout
d2 = json.loads(re.search(r'<title>RESULT(.*?)</title>', dom2, re.S).group(1))

check('with no Dawn controls on the page the link is left to do the work',
      d2['navigated'] is True,
      'click not swallowed, so the browser follows ?variant=')

failed = res.count(False)
print(f"\n{res.count(True)} passed, {failed} failed")
sys.exit(1 if failed else 0)
