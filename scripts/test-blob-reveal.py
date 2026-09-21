"""Check the blobs' entrance on the problem section.

Two things make this worth measuring rather than watching. A reveal's failure
mode is invisible content — a section stuck at opacity 0 looks like an empty
page, not like a broken animation — so every bail-out path is exercised here.
And the wobble leaves border-radius out of its last keyframe so each blob
settles back to its own lopsided shape; that works because the browser builds
the missing 100% from the underlying rule, and if it stopped working all three
blobs would quietly end up the same shape.

Chromium under --virtual-time-budget does not advance animation timelines: an
animation sits at its first frame however long the budget is, and a finished
promise never settles. So the end state is not waited for, it is forced —
animation-duration goes to 0 and the fill mode resolves straight to the last
keyframe. The start state is read from a normal run, early, before the script's
own timers have tidied up after it.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
SECTION = ROOT / 'sections' / 'problem-cards.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

SNAP = """
function snap() {
  var root = document.querySelector('.hp-problem');
  return {
    cls: root.className,
    cards: [].map.call(document.querySelectorAll('.hp-problem__card'), function (el) {
      var c = getComputedStyle(el);
      return {
        isIn: el.classList.contains('is-in'),
        opacity: Math.round(parseFloat(c.opacity) * 100) / 100,
        name: c.animationName,
        delay: c.animationDelay,
        inlineDelay: el.style.animationDelay,
        radius: c.borderTopLeftRadius + ' / ' + c.borderBottomRightRadius,
        transform: c.transform
      };
    })
  };
}
"""

# Shortening the animation to 0s does not settle it either: with no animation
# frames the animation never starts, so its fill never applies and the blob
# stays at the hidden underlying value. Taking the animation away entirely
# leaves the cascade to answer, which is the same question — every last
# keyframe here is opacity 1 and transform none, so what the rules resolve to
# with no animation is where the animation lands.
# A page with nothing to draw never runs "update the rendering", and an
# intersection is computed in that step — so the observer may simply never
# deliver. An animation that never ends keeps the loop turning. It is on a
# pseudo element of the body, so it touches nothing being measured.
TICK = """<style>
  @keyframes hp-test-tick { from { opacity: 0.99; } to { opacity: 1; } }
  body::after {
    content: '';
    position: fixed;
    width: 1px;
    height: 1px;
    top: 0;
    left: 0;
    animation: hp-test-tick 50ms linear infinite;
  }
</style>"""

SETTLE = """<style>
  .hp-problem__card.is-in { animation: none !important; }
</style>"""


# Waiting a fixed number of milliseconds for the observer to fire is a guess,
# and a guess that was wrong about one run in five here — a style would be
# snapshotted before its class landed and read as having no animation at all.
# These wait for the state itself, and fall back to snapshotting anyway so the
# bail-out cases, where the state never arrives, still report.
POLL = """
function when(test, done, tries) {
  if (tries === undefined) tries = 200;
  void document.body.offsetHeight;
  if (test() || tries <= 0) return done();
  // Two nudges, because neither is reliable alone. Reading a layout property
  // forces style and layout. Asking for a frame is what actually schedules
  // "update the rendering", the step an intersection is computed in — but
  // requestAnimationFrame never fires at all under a virtual time budget, so
  // it cannot be waited on: whichever of the two arrives first continues, and
  // the timer guarantees one of them does.
  var moved = false;
  function step() {
    if (moved) return;
    moved = true;
    when(test, done, tries - 1);
  }
  try { requestAnimationFrame(step); } catch (e) {}
  setTimeout(step, 40);
}
function report() { document.title = 'RESULT' + JSON.stringify(snap()); }
function arrived() { return !!document.querySelector('.hp-problem__card.is-in'); }
function tidied() {
  var els = document.querySelectorAll('.hp-problem__card');
  for (var i = 0; i < els.length; i++) {
    if (els[i].style.animationDelay !== '') return false;
  }
  return arrived();
}
"""


# IntersectionObserver delivery is itself lifecycle-dependent and does not
# arrive reliably under a virtual time budget — about one run in five it never
# fires, and every assertion downstream reads as a failure of the animation
# rather than of the harness. So the checks that are about the animation drive
# the element directly, and whether the observer fires at all is one check of
# its own, with room to breathe.
def probe(mode):
    if mode == 'play':
        kick = ("var el = document.querySelector('hp-problem-reveal');"
                "if (el && el.play) el.play();"
                "setTimeout(report, 60);")
        return "<script>" + SNAP + POLL + kick + "</script>"
    if mode == 'plain':
        return "<script>" + SNAP + POLL + "setTimeout(report, 400);</script>"
    wait = {'wired': 'arrived', 'tidied': 'tidied'}[mode]
    return TICK + "<script>" + SNAP + POLL + f"when({wait}, report);</script>"


def run(overrides, name, mode='play', settle=False, flags=(), extra_head='',
        budget=6000):
    page = TMP / f'pb-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    body = page.read_text(encoding='utf-8').replace('<body>', '<body>' + extra_head)
    tail = (SETTLE if settle else '') + probe(mode)
    page.write_text(body.replace('</body>', tail + '</body>'), encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--window-size=1200,900', f'--virtual-time-budget={budget}', *flags, '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


# ------------------------------------------------------------- the default --
observed = run({}, 'pop-observed', mode='wired', budget=15000)
check('the blobs wait for the section to come into view, then go',
      all(c['isIn'] for c in observed['cards']),
      f"is-in {[c['isIn'] for c in observed['cards']]} once the observer fires")

early = run({}, 'pop')
check('the blobs are a bubble by default, not a fade',
      all(c['name'] == 'hp-problem-pop' for c in early['cards']),
      f"{[c['name'] for c in early['cards']]}")
check('every blob is told to arrive',
      all(c['isIn'] for c in early['cards']) and len(early['cards']) == 3,
      f"{sum(1 for c in early['cards'] if c['isIn'])} of {len(early['cards'])}")
check('they come one after the next rather than together',
      [c['delay'] for c in early['cards']] == ['0s', '0.13s', '0.26s'],
      f"{[c['delay'] for c in early['cards']]}")
check('and each starts from nothing rather than appearing first',
      all(c['opacity'] == 0 for c in early['cards']),
      f"opacity at the first frame: {[c['opacity'] for c in early['cards']]}")

late = run({}, 'pop-late', mode='tidied', budget=15000)
check('the delay is cleared once each has landed, so it holds nothing else back',
      all(c['inlineDelay'] == '' for c in late['cards']),
      f"inline delays after 2.6s: {[c['inlineDelay'] for c in late['cards']]!r}")

settled = run({}, 'pop-settled', settle=True)
check('and every blob ends up fully there, untransformed',
      all(c['opacity'] == 1 for c in settled['cards'])
      and all(c['transform'] in ('none', 'matrix(1, 0, 0, 1, 0, 0)')
              for c in settled['cards']),
      f"opacity {[c['opacity'] for c in settled['cards']]}, "
      f"transform {settled['cards'][0]['transform']}")

gap = run({'settings': {'reveal_stagger': 0}}, 'nostagger')
check('the stagger can be turned off',
      [c['delay'] for c in gap['cards']] == ['0s', '0s', '0s'],
      f"{[c['delay'] for c in gap['cards']]}")

# ---------------------------------------------------------------- styles ----
for style in ('fade', 'rise', 'pop', 'squish', 'wobble'):
    a = run({'settings': {'motion': style}}, style)
    b = run({'settings': {'motion': style}}, style + '-settled', settle=True)
    check(f'"{style}" plays its own animation and settles',
          all(c['name'] == f'hp-problem-{style}' for c in a['cards'])
          and all(c['opacity'] == 1 for c in b['cards']),
          f"animation-name {a['cards'][0]['name']}, settles at "
          f"opacity {b['cards'][0]['opacity']}")

# The one that would fail silently: all three blobs the same shape at the end.
# Two halves, because the mechanism is split between the keyframes and the
# rule underneath them. Half one: the last keyframe must not declare a radius,
# or every blob ends up wearing whichever one it does declare.
KEYFRAMES = """<script>
  function frames(name) {
    var out = [];
    for (var i = 0; i < document.styleSheets.length; i++) {
      var rules;
      try { rules = document.styleSheets[i].cssRules; } catch (e) { continue; }
      for (var j = 0; rules && j < rules.length; j++) {
        if (rules[j].type === CSSRule.KEYFRAMES_RULE && rules[j].name === name) {
          for (var k = 0; k < rules[j].cssRules.length; k++) {
            out.push({ at: rules[j].cssRules[k].keyText,
                       radius: rules[j].cssRules[k].style.borderRadius || '' });
          }
        }
      }
    }
    return out;
  }
  document.title = 'RESULT' + JSON.stringify({ wobble: frames('hp-problem-wobble') });
</script>"""
page = TMP / 'pb-keyframes.html'
subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                '{}', str(page)], check=True, capture_output=True)
page.write_text(page.read_text(encoding='utf-8').replace('</body>', KEYFRAMES + '</body>'),
                encoding='utf-8')
dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
    '--window-size=1200,900', '--virtual-time-budget=3000', '--dump-dom',
    'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
kf = json.loads(re.search(r'<title>RESULT(.*?)</title>', dom, re.S).group(1))['wobble']
last = [f for f in kf if f['at'] in ('100%', 'to')]
check('the wobble does not dictate a shape in its last frame',
      last and all(f['radius'] == '' for f in last)
      and any(f['radius'] for f in kf),
      f"frames {[f['at'] for f in kf]}; "
      f"radius set at {[f['at'] for f in kf if f['radius']]}, not at {[f['at'] for f in last]}")

# Half two: the rule underneath must give the three blobs three shapes, which
# is what an absent last keyframe resolves to.
plain = run({'settings': {'motion': 'none'}}, 'none-shape', mode='plain')
wob = run({'settings': {'motion': 'wobble'}}, 'wobble-shape', settle=True)
shapes = [c['radius'] for c in wob['cards']]
check('so each blob lands back on its own lopsided shape',
      len(set(shapes)) == 3 and shapes == [c['radius'] for c in plain['cards']],
      f"{len(set(shapes))} distinct shapes; same as the unanimated section: "
      f"{shapes == [c['radius'] for c in plain['cards']]}")

# ------------------------------------------------------------- bail-outs ----
off = run({'settings': {'motion': 'none'}}, 'none', mode='plain')
check('"none" leaves the section alone entirely',
      'hp-problem--reveal' not in off['cls']
      and all(c['opacity'] == 1 and c['name'] == 'none' for c in off['cards']),
      f"class \"{off['cls']}\", animation {off['cards'][0]['name']}")

rm = run({}, 'reduced', mode='plain', flags=('--force-prefers-reduced-motion',))
check('reduced motion drops the whole thing, blobs visible',
      all(c['opacity'] == 1 for c in rm['cards'])
      and 'hp-problem--reveal' not in rm['cls'],
      f"class \"{rm['cls']}\", opacity {[c['opacity'] for c in rm['cards']]}")

noio = run({}, 'noio', mode='plain',
           extra_head='<script>delete window.IntersectionObserver;</script>')
check('with no IntersectionObserver the blobs are simply there',
      all(c['opacity'] == 1 for c in noio['cards'])
      and 'hp-problem--reveal' not in noio['cls'],
      f"class \"{noio['cls']}\", opacity {[c['opacity'] for c in noio['cards']]}")

torn = run({}, 'torndown', settle=True, extra_head="""<script>
  // The theme editor pulls a section out and puts it back on every change.
  window.addEventListener('DOMContentLoaded', function () {
    var el = document.querySelector('hp-problem-reveal');
    var parent = el.parentNode, next = el.nextSibling;
    el.remove();
    parent.insertBefore(el, next);
  });
</script>""")
check('pulled out and put back, it still reveals rather than sticking hidden',
      all(c['opacity'] == 1 for c in torn['cards']),
      f"is-in {[c['isIn'] for c in torn['cards']]}, "
      f"opacity {[c['opacity'] for c in torn['cards']]}")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
