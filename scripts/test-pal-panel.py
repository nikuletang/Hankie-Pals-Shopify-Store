"""Check the Pal panel: the dome's actual shape, and whether the section above
really holds still while it rises.

Both are things that look plausible when wrong — a dome that is the wrong
curve still looks like a dome, and a pin that silently does nothing just looks
like an ordinary scroll.
"""
import json, subprocess, sys, pathlib, re
from PIL import Image

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/pal-panel.liquid'
HERE = pathlib.Path(__file__).resolve().parent
PAL = (207, 225, 185)     # #CFE1B9
ABOVE = (216, 139, 109)   # #D88B6D, the stand-in section above


def build(overrides, name, above_h=600):
    """A page shaped like a Shopify theme: sections as siblings in <main>."""
    raw = HERE / f'pp-raw-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps(overrides), str(raw)], check=True, capture_output=True)
    text = raw.read_text(encoding='utf-8')
    head = text.split('<body>')[0] + '<body>'
    body = text.split('<body>')[1].rsplit('</body>', 1)[0]
    page = HERE / f'pp-{name}.html'
    page.write_text(
        head +
        '<main>'
        f'<div class="shopify-section" id="above" style="height:{above_h}px;background:#D88B6D"></div>'
        f'<div class="shopify-section hp-pp-section">{body}</div>'
        '<div class="shopify-section" style="height:1400px;background:#FCFBF6"></div>'
        '</main></body></html>', encoding='utf-8')
    return page


def probe(page, script, w=1200, h=800):
    out = pathlib.Path(str(page).replace('.html', '.probe.html'))
    out.write_text(page.read_text(encoding='utf-8').replace('</body>', script + '</body>'),
                   encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                          f'--window-size={w},{h}', '--virtual-time-budget=3000',
                          '--dump-dom', 'file://' + str(out)],
                         capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement from ' + str(page))
    return json.loads(m.group(1))


def shot(page, scroll, name, w=1200, h=800):
    pose = ("<script>window.addEventListener('load',function(){window.scrollTo(0,%d);});</script>"
            % scroll)
    out = HERE / f'pp-shot-{name}.html'
    out.write_text(page.read_text(encoding='utf-8').replace('</body>', pose + '</body>'),
                   encoding='utf-8')
    png = HERE / f'pp-{name}.png'
    subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                    f'--window-size={w},{h}', '--virtual-time-budget=3000',
                    f'--screenshot={png}', 'file://' + str(out)], capture_output=True)
    return Image.open(png).convert('RGB')


def near(px, ref, tol=14):
    return all(abs(a - b) <= tol for a, b in zip(px, ref))


res = []
def check(label, ok, detail):
    res.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


if __name__ == '__main__':
    page = build({}, 'base')

    # --- Does the section above actually hold still? ------------------------
    # update() is called directly after each scroll: the live handler is rAF
    # throttled, and headless virtual time renders about two frames, so waiting
    # on the throttle would be testing the harness rather than the logic.
    PIN = """<script>
      window.addEventListener('load', function () {
        var above = document.getElementById('above');
        var panel = document.querySelector('.hp-pp');
        var el = document.querySelector('hp-pal-panel');
        function at(y) {
          window.scrollTo(0, y);
          if (el && el.update) el.update();
          return { pinned: above.classList.contains('hp-pp-pin'),
                   pos: getComputedStyle(above).position,
                   above: Math.round(above.getBoundingClientRect().top),
                   panel: Math.round(panel.getBoundingClientRect().top) };
        }
        var out = {};
        [0, 300, 600, 900, 1200, 1800, 2400].forEach(function (y) {
          out['s' + y] = at(y);
        });
        // Back up the way we came: the pin has to come back, not stay off.
        out.back = at(600);
        document.title = 'RESULT' + JSON.stringify(out);
      });
    </script>"""
    d = probe(page, PIN)

    rising = [d['s300'], d['s600'], d['s900']]
    check('pinned while the Pal is on its way up',
          all(f['pinned'] and f['pos'] == 'sticky' for f in rising)
          and all(f['above'] == 0 for f in rising[1:]),
          '  '.join(f"{y}: pinned={d['s'+str(y)]['pinned']} top={d['s'+str(y)]['above']}"
                    for y in (300, 600, 900)))

    panels = [d['s' + str(y)]['panel'] for y in (300, 600, 900)]
    check('the Pal rises over it while it holds',
          panels == sorted(panels, reverse=True),
          f'panel top at those scrolls = {panels}')

    late = [d['s1800'], d['s2400']]
    check('let go once the Pal has covered the screen',
          all(not f['pinned'] and f['pos'] == 'static' for f in late)
          and late[0]['above'] < 0 and late[1]['above'] < late[0]['above'],
          '  '.join(f"{y}: pinned={d['s'+str(y)]['pinned']} pos={d['s'+str(y)]['pos']} "
                    f"top={d['s'+str(y)]['above']}" for y in (1800, 2400)))

    check('the release is not permanent — scrolling back up pins it again',
          d['back']['pinned'] and d['back']['above'] == 0,
          f"after releasing at 2400, back at 600: pinned={d['back']['pinned']}, "
          f"top={d['back']['above']}")

    # --- Turning it off must really turn it off -----------------------------
    d2 = probe(build({'settings': {'pin_previous': False}}, 'nopin'), PIN)
    moved = [d2['s' + str(y)]['above'] for y in (300, 600, 900)]
    check('with the pin off, the section above scrolls away as usual',
          all(not d2['s' + str(y)]['pinned'] for y in (300, 600, 900))
          and moved == sorted(moved, reverse=True),
          f'its top = {moved}, never pinned')

    # --- The face is a Pal, and it blinks -----------------------------------
    FACE = """<script>
      window.addEventListener('load', function () {
        function has(sel) { return !!document.querySelector(sel); }
        var eye = document.querySelector('.hp-pp__eye');
        document.title = 'RESULT' + JSON.stringify({
          ears: document.querySelectorAll('.hp-pp__ear').length,
          cheeks: document.querySelectorAll('.hp-pp__cheek').length,
          muzzle: has('.hp-pp__muzzle'), nose: has('.hp-pp__nose'),
          smile: has('.hp-pp__smile'),
          blink: getComputedStyle(eye).animationName,
          period: getComputedStyle(eye).animationDuration,
          highlight: getComputedStyle(eye, '::after').backgroundColor
        });
      });
    </script>"""
    d = probe(page, FACE)
    check('the face has ears, cheeks and a muzzle with a nose and smile',
          d['ears'] == 2 and d['cheeks'] == 2 and d['muzzle'] and d['nose'] and d['smile'],
          f"{d['ears']} ears, {d['cheeks']} cheeks, muzzle {d['muzzle']}, "
          f"nose {d['nose']}, smile {d['smile']}")
    check('the eyes blink, and have a catchlight',
          d['blink'] == 'hp-pp-blink' and d['period'] == '6s'
          and '255, 255, 255' in d['highlight'],
          f"animation {d['blink']} every {d['period']}, catchlight {d['highlight']}")

    d = probe(build({'settings': {'blink': False}}, 'noblink'), FACE)
    check('blink can be switched off', d['blink'] == 'none', f"animation {d['blink']}")



    # --- The dome's shape ---------------------------------------------------
    # Scrolled so the panel's top edge is on screen, then read the curve off
    # the pixels the way the reference video was read.
    # The face is turned off for this one: the ears sit right on the dome's
    # edge at some columns, so a scan for the body colour would find it below
    # an ear and report the curve as deeper than it is.
    img = shot(build({'settings': {'show_face': False}}, 'domeonly'), 600, 'dome')
    vpw, vph = 1185, 713          # the rendered area inside the window
    def edge(x):
        for y in range(0, vph):
            if near(img.getpixel((x, y)), PAL):
                return y
        return None
    # The curve is checked against the ellipse it is supposed to be, rather
    # than against a rule of thumb about how far it should drop: a corner with
    # radii (rx, ry) puts its edge at ry - ry*sqrt(1 - ((rx-x)/rx)^2) below the
    # apex. Only part of the curve is ever on screen at once, so a test that
    # needed to see all of it would be testing the screenshot, not the shape.
    import math
    rx = vpw / 2
    ry = 606.05                     # the radius the browser reported above
    xs = [int(vpw * f) for f in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)]
    prof = [(x, edge(x)) for x in xs]
    apex = min(y for _, y in prof if y is not None)
    rows = []
    worst = 0
    for x, y in prof:
        if y is None:
            continue
        dx = min(x, vpw - x)
        want = ry - ry * math.sqrt(max(0.0, 1 - ((rx - dx) / rx) ** 2))
        got = y - apex
        worst = max(worst, abs(got - want))
        rows.append(f'{int(x/vpw*100)}%: {got:.0f} vs {want:.0f}')
    # Five columns is what fits on screen at once: past about 30% from either
    # edge the curve has already dropped below the viewport.
    check('the top edge follows the ellipse it is meant to be',
          worst <= 4 and len(rows) >= 5,
          'depth below the apex, measured vs predicted — ' + ',  '.join(rows)
          + f'   (worst {worst:.1f}px)')

    check('the corners above the dome are not the Pal',
          not near(img.getpixel((3, 3)), PAL) and not near(img.getpixel((vpw - 4, 3)), PAL),
          f"top corners {img.getpixel((3,3))}, {img.getpixel((vpw-4,3))}")

    # --- Dome height follows its setting ------------------------------------
    for vh, tag in ((85, 'tall'), (40, 'shallow')):
        p2 = build({'settings': {'dome_height': vh}}, f'cap{vh}')
        D = """<script>
          window.addEventListener('load', function () {
            var el = document.querySelector('.hp-pp');
            var cs = getComputedStyle(el);
            document.title = 'RESULT' + JSON.stringify({
              radius: cs.borderTopLeftRadius,
              vh: window.innerHeight,
              faceTop: Math.round(document.querySelector('.hp-pp__face')
                       .getBoundingClientRect().top - el.getBoundingClientRect().top)
            });
          });
        </script>"""
        d = probe(p2, D)
        want = round(d['vh'] * vh / 100)
        got = float(d['radius'].split()[-1].rstrip('px'))
        check(f'dome height {vh}vh renders as {want}px of rise',
              abs(got - want) <= 2, f"border radius {d['radius']}")
        check(f'the face sits 22% down that dome at {vh}vh',
              abs(d['faceTop'] - want * 0.22) <= 4,
              f"face {d['faceTop']}px from the top, wanted {round(want*0.22)}px")

    print(f"\n{sum(res)} passed, {len(res) - sum(res)} failed")
