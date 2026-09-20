"""Check the decoration on "Meet the Pals" stays decoration: that the corner
pebbles hold the corners without crowding the words, that nothing they do can
widen the page, and that the picker row centres on a phone without stranding a
Pal off the left edge.

Geometry is measured with motion off. Headless Chromium renders about two frames
under --virtual-time-budget, so anything mid-animation reports its *starting*
value; motion is checked separately, by reading what is wired up.
"""
import json, subprocess, sys, pathlib, re

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/pals-picker.liquid'
HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path('/tmp/claude-0')

COPY = {
    'heading': "Choose the pal your little one's nose will love",
    'intro': '<p>Ask a toddler for the fox one and you will get a blank look. '
             'Ask for Pip and you will get a hand held out.</p>',
    'footnote': '<p>More Pals on the way. Tell us who you would like to meet next.</p>',
}

PALS = {'blocks': [
    {'type': 'pal', 'settings': {'name': n, 'trait': t}} for n, t in (
        ('Pip', 'First one out the door.'),
        ('Bo', 'Takes his time about everything.'),
        ('June', 'Wants to do it herself, thank you.'))]}

PROBE = """<script>
function box(el) {
  var r = el.getBoundingClientRect();
  return { l: Math.round(r.left), r: Math.round(r.right),
           t: Math.round(r.top), b: Math.round(r.bottom),
           w: Math.round(r.width), h: Math.round(r.height) };
}

function shown(el) {
  var cs = getComputedStyle(el);
  return cs.display !== 'none' && cs.visibility !== 'hidden';
}

setTimeout(function () {
  var panel = null;
  [].forEach.call(document.querySelectorAll('.hp-pals__panel'), function (p) {
    if (shown(p)) panel = p;
  });
  var chips = document.querySelector('.hp-pals__chips');
  var kids = chips.children;
  var cs = getComputedStyle(chips);

  document.title = 'RESULT' + JSON.stringify({
    pebblesInDom: document.querySelectorAll('.hp-pals__pebble').length,
    // The layer carries the stacking, not each pebble.
    pebbleZ: (function () {
      var w = document.querySelector('.hp-pals__pebbles');
      return w ? getComputedStyle(w).zIndex : null;
    })(),
    pebbles: [].filter.call(document.querySelectorAll('.hp-pals__pebble'), shown)
      .map(function (el) {
        var c = getComputedStyle(el);
        return { side: el.classList.contains('hp-pals__pebble--l') ? 'left' : 'right',
                 box: box(el), z: c.zIndex, opacity: Math.round(parseFloat(c.opacity) * 100) / 100,
                 radius: c.borderTopLeftRadius, anim: c.animationName,
                 events: c.pointerEvents };
      }),
    // Everything the pebbles must stay clear of. For text that means the line
    // boxes, not the element: the heading's box is 28ch wide and centred, so it
    // runs nearly edge to edge at these sizes while the words themselves sit in
    // the middle of it. Measuring the box would report an overlap that nobody
    // can see, and would push the pebbles off the screen to satisfy it.
    words: (function () {
      var out = [];
      [].forEach.call(document.querySelectorAll(
        '.hp-pals__eyebrow-inner, .hp-pals__heading, .hp-pals__intro, .hp-pals__footnote'),
        function (el) {
          var range = document.createRange();
          range.selectNodeContents(el);
          [].forEach.call(range.getClientRects(), function (r, i) {
            if (r.width < 1 || r.height < 1) return;
            out.push({ what: el.className.split(' ')[0] + ' line ' + (i + 1),
                       box: { l: Math.round(r.left), r: Math.round(r.right),
                              t: Math.round(r.top), b: Math.round(r.bottom) } });
          });
        });
      // A chip is a picture, so its own box is the thing to clear.
      [].forEach.call(document.querySelectorAll('.hp-pals__chip'), function (el) {
        out.push({ what: 'chip', box: box(el) });
      });
      return out;
    })(),
    chips: {
      box: box(chips),
      padL: parseFloat(cs.paddingLeft),
      padR: parseFloat(cs.paddingRight),
      justify: cs.justifyContent,
      scrollW: chips.scrollWidth,
      clientW: chips.clientWidth,
      scrollLeft: Math.round(chips.scrollLeft),
      first: box(kids[0]),
      last: box(kids[kids.length - 1]),
      count: kids.length
    },
    panel: panel ? box(panel) : null,
    innerZ: getComputedStyle(document.querySelector('.hp-pals__inner')).zIndex,
    docW: document.documentElement.scrollWidth,
    winW: window.innerWidth,
    clip: getComputedStyle(document.querySelector('.hp-pals')).overflowX
  });
}, 700);
</script>"""


def run(overrides, name, width=1440, flags=()):
    page = TMP / f'pk-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>'),
                    encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},1000', '--virtual-time-budget=4000', *flags,
        '--dump-dom', 'file://' + str(page)], capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def overlap(a, b):
    """How far two boxes overlap on the narrower axis; 0 or less means clear."""
    return min(min(a['r'], b['r']) - max(a['l'], b['l']),
               min(a['b'], b['b']) - max(a['t'], b['t']))


still = dict(PALS, settings=dict(COPY, enable_motion=False))

# ------------------------------------------------------------ the corners --
d = run(still, 'wide')
check('two pebbles, one in each top corner',
      len(d['pebbles']) == 2 and
      sorted(p['side'] for p in d['pebbles']) == ['left', 'right'],
      f"{[(p['side'], p['box']['l'], p['box']['t']) for p in d['pebbles']]}")
check('both are in the upper half of the band',
      all(p['box']['b'] < d['panel']['t'] for p in d['pebbles']),
      f"pebbles end {[p['box']['b'] for p in d['pebbles']]}, panel starts {d['panel']['t']}")
check('each hangs off its own edge rather than floating inside',
      d['pebbles'][0]['box']['l'] < 0 and d['pebbles'][1]['box']['r'] > d['winW'],
      f"left starts {d['pebbles'][0]['box']['l']}, right ends {d['pebbles'][1]['box']['r']} "
      f"in a {d['winW']}px window")
check('they are pebbles, not circles or boxes',
      all('%' in p['radius'] for p in d['pebbles']),
      f"border-radius {d['pebbles'][0]['radius']}")
check('they sit behind the content',
      int(d['pebbleZ']) < int(d['innerZ']),
      f"pebble layer z {d['pebbleZ']} vs content z {d['innerZ']}")
check('and cannot be clicked',
      all(p['events'] == 'none' for p in d['pebbles']),
      f"pointer-events {[p['events'] for p in d['pebbles']]}")
check('they are held back, not painted at full strength',
      all(0 < p['opacity'] < 1 for p in d['pebbles']),
      f"opacity {[p['opacity'] for p in d['pebbles']]}")
check('the band clips them instead of widening the page',
      d['docW'] <= d['winW'] and d['clip'] in ('hidden', 'clip'),
      f"document {d['docW']}px in a {d['winW']}px window, overflow-x: {d['clip']}")

# The one that matters: a pebble behind a word is the thing to avoid.
for w in (1920, 1600, 1440, 1200, 990, 800, 750):
    n = run(still, f'w{w}', width=w)
    worst, where = -10 ** 6, None
    for peb in n['pebbles']:
        for word in n['words']:
            o = overlap(peb['box'], word['box'])
            if o > worst:
                worst, where = o, word['what']
    # A margin, not a miss: touching would read as a mistake, and the floor is
    # what stops a later tweak creeping back up to the text.
    check(f'no pebble comes within 24px of the words at {w}px',
          worst <= -24 and n['docW'] <= n['winW'],
          f"closest {-worst}px clear of {where}; document {n['docW']}px in {n['winW']}px"
          if worst <= 0 else f"{worst}px over {where}")

for w in (749, 600, 390):
    n = run(still, f'narrow{w}', width=max(w, 500))
    check(f'no pebbles at {w}px, where there is no margin for them',
          len(n['pebbles']) == 0 and n['docW'] <= n['winW'],
          f"{len(n['pebbles'])} shown, document {n['docW']}px in {n['winW']}px")

off = run(dict(PALS, settings={'enable_motion': False, 'show_pebbles': False}), 'off')
check('the pebbles can be turned off',
      off['pebblesInDom'] == 0, f"{off['pebblesInDom']} in the DOM with the setting off")

# ---------------------------------------------------------------- motion --
m = run(PALS, 'motion')
check('the pebbles drift on the same morph the photo uses',
      all(p['anim'] == 'hp-pals-morph' for p in m['pebbles']),
      f"{[p['anim'] for p in m['pebbles']]}")
rm = run(PALS, 'reduced', flags=('--force-prefers-reduced-motion',))
check('nothing drifts for a visitor who asked for less motion',
      all(p['anim'] == 'none' for p in rm['pebbles']) and len(rm['pebbles']) == 2,
      f"{[p['anim'] for p in rm['pebbles']]}, {len(rm['pebbles'])} still shown")

# ----------------------------------------------------------------- chips --
# 500px is the narrowest window this browser will open, so the phone cases are
# rendered at 500 and read through the layout rather than the window.
for w in (500, 600, 749):
    c = run(still, f'chips{w}', width=w)['chips']
    fits = c['scrollW'] <= c['clientW'] + 1
    left = c['first']['l'] - (c['box']['l'] + c['padL'])
    right = (c['box']['r'] - c['padR']) - c['last']['r']
    check(f'the three Pals are centred at {w}px',
          fits and abs(left - right) <= 2,
          f"{left:.0f}px before, {right:.0f}px after ({c['count']} Pals, "
          f"row {c['scrollW']}px in {c['clientW']}px)")

# Six Pals will not fit a phone; the row has to scroll from the first one.
many = {'settings': {'enable_motion': False},
        'blocks': [{'type': 'pal', 'settings': {'name': n}} for n in
                   ('Pip', 'Bo', 'June', 'Nell', 'Wren', 'Otto')]}
c = run(many, 'chips-many', width=500)['chips']
check('a row too long to fit still starts at the first Pal',
      c['scrollW'] > c['clientW'] and c['first']['l'] >= c['box']['l'] - 1,
      f"row {c['scrollW']}px in {c['clientW']}px, first Pal at {c['first']['l']} "
      f"with the row at {c['box']['l']}")
check('and it can be scrolled to the last one',
      c['justify'] == 'safe center',
      f"justify-content: {c['justify']}")

wide = run(still, 'chips-wide', width=1440)['chips']
check('the row is still centred on desktop',
      abs((wide['first']['l'] - wide['box']['l']) -
          (wide['box']['r'] - wide['last']['r'])) <= 2,
      f"{wide['first']['l'] - wide['box']['l']}px before, "
      f"{wide['box']['r'] - wide['last']['r']}px after")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
