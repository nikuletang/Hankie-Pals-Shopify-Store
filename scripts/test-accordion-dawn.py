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
  /* The site's button, which these rows sit directly beneath and must not
     compete with: 2px ink outline, pill radius, hard offset shadow, a fill. */
  .hp-btn {
    display: flex; width: 100%; padding: 15px 32px;
    border: 2px solid #2F3326; border-radius: 999px; background: #D88B6D;
    color: #2F3326; box-shadow: 0 4px 0 0 #2F3326;
  }
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
  var btn=document.querySelector('.hp-btn');
  var btnCS=getComputedStyle(btn);
  return {button:{border:btnCS.borderTopWidth, radius:btnCS.borderTopLeftRadius,
                  shadow:btnCS.boxShadow, bg:btnCS.backgroundColor},
    rows:[].map.call(rows,function(row){
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
        '<div style="max-width:600px;margin:40px auto">'
        '<button class="hp-btn">Add to cart</button>' + ROWS + '</div>'
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

    btn = d['button']
    # These rows sit directly under Add to cart and Buy it now. Wearing the
    # button's own outline, shadow, radius and fill made a third button out of
    # a disclosure, which is the complaint this check exists for.
    borrowed = []
    if r0['border'] == btn['border']:
        borrowed.append(f"the same {btn['border']} outline")
    if r0['shadow'] != 'none':
        borrowed.append('a hard shadow')
    if r0['bg'] != 'rgba(0, 0, 0, 0)':
        borrowed.append('a fill of its own')
    if r0['radius'] != '0px':
        borrowed.append('rounded corners')
    check(f'a row borrows none of the buttons\' weight {tag}',
          not borrowed,
          'shares nothing with the button' if not borrowed
          else 'shares ' + ', '.join(borrowed))
    check(f'it is a hairline rule, thinner than the button\'s outline {tag}',
          r0['border'] == '1px' and r0['borderStyle'] == 'solid'
          and int(btn['border'].rstrip('px')) > 1,
          f"row {r0['border']} against the button's {btn['border']}")
    check(f'the rows butt together as one list, not a stack of cards {tag}',
          abs(d['rows'][1]['box']['t'] - d['rows'][0]['box']['b']) <= 1,
          f"gap {d['rows'][1]['box']['t'] - d['rows'][0]['box']['b']}px")
    check(f'the handle sits flush with the column {tag}',
          r0['summaryPad'] == '16px 0px',
          f"padding {r0['summaryPad']}")
    check(f'the title is the heading face, uppercase and smaller {tag}',
          r0['titleSize'] == '14px' and r0['titleCase'] == 'uppercase',
          f"{r0['titleSize']}, {r0['titleCase']}")
    check(f'the icon takes the brand green {tag}',
          rgb(r0['icoFill']) == [181, 201, 154] and r0['icoW'] == 20,
          f"fill {r0['icoFill']}, {r0['icoW']}px")
    # Dawn pins the caret absolutely to the summary's right edge. Taken into
    # the flex row it follows the padding instead of being nailed to a corner
    # the padding has since moved -- which is what went wrong when this file
    # loaded first.
    check(f'the caret comes out of absolute placement into the row {tag}',
          r0['caretPos'] == 'static'
          and r0['caretBox']['r'] <= r0['box']['r']
          and r0['caretBox']['l'] > r0['summary']['l'],
          f"position {r0['caretPos']}, caret {r0['caretBox']['l']}-"
          f"{r0['caretBox']['r']} inside a row ending {r0['box']['r']}")
    check(f"the content loses Dawn's scrollbar and takes the body size {tag}",
          r0['contentOverflow'] == 'visible' and r0['contentSize'] == '15px',
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
# The row draws no fill of its own now, so the words sit on whatever the
# product column is: white on Dawn's default scheme.
behind = [255, 255, 255] if r0['bg'] == 'rgba(0, 0, 0, 0)' else rgb(r0['bg'])
check('the title reads on whatever is behind the row',
      contrast(rgb(r0['titleColor']), behind) >= 4.5,
      f"{contrast(rgb(r0['titleColor']), behind)}:1 against the page")
check('and so does the text inside it',
      contrast(rgb(r0['contentColor']), behind) >= 4.5,
      f"{contrast(rgb(r0['contentColor']), behind)}:1")

# ------------------------------------------------------------------ widths ---
for w in (1000, 500, 390):
    r = run(f'w{w}', width=w)
    check(f'nothing runs off the page at {w}px',
          r['docW'] <= r['winW'], f"document {r['docW']}px in {r['winW']}px")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
