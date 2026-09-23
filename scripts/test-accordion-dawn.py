"""Check the restyle of Dawn's collapsible rows, against a stand-in for Dawn.

The theme is not in this repo, so this builds Dawn's collapsible-row markup and
a stylesheet that behaves the way Dawn's accordion.css does — the hairlines
above and below, the rem sizing against a 62.5% root, the absolutely placed
caret, the `overflow: auto` on the content.

That makes this a test of the override mechanics: specificity and load order.
It would not catch a Dawn version that renames a class. Every check is run
twice — once with this file loaded after Dawn's and once before it — because
the file is installed by hand and that order is not ours to promise.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHEET = ROOT / 'assets' / 'hp-accordion-dawn.css'
TMP = pathlib.Path('/tmp/claude-0')

# Dawn's accordion.css, near enough: hairlines top and bottom, rem sizes
# against a 62.5% root, the caret placed absolutely, overflow on the content.
DAWN_CSS = """
  html { font-size: 62.5%; }
  body { margin: 0; font-size: 1.6rem; font-family: system-ui, sans-serif; }
  .accordion {
    border-top: 0.1rem solid rgba(18, 18, 18, 0.08);
    border-bottom: 0.1rem solid rgba(18, 18, 18, 0.08);
  }
  .accordion summary {
    display: flex;
    position: relative;
    line-height: 1;
    padding: 1.5rem 0;
    cursor: pointer;
  }
  .summary__title { display: flex; align-items: center; }
  .accordion__title {
    display: inline-block;
    margin: 0;
    padding-right: 2.5rem;
    font-size: 1.8rem;
    word-break: break-word;
  }
  .accordion .icon-accordion {
    align-self: center;
    fill: rgb(18, 18, 18);
    height: 2rem;
    width: 2rem;
    margin-right: 1rem;
  }
  .accordion .summary__title + .icon-caret {
    position: absolute;
    height: 0.6rem;
    right: 0;
    top: calc(50% - 0.2rem);
  }
  .accordion__content { margin-bottom: 1.5rem; padding: 0 0.6rem; overflow: auto; }
  details[open] > summary .icon-caret { transform: rotate(180deg); }
"""

ROW = """
<div class="product__accordion accordion quick-add-hidden">
  <details id="Details-%(i)d">
    <summary>
      <div class="summary__title">
        <svg class="icon icon-accordion" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8"/></svg>
        <h2 class="h4 accordion__title inline-richtext">%(title)s</h2>
      </div>
      <svg class="icon icon-caret" viewBox="0 0 10 6"><path d="M9 1 5 5 1 1"/></svg>
    </summary>
    <div class="accordion__content rte" id="ProductAccordion-%(i)d">
      <p>%(body)s</p>
    </div>
  </details>
</div>
"""

ROWS = "".join(ROW % {'i': i, 'title': t, 'body': b} for i, (t, b) in enumerate([
    ('Materials', 'Double gauze cotton, soft on a sore face.'),
    ('Shipping &amp; returns', 'Free U.S. shipping over $50.'),
    ('Care &amp; safety', 'Machine wash warm, clip off first.'),
]))

PROBE = """
function bx(e){var r=e.getBoundingClientRect();
 return {t:Math.round(r.top),b:Math.round(r.bottom),h:Math.round(r.height),
         l:Math.round(r.left),r:Math.round(r.right)};}
function snap(){
  var rows=document.querySelectorAll('.product__accordion');
  return {rows:[].map.call(rows,function(row){
    var cs=getComputedStyle(row);
    var sum=row.querySelector('summary');
    var title=row.querySelector('.accordion__title');
    var ico=row.querySelector('.icon-accordion');
    var caret=row.querySelector('.icon-caret');
    var content=row.querySelector('.accordion__content');
    var det=row.querySelector('details');
    return {
      border:cs.borderTopWidth, borderStyle:cs.borderTopStyle,
      radius:cs.borderTopLeftRadius, bg:cs.backgroundColor, shadow:cs.boxShadow,
      marginBottom:cs.marginBottom,
      box:bx(row), summary:bx(sum), summaryPad:getComputedStyle(sum).padding,
      titleSize:getComputedStyle(title).fontSize,
      titleCase:getComputedStyle(title).textTransform,
      titleColor:getComputedStyle(title).color,
      icoW:Math.round(ico.getBoundingClientRect().width),
      icoFill:getComputedStyle(ico).fill,
      caretPos:getComputedStyle(caret).position,
      caretBox:bx(caret), caretTransform:getComputedStyle(caret).transform,
      contentOverflow:getComputedStyle(content).overflow,
      contentSize:getComputedStyle(content).fontSize,
      contentColor:getComputedStyle(content).color,
      open:det.hasAttribute('open')
    };
  }), docW:document.documentElement.scrollWidth, winW:window.innerWidth};
}
"""


def run(name, ours_last=True, script='', width=1000):
    ours = f'<link rel="stylesheet" href="{SHEET}">'
    dawn = f'<style>{DAWN_CSS}</style>'
    head = (dawn + ours) if ours_last else (ours + dawn)
    page = TMP / f'accd-{name}.html'
    page.write_text(
        '<!doctype html><html><head><meta charset="utf-8">' + head +
        '<style>.icon-caret{transition:none !important}</style></head><body>'
        '<div style="max-width:600px;margin:40px auto">' + ROWS + '</div>'
        '<script>' + PROBE + script +
        "setTimeout(function(){document.title='RESULT'+JSON.stringify(snap());},300);"
        '</script></body></html>', encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', f'--window-size={width},900',
        '--virtual-time-budget=5000', '--dump-dom', 'file://' + str(page)],
        capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    raw = (m.group(1).replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&'))
    return json.loads(raw)


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


OPEN = "document.querySelectorAll('.product__accordion details')[0].open = true;"

for order, ours_last in (('loaded after Dawn', True), ('loaded BEFORE Dawn', False)):
    d = run('after' if ours_last else 'before', ours_last=ours_last)
    r0 = d['rows'][0]
    tag = f'({order})'

    check(f'the rows become outlined cards {tag}',
          r0['border'] == '2px' and r0['radius'] == '18px',
          f"outline {r0['border']}, radius {r0['radius']}")
    check(f'with the hard shadow under them {tag}',
          '0px 4px 0px 0px' in r0['shadow'],
          f"{r0['shadow']}")
    check(f'and they sit apart rather than butting together {tag}',
          d['rows'][1]['box']['t'] - d['rows'][0]['box']['b'] >= 14,
          f"gap {d['rows'][1]['box']['t'] - d['rows'][0]['box']['b']}px "
          f"below an 18px margin plus a 4px shadow")
    check(f"the handle gets real padding, not Dawn's 15px top and bottom {tag}",
          r0['summaryPad'] == '18px 20px',
          f"padding {r0['summaryPad']}")
    check(f'the title is the heading face, uppercase {tag}',
          r0['titleSize'] == '17px' and r0['titleCase'] == 'uppercase',
          f"{r0['titleSize']}, {r0['titleCase']}")
    check(f'the icon takes the brand green {tag}',
          rgb(r0['icoFill']) == [181, 201, 154] and r0['icoW'] == 26,
          f"fill {r0['icoFill']}, {r0['icoW']}px")
    check(f'the caret comes out of absolute placement into the row {tag}',
          r0['caretPos'] == 'static'
          and r0['caretBox']['r'] <= r0['box']['r'] - 18,
          f"position {r0['caretPos']}, caret ends {r0['caretBox']['r']} "
          f"in a row ending {r0['box']['r']}")
    check(f"the content loses Dawn's scrollbar and takes the body size {tag}",
          r0['contentOverflow'] == 'visible' and r0['contentSize'] == '16px',
          f"overflow {r0['contentOverflow']}, {r0['contentSize']}")

# --------------------------------------------------------------- behaviour ---
d = run('after', ours_last=True)
op = run('open', ours_last=True, script=OPEN)
check('opening a row still works, because the markup is untouched',
      op['rows'][0]['open'] and op['rows'][0]['box']['h'] > d['rows'][0]['box']['h'],
      f"row grows from {d['rows'][0]['box']['h']}px to {op['rows'][0]['box']['h']}px")
check("and Dawn's own caret rotation survives the restyle",
      op['rows'][0]['caretTransform'] == 'matrix(-1, 0, 0, -1, 0, 0)',
      f"{op['rows'][0]['caretTransform']}")

# ---------------------------------------------------------------- contrast ---
r0 = d['rows'][0]
check('the title reads on the row',
      contrast(rgb(r0['titleColor']), rgb(r0['bg'])) >= 4.5,
      f"{contrast(rgb(r0['titleColor']), rgb(r0['bg']))}:1")
check('and so does the text inside it',
      contrast(rgb(r0['contentColor']), rgb(r0['bg'])) >= 4.5,
      f"{contrast(rgb(r0['contentColor']), rgb(r0['bg']))}:1")

# ------------------------------------------------------------------ widths ---
for w in (1000, 500, 390):
    r = run(f'w{w}', width=w)
    check(f'nothing runs off the page at {w}px',
          r['docW'] <= r['winW'], f"document {r['docW']}px in {r['winW']}px")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
