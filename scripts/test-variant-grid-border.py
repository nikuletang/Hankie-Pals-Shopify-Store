"""Does the restored border stay off by default, and not disturb the layout?"""
import json, subprocess, sys, pathlib, re
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/variant-grid.liquid'
HERE = pathlib.Path('.').resolve()

PROBE = """<script>
(function(){
  var card = document.querySelector('.hp-vg__card');
  var cs = getComputedStyle(card);
  var grid = document.querySelector('.hp-vg__grid');
  var items = document.querySelectorAll('.hp-vg__item');
  var over = 0;
  items.forEach(function(it){
    var c = it.querySelector('.hp-vg__card').getBoundingClientRect();
    var b = it.getBoundingClientRect();
    if (c.width > b.width + 0.5) over++;
  });
  document.title = 'RESULT' + JSON.stringify({
    w: cs.borderTopWidth, style: cs.borderTopStyle, color: cs.borderTopColor,
    sides: [cs.borderTopWidth, cs.borderRightWidth,
            cs.borderBottomWidth, cs.borderLeftWidth].join(' '),
    cols: getComputedStyle(grid).gridTemplateColumns,
    cardW: Math.round(document.querySelector('.hp-vg__card').getBoundingClientRect().width),
    itemW: Math.round(items[0].getBoundingClientRect().width),
    wider: over,
    scrollW: document.documentElement.scrollWidth, vw: window.innerWidth
  });
})();
</script>"""

def run(overrides, name, width=1200):
    page = HERE / f'vg-{name}.html'
    subprocess.run([sys.executable, 'render-section.py', SECTION,
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    html = page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>')
    page.write_text(html, encoding='utf-8')
    dom = subprocess.run([CHROME,'--headless','--no-sandbox','--disable-gpu',
        f'--window-size={width},900','--virtual-time-budget=3000','--dump-dom',
        'file://'+str(page)], capture_output=True, text=True, timeout=120).stdout
    return json.loads(re.search(r'<title>RESULT(.*?)</title>', dom, re.S).group(1))

res = []
def check(label, ok, detail):
    res.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")

d = run({}, 'off')
check('default: no border drawn', d['w'] == '0px',
      f"border-top-width {d['w']}, style {d['style']}")
base_cols, base_item = d['cols'], d['itemW']

d = run({'settings': {'border_width': 2}}, 'on2')
check('border 2px: drawn at the width asked for', d['w'] == '2px',
      f"width {d['w']}  colour {d['color']}")
check('border 2px: columns unchanged', d['cols'] == base_cols,
      f"{d['cols']}")
check('border 2px: card does not grow past its column', d['wider'] == 0 and d['cardW'] <= d['itemW'],
      f"card {d['cardW']}px in a {d['itemW']}px column, {d['wider']} overflowing")
check('border 2px: no horizontal page overflow', d['scrollW'] <= d['vw'],
      f"scrollWidth {d['scrollW']} vs viewport {d['vw']}")

d = run({'settings': {'border_width': 2, 'border_tint': '#FF0000'}}, 'tint')
check('section border colour applies', d['color'] == 'rgb(255, 0, 0)', d['color'])

d = run({'settings': {'border_width': 3},
         'blocks': [{'type': 'variant', 'settings': {'card_border_color': '#00FF00'}},
                    {'type': 'variant', 'settings': {}}]}, 'blockover')
check('a card can override the colour for itself', d['color'] == 'rgb(0, 255, 0)', d['color'])

d = run({'settings': {'border_width': 8}}, 'max', width=390)
check('8px on a phone: still no overflow', d['scrollW'] <= d['vw'],
      f"scrollWidth {d['scrollW']} vs {d['vw']}, cols {d['cols']}")

# --- Per-side toggles ------------------------------------------------------
# Order throughout is top right bottom left, as the CSS shorthand reads.
cases = [
    ('all four on (default)',        {}, '3px 3px 3px 3px'),
    ('right only',                   {'border_top': False, 'border_bottom': False,
                                      'border_left': False}, '0px 3px 0px 0px'),
    ('top and bottom only',          {'border_left': False, 'border_right': False},
                                     '3px 0px 3px 0px'),
    ('left and right only',          {'border_top': False, 'border_bottom': False},
                                     '0px 3px 0px 3px'),
    ('bottom only',                  {'border_top': False, 'border_right': False,
                                      'border_left': False}, '0px 0px 3px 0px'),
    ('all four off',                 {'border_top': False, 'border_right': False,
                                      'border_bottom': False, 'border_left': False},
                                     '0px 0px 0px 0px'),
]
for label, flags, want in cases:
    d = run({'settings': dict({'border_width': 3}, **flags)},
            'side-' + label.split()[0] + str(len(flags)))
    check(f'sides — {label}', d['sides'] == want, f"got {d['sides']}, wanted {want}")

# A side switched off must not change the card's footprint.
d = run({'settings': {'border_width': 6, 'border_left': False, 'border_top': False}}, 'sidefit')
check('a dropped side does not change the card footprint',
      d['wider'] == 0 and d['cardW'] <= d['itemW'] and d['scrollW'] <= d['vw'],
      f"card {d['cardW']}px in {d['itemW']}px, scrollWidth {d['scrollW']} vs {d['vw']}")

# Right-only is the reason to have this at all: one hairline between cards
# rather than two borders meeting.
d = run({'settings': {'border_width': 1, 'border_top': False, 'border_bottom': False,
                      'border_left': False}}, 'hairline')
check('right-only leaves a single 1px edge between cards',
      d['sides'] == '0px 1px 0px 0px', d['sides'])

print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
