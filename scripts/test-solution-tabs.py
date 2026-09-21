"""Check the tabs sliding in on the solution section.

The interesting part is not the slide, it is what happens after it. This
element already owns its transform — the hover lift is `.hp-sol__tab:hover` —
and a reveal rule scoped under the section class outranks it, so a reveal left
in place would kill the hover for the rest of the page's life. The class comes
off when the last tab lands, and that is what most of this checks: that the
section afterwards is exactly what it was before.

Same harness rules as the other reveals: an IntersectionObserver needs a
rendering step a quiet page never schedules, so the checks that are about the
animation drive the element directly and whether the observer fires is one
check of its own, with the page kept ticking while it is waited for.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
SECTION = ROOT / 'sections' / 'solution-tabs.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

SNAP = """
function snap() {
  var root = document.querySelector('.hp-sol');
  var list = document.querySelector('.hp-sol__tabs');
  return {
    cls: root.className,
    listRole: list ? list.getAttribute('role') : null,
    tabRoles: [].map.call(document.querySelectorAll('.hp-sol__tabs > *'), function (el) {
      return el.tagName.toLowerCase() + ':' + el.getAttribute('role');
    }),
    selected: [].map.call(document.querySelectorAll('.hp-sol__tab'), function (el) {
      return el.getAttribute('aria-selected');
    }),
    tabs: [].map.call(document.querySelectorAll('.hp-sol__tab'), function (el) {
      var c = getComputedStyle(el);
      return {
        isIn: el.classList.contains('is-in'),
        opacity: Math.round(parseFloat(c.opacity) * 100) / 100,
        transform: c.transform,
        delay: c.transitionDelay,
        inlineDelay: el.style.transitionDelay,
        transitionProp: c.transitionProperty,
        left: Math.round(el.getBoundingClientRect().left)
      };
    })
  };
}
"""

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

POLL = """
function when(test, done, tries) {
  if (tries === undefined) tries = 200;
  void document.body.offsetHeight;
  if (test() || tries <= 0) return done();
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
function arrived() { return !!document.querySelector('.hp-sol__tab.is-in'); }
function done_() { return !document.querySelector('.hp-sol--reveal'); }
"""


def probe(mode):
    if mode == 'play':
        return ("<script>" + SNAP + POLL +
                "var el=document.querySelector('hp-sol-reveal');"
                "if(el&&el.play) el.play(); setTimeout(report,60);</script>")
    if mode == 'finished':
        return (TICK + "<script>" + SNAP + POLL +
                "var el=document.querySelector('hp-sol-reveal');"
                "if(el&&el.play) el.play(); when(done_, report);</script>")
    if mode == 'plain':
        return "<script>" + SNAP + POLL + "setTimeout(report,400);</script>"
    return TICK + "<script>" + SNAP + POLL + "when(arrived, report);</script>"


def run(overrides, name, mode='play', flags=(), extra_head='', budget=9000):
    page = TMP / f'st-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    body = page.read_text(encoding='utf-8').replace('<body>', '<body>' + extra_head)
    page.write_text(body.replace('</body>', probe(mode) + '</body>'), encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--window-size=1280,900', f'--virtual-time-budget={budget}', *flags, '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def tx(t):
    """The x translation out of a computed matrix."""
    if t == 'none':
        return 0.0
    n = [float(x) for x in re.findall(r'(-?[\d.]+)', t)]
    return n[4] if len(n) >= 6 else 0.0


def ty(t):
    if t == 'none':
        return 0.0
    n = [float(x) for x in re.findall(r'(-?[\d.]+)', t)]
    return n[5] if len(n) >= 6 else 0.0


# ------------------------------------------------------------ the arrival --
start = run({'settings': {'reveal_stagger': 0, 'reveal_duration': 1200}}, 'start',
            mode='plain')
check('the tabs start out of sight, off to the right',
      all(t['opacity'] == 0 for t in start['tabs'])
      and all(abs(tx(t['transform']) - 56) < 1 for t in start['tabs']),
      f"opacity {[t['opacity'] for t in start['tabs']]}, "
      f"x {[round(tx(t['transform'])) for t in start['tabs']]}")

d = run({}, 'play')
check('each is told to arrive, one after the next',
      all(t['isIn'] for t in d['tabs'])
      and [t['delay'] for t in d['tabs']] == ['0s', '0.11s', '0.22s'],
      f"{[t['delay'] for t in d['tabs']]}")

fin = run({}, 'finished', mode='finished')
check('and they finish where they belong',
      all(t['opacity'] == 1 for t in fin['tabs'])
      and all(t['transform'] in ('none', 'matrix(1, 0, 0, 1, 0, 0)') for t in fin['tabs']),
      f"opacity {[t['opacity'] for t in fin['tabs']]}, "
      f"transform {fin['tabs'][0]['transform']}")

# The point of the whole design: nothing of the reveal survives it.
check('the reveal takes itself off the section when it is done',
      'hp-sol--reveal' not in fin['cls'], f"class \"{fin['cls']}\"")
check('so the hover lift is not outranked for the rest of the page',
      all(not t['isIn'] for t in fin['tabs'])
      and all(t['inlineDelay'] == '' for t in fin['tabs']),
      'is-in and the inline delays are gone too')
plain = run({'settings': {'motion': 'none'}}, 'nomotion', mode='plain')
check('and the section ends up styled exactly as it would with no motion at all',
      [t['transitionProp'] for t in fin['tabs']]
      == [t['transitionProp'] for t in plain['tabs']],
      f"transition-property {fin['tabs'][0]['transitionProp']}")

# --------------------------------------------------------------- the paths --
for style, axis, sign, where in (('right', tx, 1, '56px to the right'),
                                 ('left', tx, -1, '56px to the left'),
                                 ('up', ty, 1, '56px below where it lands')):
    n = run({'settings': {'motion': style, 'reveal_stagger': 0,
                          'reveal_duration': 1200}}, 'dir-' + style, mode='plain')
    got = axis(n['tabs'][0]['transform'])
    other = (ty if axis is tx else tx)(n['tabs'][0]['transform'])
    check(f'"{style}" starts {where}, and only there',
          abs(got - 56 * sign) < 1 and abs(other) < 1
          and 'hp-sol--rev-' + style in n['cls'],
          f"{round(got)}px on its own axis, {round(other)}px on the other")

fade = run({'settings': {'motion': 'fade', 'reveal_duration': 1200}}, 'dir-fade',
           mode='plain')
check('"fade" does not move them at all',
      fade['tabs'][0]['transform'] in ('none', 'matrix(1, 0, 0, 1, 0, 0)')
      and fade['tabs'][0]['opacity'] == 0,
      f"transform {fade['tabs'][0]['transform']}, opacity {fade['tabs'][0]['opacity']}")

far = run({'settings': {'reveal_distance': 160, 'reveal_duration': 1200}}, 'far',
          mode='plain')
check('the distance setting is the distance',
      abs(tx(far['tabs'][0]['transform']) - 160) < 1,
      f"{round(tx(far['tabs'][0]['transform']))}px")

# ------------------------------------------------------- nothing else moved --
check('the tablist is still a tablist of buttons',
      d['listRole'] == 'tablist'
      and all(r == 'button:tab' for r in d['tabRoles']),
      f"{d['listRole']} containing {d['tabRoles']}")
check('and the first tab is still the selected one',
      d['selected'] == ['true', 'false', 'false'], f"{d['selected']}")

# -------------------------------------------------------------- bail-outs ---
off = run({'settings': {'motion': 'none'}}, 'none', mode='plain')
check('"none" leaves the section alone entirely',
      'hp-sol--reveal' not in off['cls']
      and all(t['opacity'] == 1 for t in off['tabs']),
      f"class \"{off['cls']}\"")
rm = run({}, 'reduced', mode='plain', flags=('--force-prefers-reduced-motion',))
check('reduced motion drops it, tabs visible and in place',
      all(t['opacity'] == 1 for t in rm['tabs'])
      and 'hp-sol--reveal' not in rm['cls'],
      f"opacity {[t['opacity'] for t in rm['tabs']]}")
noio = run({}, 'noio', mode='plain',
           extra_head='<script>delete window.IntersectionObserver;</script>')
check('with no IntersectionObserver the tabs are simply there',
      all(t['opacity'] == 1 for t in noio['tabs'])
      and 'hp-sol--reveal' not in noio['cls'],
      f"opacity {[t['opacity'] for t in noio['tabs']]}")

observed = run({}, 'observed', mode='wired', budget=20000)
check('the tabs wait for the list to come into view, then go',
      all(t['isIn'] for t in observed['tabs']) or 'hp-sol--reveal' not in observed['cls'],
      f"is-in {[t['isIn'] for t in observed['tabs']]}")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
