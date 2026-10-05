"""Our values: the band, the pebble geometry, and how it folds down.

Every number in the brief is measured here rather than read off the source,
because the ones most likely to be wrong are the ones only layout knows: that
the shadow sits behind its pebble and not on it, that the badge overlaps the
pebble's top edge instead of floating above it, and that four tilted cards in
a row do not push the page sideways on a phone.
"""
import json, subprocess, sys, pathlib, re

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/our-values.liquid'
HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path('/tmp/claude-0')

PROBE = """<script>
(function(){
  function box(el){ if(!el) return null; var r = el.getBoundingClientRect();
    return {x:+r.left.toFixed(1), y:+r.top.toFixed(1),
            w:+r.width.toFixed(1), h:+r.height.toFixed(1)}; }
  // Layout metrics, immune to the card's rotation.
  function lay(el){ if(!el) return null;
    return {l: el.offsetLeft, t: el.offsetTop,
            w: el.offsetWidth, h: el.offsetHeight}; }
  // Works where offsetWidth does not, e.g. on an <svg>.
  function used(el){ if(!el) return null; var c = getComputedStyle(el);
    return {w: parseFloat(c.width), h: parseFloat(c.height)}; }
  function cs(el, props){ if(!el) return null;
    var c = getComputedStyle(el), o = {};
    props.forEach(function(p){ o[p] = c.getPropertyValue(p); }); return o; }

  var root = document.querySelector('.hp-ov');
  var head = document.querySelector('.hp-ov__head');
  var eyebrow = document.querySelector('.hp-ov__eyebrow');
  var heading = document.querySelector('.hp-ov__heading');
  var row = document.querySelector('.hp-ov__row');
  var cards = [].slice.call(document.querySelectorAll('.hp-ov__card'));
  var sprinkles = [].slice.call(document.querySelectorAll('.hp-ov__sprinkle'));

  document.title = 'RESULT' + JSON.stringify({
    rootBg: root ? getComputedStyle(root).backgroundColor : null,
    rootIsolation: root ? getComputedStyle(root).isolation : null,
    rootOverflowX: root ? getComputedStyle(root).overflowX : null,
    rootPad: cs(root, ['padding-top','padding-bottom']),
    rootGap: root ? getComputedStyle(root).rowGap : null,

    headMax: head ? getComputedStyle(head).maxWidth : null,
    headGap: head ? getComputedStyle(head).rowGap : null,
    eyeType: cs(eyebrow, ['font-size','letter-spacing','text-transform',
                          'border-radius','padding-top','padding-left','font-weight']),
    headingTag: heading ? heading.tagName : null,
    headingType: cs(heading, ['font-size','line-height','letter-spacing',
                              'font-weight','text-align']),

    rowCols: row ? getComputedStyle(row).gridTemplateColumns : null,
    rowGap: row ? getComputedStyle(row).columnGap : null,
    rowMax: row ? getComputedStyle(row).maxWidth : null,
    rowBox: box(row),

    cards: cards.map(function(c){
      var sh = c.querySelector('.hp-ov__shadow');
      var pb = c.querySelector('.hp-ov__pebble');
      var bd = c.querySelector('.hp-ov__badge');
      var cp = c.querySelector('.hp-ov__copy');
      var ti = c.querySelector('.hp-ov__title');
      var bo = c.querySelector('.hp-ov__body');
      var ic = c.querySelector('.hp-ov__badge svg');
      var st = getComputedStyle(c);
      return {
        cls: c.className,
        box: box(c), lay: lay(c), transform: st.transform, transition: st.transitionProperty,
        rot: st.getPropertyValue('--hp-ov-rot').trim(),
        offset: st.getPropertyValue('--hp-ov-offset').trim(),
        marginTop: st.marginTop,
        shadowBox: box(sh), pebbleBox: box(pb),
        shadowLay: lay(sh), pebbleLay: lay(pb),
        shadowZ: sh ? getComputedStyle(sh).zIndex : null,
        pebbleZ: pb ? getComputedStyle(pb).zIndex : null,
        shadowTf: sh ? getComputedStyle(sh).transform : null,
        shadowFill: sh ? sh.querySelector('path').getAttribute('fill') : null,
        pebbleFill: pb ? pb.querySelector('path').getAttribute('fill') : null,
        pebbleStroke: pb ? pb.querySelector('path').getAttribute('vector-effect') : null,
        pebbleLine: pb ? getComputedStyle(pb.querySelector('path')).stroke : null,
        pebbleLineW: pb ? pb.querySelector('path').getAttribute('stroke-width') : null,
        badgeLine: bd ? getComputedStyle(bd).borderTopColor : null,
        titleColor: ti ? getComputedStyle(ti).color : null,
        badgeBox: box(bd), badgeLay: lay(bd),
        badgeBorder: bd ? getComputedStyle(bd).borderTopWidth : null,
        badgeRadius: bd ? getComputedStyle(bd).borderRadius : null,
        badgeTf: bd ? getComputedStyle(bd).transform : null,
        iconBox: box(ic), iconUsed: used(ic),
        copyBox: box(cp), copyLay: lay(cp),
        copyAlign: cp ? getComputedStyle(cp).textAlign : null,
        copyGap: cp ? getComputedStyle(cp).rowGap : null,
        titleTag: ti ? ti.tagName : null,
        titleType: cs(ti, ['font-size','line-height','letter-spacing',
                           'text-transform','font-weight']),
        bodyType: cs(bo, ['font-size','line-height','font-weight']),
        iconShapes: bd ? bd.querySelectorAll('path,circle,ellipse').length : 0
      };
    }),

    sprinkles: sprinkles.map(function(s){
      var c = getComputedStyle(s);
      return {w: c.width, bg: c.backgroundColor, display: c.display,
              left: s.style.left, top: s.style.top};
    }),

    scrollW: document.documentElement.scrollWidth, vw: window.innerWidth
  });
})();
</script>"""


def run(name, overrides=None, width=1440, height=1100, reduced=False):
    page = TMP / f'ov-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps(overrides or {}), str(page)],
                   check=True, capture_output=True)
    html = page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>')
    page.write_text(html, encoding='utf-8')
    cmd = [CHROME, '--headless', '--no-sandbox', '--disable-gpu',
           f'--window-size={width},{height}', '--virtual-time-budget=4000', '--dump-dom']
    if reduced:
        cmd.append('--force-prefers-reduced-motion')
    cmd.append('file://' + str(page))
    dom = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit(f'{name}: no probe result\n' + dom[:2000])
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")

def near(a, b, tol=1.5):
    return abs(a - b) <= tol


d = run('desktop')
cards = d['cards']

# ----------------------------------------------------------------- band ---
check('the band is peach',
      d['rootBg'] == 'rgb(240, 196, 168)',
      f"{d['rootBg']} (want #F0C4A8)")

check('the section makes a stacking context and clips its own overhang',
      d['rootIsolation'] == 'isolate' and d['rootOverflowX'] == 'clip',
      f"isolation {d['rootIsolation']}, overflow-x {d['rootOverflowX']}")

check('section padding is 130 top / 160 bottom',
      d['rootPad']['padding-top'] == '130px' and d['rootPad']['padding-bottom'] == '160px',
      f"{d['rootPad']['padding-top']} / {d['rootPad']['padding-bottom']}")

check('header and row are 64px apart',
      d['rootGap'] == '64px', f"gap {d['rootGap']}")

# --------------------------------------------------------------- header ---
check('the header is held to 780px, with an 18px gap',
      d['headMax'] == '780px' and d['headGap'] == '18px',
      f"max-width {d['headMax']}, gap {d['headGap']}")

e = d['eyeType']
check('the eyebrow is a 10px uppercase pill, 1.5px tracking, 7/14 padding',
      e['font-size'] == '10px' and e['letter-spacing'] == '1.5px'
      and e['text-transform'] == 'uppercase' and e['border-radius'] == '999px'
      and e['padding-top'] == '7px' and e['padding-left'] == '14px'
      and e['font-weight'] == '700',
      f"{e['font-size']} ls {e['letter-spacing']} "
      f"pad {e['padding-top']}/{e['padding-left']} r{e['border-radius']}")

check('the heading is a real heading element',
      d['headingTag'] == 'H2', f"<{(d['headingTag'] or '?').lower()}>")

h = d['headingType']
check('heading type is 40/48, -0.5px, weight 800, centred',
      h['font-size'] == '40px' and h['line-height'] == '48px'
      and h['letter-spacing'] == '-0.5px' and h['font-weight'] == '800'
      and h['text-align'] == 'center',
      f"{h['font-size']}/{h['line-height']} ls {h['letter-spacing']} "
      f"w{h['font-weight']} {h['text-align']}")

# ------------------------------------------------------------------ row ---
check('four columns of 300px',
      d['rowCols'] == '300px 300px 300px 300px', f"{d['rowCols']}")

check('the row is 1272 wide with a 24px gap',
      d['rowMax'] == '1272px' and d['rowGap'] == '24px',
      f"max-width {d['rowMax']}, gap {d['rowGap']}")

# The brief's absolute x positions, reproduced by the grid.
want_x = [10, 330, 655, 970]
got_x = [c['lay']['l'] for c in cards]
check("the cards land where the brief's x positions put them",
      all(abs(g - w) <= 12 for g, w in zip(got_x, want_x)),
      f"got {got_x}  brief {want_x}  (grid, within 12px)")

check('all four values render',
      len(cards) == 4,
      f"{len(cards)} card(s)")

# ----------------------------------------------------------------- card ---
check('each card is 300 x 320',
      all(near(c['lay']['w'], 300) and near(c['lay']['h'], 320) for c in cards),
      ', '.join(f"{c['lay']['w']}x{c['lay']['h']}" for c in cards))

check('the four tilts are -3, +2, -1, +3',
      [c['rot'] for c in cards] == ['-3deg', '2deg', '-1deg', '3deg'],
      f"{[c['rot'] for c in cards]}")

check('the four drops are 60, 140, 40, 130',
      [c['marginTop'] for c in cards] == ['60px', '140px', '40px', '130px'],
      f"{[c['marginTop'] for c in cards]}")

check('the drop is a margin, so the hover transform does not have to carry it',
      all(c['marginTop'] != '0px' or c['offset'] == '0px' for c in cards)
      and 'transform' in cards[0]['transition'],
      f"margin-top {cards[0]['marginTop']}, transition on {cards[0]['transition']}")

# ------------------------------------------------- pebble and its shadow ---
check('the pebble is 305 x 270, 50px down the card',
      all(near(c['pebbleLay']['w'], 305) and near(c['pebbleLay']['h'], 270)
          for c in cards)
      and all(near(c['pebbleLay']['t'], 50) for c in cards),
      f"{cards[0]['pebbleLay']['w']}x{cards[0]['pebbleLay']['h']}, "
      f"{cards[0]['pebbleLay']['t']}px down")

check('the pebble is centred across a column 5px narrower than it is',
      all(near(c['pebbleLay']['l'], -2.5, 1) for c in cards),
      f"left {cards[0]['pebbleLay']['l']}px (want -2.5)")

check('the shadow sits behind the pebble, not on it',
      all(int(c['shadowZ']) < int(c['pebbleZ']) for c in cards),
      f"shadow z{cards[0]['shadowZ']} < pebble z{cards[0]['pebbleZ']}")

check('the shadow is offset 8 right and 8 down',
      all(c['shadowTf'] == 'matrix(1, 0, 0, 1, 8, 8)' for c in cards),
      f"{cards[0]['shadowTf']}")

check('the shadow is a different shape from the pebble, not the same one moved',
      all(c['shadowLay']['w'] == c['pebbleLay']['w'] for c in cards)
      and cards[0]['shadowFill'] == 'var(--hp-ov-shadow)',
      "both 305 wide, drawn from two different generated paths")

check('the outline holds 2px however the blob is stretched',
      all(c['pebbleStroke'] == 'non-scaling-stroke' for c in cards),
      f"vector-effect={cards[0]['pebbleStroke']!r}")

check('the pebble fills alternate cream and pale green',
      [c['pebbleFill'] for c in cards] == ['#FCF9F4', '#E8F0E0', '#FCF9F4', '#E8F0E0'],
      f"{[c['pebbleFill'] for c in cards]}")

# Ink, the pebble outline and the badge ring are three settings that happen to
# share a default. Changing one must not drag the others with it.
check('out of the box all three lines are the same ink',
      all(c['pebbleLine'] == 'rgb(47, 52, 39)' and c['badgeLine'] == 'rgb(47, 52, 39)'
          and c['titleColor'] == 'rgb(47, 52, 39)' for c in cards),
      f"pebble {cards[0]['pebbleLine']}, badge {cards[0]['badgeLine']}, "
      f"title {cards[0]['titleColor']}")

only_pebble = run('pebbleline', {'settings': {'pebble_outline': '#E06E4C'}})
pc = only_pebble['cards'][0]
check('the pebble outline can be changed on its own',
      pc['pebbleLine'] == 'rgb(224, 110, 76)'
      and pc['badgeLine'] == 'rgb(47, 52, 39)'
      and pc['titleColor'] == 'rgb(47, 52, 39)',
      f"pebble {pc['pebbleLine']}, badge {pc['badgeLine']} and "
      f"title {pc['titleColor']} both unmoved")

# 0 is how the outline is removed, and it is exactly the value a `| default:`
# would swallow. Both widths are checked at 0 and at a value either side.
noline = run('noline', {'settings': {'pebble_outline_width': 0,
                                     'badge_outline_width': 0}})
nc = noline['cards'][0]
check('both outlines can be removed entirely',
      nc['pebbleLineW'] == '0' and nc['badgeLine'].startswith('rgb')
      and nc['badgeBorder'] == '0px',
      f"pebble stroke-width {nc['pebbleLineW']}, badge border {nc['badgeBorder']}")

check('removing the ring does not resize the badge',
      near(nc['badgeLay']['w'], 84) and near(nc['badgeLay']['h'], 84),
      f"{nc['badgeLay']['w']}x{nc['badgeLay']['h']} with no ring "
      f"(was {cards[0]['badgeLay']['w']}x{cards[0]['badgeLay']['h']})")

check('removing the pebble outline does not move the pebble',
      near(nc['pebbleLay']['w'], 305) and near(nc['pebbleLay']['t'], 50),
      f"{nc['pebbleLay']['w']}x{nc['pebbleLay']['h']} at {nc['pebbleLay']['t']}px")

thick = run('thickline', {'settings': {'pebble_outline_width': 5,
                                       'badge_outline_width': 4}})
tc = thick['cards'][0]
check('the outlines can also be made heavier',
      tc['pebbleLineW'] == '5' and tc['badgeBorder'] == '4px',
      f"pebble {tc['pebbleLineW']}, badge {tc['badgeBorder']}")

check('the default width is still 2 on both',
      cards[0]['pebbleLineW'] == '2' and cards[0]['badgeBorder'] == '2px',
      f"pebble {cards[0]['pebbleLineW']}, badge {cards[0]['badgeBorder']}")

only_badge = run('badgeline', {'settings': {'badge_outline': '#5E6152'}})
bc = only_badge['cards'][0]
check('the badge ring can be changed on its own',
      bc['badgeLine'] == 'rgb(94, 97, 82)'
      and bc['pebbleLine'] == 'rgb(47, 52, 39)',
      f"badge {bc['badgeLine']}, pebble {bc['pebbleLine']} unmoved")

only_ink = run('inkonly', {'settings': {'ink_color': '#8A3B2A'}})
ic = only_ink['cards'][0]
check('changing the ink no longer repaints the outlines',
      ic['titleColor'] == 'rgb(138, 59, 42)'
      and ic['pebbleLine'] == 'rgb(47, 52, 39)'
      and ic['badgeLine'] == 'rgb(47, 52, 39)',
      f"title {ic['titleColor']}, pebble {ic['pebbleLine']}, badge {ic['badgeLine']}")

# ---------------------------------------------------------------- badge ---
check('each badge is an 84px circle with a 2px outline',
      all(near(c['badgeLay']['w'], 84) and near(c['badgeLay']['h'], 84)
          and c['badgeBorder'] == '2px' and c['badgeRadius'] == '50%'
          for c in cards),
      f"{cards[0]['badgeLay']['w']}px, border {cards[0]['badgeBorder']}, "
      f"radius {cards[0]['badgeRadius']}")

check('each icon is 40px',
      all(near(c['iconUsed']['w'], 40) for c in cards),
      f"{[c['iconUsed']['w'] for c in cards]}")

# This is the whole look: a badge clear of the blob would read as a floating
# bubble instead of a sticker pressed onto it.
overlaps = [c['badgeLay']['t'] + c['badgeLay']['h'] - c['pebbleLay']['t']
            for c in cards]
check('every badge overlaps the top edge of its pebble',
      all(o > 10 for o in overlaps),
      f"overlap {overlaps}px")

badge_l = [c['badgeLay']['l'] for c in cards]
check('badges 1 and 3 are centred, 2 and 4 sit right',
      all(near(badge_l[i], 108, 3) for i in (0, 2))
      and all(near(badge_l[i], 126, 3) for i in (1, 3)),
      f"left offsets {badge_l} (want 108, 126, 108, 126)")

check('the badges tilt -8, +8, -8, +8',
      cards[0]['badgeTf'] != cards[1]['badgeTf']
      and cards[0]['badgeTf'] == cards[2]['badgeTf']
      and cards[1]['badgeTf'] == cards[3]['badgeTf'],
      "alternating, and the two directions differ")

# Each icon is drawn, not an empty <svg> left behind by a missing `when`.
check('every icon actually draws something',
      all(c['iconShapes'] > 0 for c in cards),
      f"shapes per icon: {[c['iconShapes'] for c in cards]}")

# ----------------------------------------------------------------- copy ---
check('the copy column is 210px, centred, 10px gap',
      all(near(c['copyLay']['w'], 210) and c['copyAlign'] == 'center'
          and c['copyGap'] == '10px' for c in cards),
      f"{cards[0]['copyLay']['w']}px, {cards[0]['copyAlign']}, gap {cards[0]['copyGap']}")

check('the title is a real heading element',
      all(c['titleTag'] == 'H3' for c in cards),
      f"<{cards[0]['titleTag'].lower()}>")

t = cards[0]['titleType']
check('title type is 18/22 uppercase, 1.5px tracking, weight 800',
      t['font-size'] == '18px' and t['line-height'] == '22px'
      and t['letter-spacing'] == '1.5px' and t['text-transform'] == 'uppercase'
      and t['font-weight'] == '800',
      f"{t['font-size']}/{t['line-height']} ls {t['letter-spacing']} w{t['font-weight']}")

bt = cards[0]['bodyType']
check('body type is 14/22, weight 300',
      bt['font-size'] == '14px' and bt['line-height'] == '22px'
      and bt['font-weight'] == '300',
      f"{bt['font-size']}/{bt['line-height']} w{bt['font-weight']}")

# Copy is centred in the pebble rather than pinned, so a two-line title does
# not push the body out of the blob. Card 3's title wraps; card 1's does not.
def copy_centre_gap(c):
    pebble_mid = c['pebbleLay']['t'] + c['pebbleLay']['h'] / 2
    copy_mid = c['copyLay']['t'] + c['copyLay']['h'] / 2
    return abs(copy_mid - pebble_mid)
check('the copy stays centred in the pebble whether the title wraps or not',
      all(copy_centre_gap(c) < 2.0 for c in cards),
      ', '.join(f"{copy_centre_gap(c):.1f}px off centre" for c in cards))

# ------------------------------------------------------------ sprinkles ---
check('five sprinkles, at the brief\'s sizes',
      len(d['sprinkles']) == 5
      and [s['w'] for s in d['sprinkles']] == ['14px','20px','16px','24px','18px'],
      f"{[s['w'] for s in d['sprinkles']]}")

check('the sprinkles are coral, cream, coral, sage, cream',
      [s['bg'] for s in d['sprinkles']] == [
          'rgb(224, 110, 76)', 'rgb(252, 249, 244)', 'rgb(224, 110, 76)',
          'rgb(194, 214, 168)', 'rgb(252, 249, 244)'],
      f"{[s['bg'] for s in d['sprinkles']]}")

off = run('nosprinkle', {'settings': {'show_sprinkles': False}})
check('the sprinkles can be switched off',
      len(off['sprinkles']) == 0,
      f"{len(off['sprinkles'])} rendered with the box unticked")

# ------------------------------------------------------------- 2 x 2 ---
t2 = run('tablet', width=1100, height=1400)
check('under 1320 the row folds to two columns',
      t2['rowCols'] == '300px 300px', f"{t2['rowCols']}")

check('folded, the sprinkles go with the wide arrangement they were placed for',
      all(s['display'] == 'none' for s in t2['sprinkles']),
      f"display {t2['sprinkles'][0]['display']} at 1100px")

check('folded, the drops are eased off rather than kept at full strength',
      all(float(c['marginTop'][:-2]) < float(o['marginTop'][:-2])
          for c, o in zip(t2['cards'], cards) if o['marginTop'] != '0px'),
      f"{[c['marginTop'] for c in t2['cards']]} "
      f"(from {[c['marginTop'] for c in cards]})")

# ------------------------------------------------------------- phone ---
p = run('phone', width=749, height=2400)
check('on a phone it is a single column',
      p['rowCols'].count('px') == 1, f"{p['rowCols']}")

check('on a phone the drops are dropped entirely',
      all(c['marginTop'] == '0px' for c in p['cards']),
      f"{[c['marginTop'] for c in p['cards']]}")

check('on a phone the tilts are eased to about a third',
      p['cards'][0]['transform'] != cards[0]['transform']
      and p['cards'][0]['transform'] != 'none',
      f"still tilted, less so: {p['cards'][0]['transform']}")

check('on a phone the sprinkles are hidden',
      all(s['display'] == 'none' for s in p['sprinkles']),
      f"display {p['sprinkles'][0]['display']}")

check('no tilted card pushes the page sideways',
      p['scrollW'] <= p['vw'],
      f"scrollWidth {p['scrollW']} vs viewport {p['vw']}")

# ------------------------------------------------------ reduced motion ---
r = run('reduced', reduced=True)
check('reduced motion: the hover straighten does not animate',
      r['cards'][0]['transition'] == 'none' or r['cards'][0]['transition'] == 'all',
      f"transition-property {r['cards'][0]['transition']!r}")

check('reduced motion: the cards keep their tilt',
      r['cards'][0]['transform'] == cards[0]['transform'],
      f"{r['cards'][0]['transform']}")

failed = res.count(False)
print(f"\n{res.count(True)} passed, {failed} failed")
sys.exit(1 if failed else 0)
