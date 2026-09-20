"""Drive the why-choose reveal in real Chromium and report what it did.

Every case here is one the section has to survive: in view on load, below the
fold then scrolled to, reduced motion, no IntersectionObserver, and the theme
editor pulling the section out of the DOM and putting it back.
"""
import json, subprocess, sys, pathlib, re, textwrap

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/why-choose.liquid'
HERE = pathlib.Path(__file__).resolve().parent


def render(overrides, name):
    out = HERE / name
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps(overrides), str(out)], check=True,
                   capture_output=True)
    return out


def run(page, probe, flags=(), spacer=False, kill_io=False):
    html = pathlib.Path(page).read_text(encoding='utf-8')
    if spacer:
        # Push the section below the fold so the observer has to do its job.
        html = html.replace('<body>', '<body><div style="height:1600px"></div>')
    if kill_io:
        html = html.replace('<body>', '<body><script>delete window.IntersectionObserver;</script>')
    probed = html.replace('</body>', f'<script>{probe}</script></body>')
    tmp = pathlib.Path(page).with_suffix('.t.html')
    tmp.write_text(probed, encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                          '--window-size=900,800', '--virtual-time-budget=9000',
                          *flags, '--dump-dom', 'file://' + str(tmp)],
                         capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement back from ' + str(page))
    return json.loads(m.group(1))


REPORT = """
  function report(extra) {
    var root = document.querySelector('.hp-why');
    var items = document.querySelectorAll('[data-reveal]');
    var o = extra || {};
    o.armed = root.classList.contains('hp-why--reveal');
    o.inClass = [];
    o.delay = [];
    items.forEach(function (el) {
      o.inClass.push(el.classList.contains('is-in'));
      o.delay.push(getComputedStyle(el).transitionDelay);
    });

    // Headless virtual time produces almost no animation frames, so a computed
    // value read mid-transition still reports the START of it. Cutting the
    // transitions makes the cascade resolve straight to its target, which is
    // what these cases are actually asserting about.
    var kill = document.createElement('style');
    kill.textContent = '*{transition:none !important;animation:none !important}';
    document.head.appendChild(kill);
    void document.body.offsetHeight;

    o.opacity = [];
    o.transform = [];
    items.forEach(function (el) {
      var cs = getComputedStyle(el);
      o.opacity.push(Math.round(parseFloat(cs.opacity) * 100) / 100);
      o.transform.push(cs.transform === 'none' ? 'none' : 'moved');
    });
    document.title = 'RESULT' + JSON.stringify(o);
  }
"""

SETTLED = REPORT + """
  // Long enough for the stagger plus the transition plus the delay cleanup.
  setTimeout(function () { report({}); }, 2500);
"""

EARLY = REPORT + """
  // Before any scroll: below the fold, nothing should have arrived yet.
  setTimeout(function () { report({scrollY: window.scrollY}); }, 400);
"""

# Chromium under --virtual-time-budget runs about two animation frames, so no
# rendering lifecycle happens after a programmatic scroll and the browser never
# recomputes intersection. The case above already proves a real observer
# callback drives the reveal; what is left to check is this element's own
# handling of an entry, which is exercised directly here.
ENTERS = REPORT + """
  setTimeout(function () {
    var el = document.querySelector('hp-why-reveal');
    el.onIntersect([{ isIntersecting: true }]);
    setTimeout(function () { report({}); }, 1800);
  }, 300);
"""

LEAVES_NO_REPLAY = REPORT + """
  setTimeout(function () {
    var el = document.querySelector('hp-why-reveal');
    el.onIntersect([{ isIntersecting: true }]);
    el.onIntersect([{ isIntersecting: false }]);
    setTimeout(function () { report({}); }, 1800);
  }, 300);
"""

LEAVES_REPLAY = REPORT + """
  setTimeout(function () {
    var el = document.querySelector('hp-why-reveal');
    el.onIntersect([{ isIntersecting: true }]);
    el.onIntersect([{ isIntersecting: false }]);
    setTimeout(function () { report({}); }, 1800);
  }, 300);
"""

TEARDOWN = REPORT + """
  // What the theme editor does on every settings change.
  setTimeout(function () {
    var sec = document.querySelector('.hp-why');
    var parent = sec.parentNode, clone = sec.cloneNode(true);
    parent.removeChild(sec);
    parent.appendChild(clone);
  }, 900);
  setTimeout(function () { report({}); }, 3200);
"""


def show(label, d, expect):
    ok = expect(d)
    print(f"{'PASS' if ok else 'FAIL'}  {label}")
    print(f"        armed={d['armed']}  opacity={d['opacity']}  transform={d['transform']}"
          f"  is-in={sum(d['inClass'])}/{len(d['inClass'])}" +
          (f"  scrollY={d['scrollY']}" if 'scrollY' in d else ''))
    return ok

if __name__ == '__main__':
    rise = render({}, 'anim-rise.html')
    results = []

    results.append(show(
        'in view on load: every column arrives, delays cleared',
        run(rise, SETTLED),
        lambda d: all(o == 1 for o in d['opacity'])
                  and all(t == 'none' for t in d['transform'])
                  and all(d['inClass'])
                  and all(set(x.split(', ')) == {'0s'} for x in d['delay'])))

    results.append(show(
        'below the fold: still hidden before any scroll',
        run(rise, EARLY, spacer=True),
        lambda d: d['armed'] and all(o == 0 for o in d['opacity'])
                  and all(t == 'moved' for t in d['transform'])))

    results.append(show(
        'observer reports it entered: arrives, un-translated',
        run(rise, ENTERS, spacer=True),
        lambda d: all(d['inClass']) and all(o == 1 for o in d['opacity'])
                  and all(t == 'none' for t in d['transform'])))

    results.append(show(
        'replay off: leaving view leaves it settled',
        run(rise, LEAVES_NO_REPLAY, spacer=True),
        lambda d: all(d['inClass']) and all(o == 1 for o in d['opacity'])))

    replay = render({'settings': {'reveal_replay': True}}, 'anim-replay.html')
    results.append(show(
        'replay on: leaving view puts it back to the start state',
        run(replay, LEAVES_REPLAY, spacer=True),
        lambda d: not any(d['inClass']) and all(o == 0 for o in d['opacity'])
                  and all(t == 'moved' for t in d['transform'])))

    results.append(show(
        'reduced motion: visible, un-translated, no start state',
        run(rise, SETTLED, flags=['--force-prefers-reduced-motion']),
        lambda d: not d['armed'] and all(o == 1 for o in d['opacity'])
                  and all(t == 'none' for t in d['transform'])))

    results.append(show(
        'no IntersectionObserver: class dropped, copy visible and un-translated',
        run(rise, EARLY, spacer=True, kill_io=True),
        lambda d: not d['armed'] and all(o == 1 for o in d['opacity'])
                  and all(t == 'none' for t in d['transform'])))

    results.append(show(
        'section torn out and re-inserted (theme editor): arrives again',
        run(rise, TEARDOWN),
        lambda d: all(o == 1 for o in d['opacity'])))

    for style, moved in (('fade', False), ('pop', True), ('none', False)):
        page = render({'settings': {'motion': style}}, f'anim-{style}.html')
        d = run(page, EARLY, spacer=True)
        results.append(show(
            f'motion={style}: start state is {"a transform" if moved else "opacity only" if style=="fade" else "absent"}',
            d,
            lambda d, m=moved, s=style: (
                (not d['armed'] and all(o == 1 for o in d['opacity'])) if s == 'none'
                else d['armed'] and all(o == 0 for o in d['opacity'])
                     and all((t == 'moved') == m for t in d['transform']))))

    print()
    print(f"{sum(results)} passed, {len(results) - sum(results)} failed")
