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
    # bool(), because `a and b` on strings returns the string, and a count of
    # passes then fails on the sum rather than on the assertion.
    ok = bool(ok)
    res.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


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



    # --- The dome -----------------------------------------------------------
    # Checked against the ellipse it is meant to be rather than against a rule
    # of thumb about how far it should drop: a corner with radii (rx, ry) puts
    # its edge ry - ry*sqrt(1 - ((rx-x)/rx)^2) below the apex. The face is off
    # for this — the ears sit on the dome's edge at some columns, and a scan
    # for the body colour would find it below an ear and read the curve as
    # twice as deep.
    import math
    img = shot(build({'settings': {'show_face': False}}, 'domeonly'), 600, 'dome')
    vpw, vph = 1185, 713

    def edge(x):
        for y in range(0, vph):
            if near(img.getpixel((x, y)), PAL):
                return y
        return None

    rx = vpw / 2
    ry = 606.05
    xs = [int(vpw * f) for f in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)]
    prof = [(x, edge(x)) for x in xs]
    apex = min(y for _, y in prof if y is not None)
    rows, worst = [], 0
    for x, y in prof:
        if y is None:
            continue
        dx = min(x, vpw - x)
        want = ry - ry * math.sqrt(max(0.0, 1 - ((rx - dx) / rx) ** 2))
        worst = max(worst, abs((y - apex) - want))
        rows.append(f'{int(x/vpw*100)}%: {y - apex:.0f} vs {want:.0f}')

    # Five columns is what fits on screen at once: past about 30% from either
    # edge the curve has already dropped below the viewport.
    check('the top edge follows the ellipse it is meant to be',
          worst <= 4 and len(rows) >= 5,
          'depth below the apex, measured vs predicted — ' + ',  '.join(rows)
          + f'   (worst {worst:.1f}px)')

    check('the corners above the dome are not the Pal',
          not near(img.getpixel((3, 3)), PAL) and not near(img.getpixel((vpw - 4, 3)), PAL),
          f"top corners {img.getpixel((3,3))}, {img.getpixel((vpw-4,3))}")

    # --- The shoulder depth the pin relies on -------------------------------
    for vh, tag in ((85, 'tall'), (40, 'shallow')):
        D = """<script>
          window.addEventListener('load', function () {
            var el = document.querySelector('.hp-pp');
            document.title = 'RESULT' + JSON.stringify({
              vh: window.innerHeight,
              gauge: document.querySelector('.hp-pp__gauge').offsetHeight,
              faceTop: Math.round(document.querySelector('.hp-pp__face')
                       .getBoundingClientRect().top - el.getBoundingClientRect().top)
            });
          });
        </script>"""
        d = probe(build({'settings': {'dome_height': vh}}, f'cap{vh}'), D)
        want = round(d['vh'] * vh / 100)
        check(f'at {vh}vh the dome rises {want}px, which is what the pin reads',
              abs(d['gauge'] - want) <= 2, f"gauge {d['gauge']}px")
        check(f'the face sits 22% down the dome at {vh}vh',
              abs(d['faceTop'] - want * 0.22) <= 4,
              f"face {d['faceTop']}px from the top, wanted {round(want*0.22)}px")

    # --- Ear styles ---------------------------------------------------------
    EARS = """<script>
      window.addEventListener('load', function () {
        var ear = document.querySelector('.hp-pp__ear');
        var cs = getComputedStyle(ear);
        document.title = 'RESULT' + JSON.stringify({
          cls: document.querySelector('.hp-pp').className,
          radius: cs.borderTopLeftRadius + ' / ' + cs.borderBottomLeftRadius,
          origin: cs.transformOrigin,
          h: Math.round(ear.getBoundingClientRect().height),
          w: Math.round(ear.getBoundingClientRect().width)
        });
      });
    </script>"""
    seen = {}
    for style in ('cow', 'bunny', 'dog'):
        d = probe(build({'settings': {'ear_style': style}}, 'ear-' + style), EARS)
        seen[style] = d
        check(f'{style} ears are their own shape',
              f'hp-pp--ears-{style}' in d['cls'] and d['radius'] and d['origin'],
              f"radius {d['radius']}, pivot {d['origin']}")

    check('the three ear styles really differ from one another',
          len({seen[k]['radius'] for k in seen}) == 3
          and len({seen[k]['origin'] for k in seen}) == 3,
          '  '.join(f"{k}: pivot {seen[k]['origin']}" for k in seen))

    # --- Nose, whiskers and the signature sparkle ---------------------------
    NOSE = """<script>
      window.addEventListener('load', function () {
        var nose = document.querySelector('.hp-pp__nose');
        var sp = document.querySelector('.hp-pp__sparkle');
        document.title = 'RESULT' + JSON.stringify({
          cls: document.querySelector('.hp-pp').className,
          noseClip: getComputedStyle(nose).clipPath,
          whiskers: document.querySelectorAll('.hp-pp__whiskers i').length,
          philtrum: getComputedStyle(document.querySelector('.hp-pp__philtrum')).display,
          lips: [].filter.call(document.querySelectorAll('.hp-pp__lip'),
                 function (el) { return getComputedStyle(el).display !== 'none'; }).length,
          smile: getComputedStyle(document.querySelector('.hp-pp__smile')).display,
          sparkle: !!sp,
          sparkleClip: sp ? getComputedStyle(sp).clipPath : null,
          sparkleColor: sp ? getComputedStyle(sp).backgroundColor : null
        });
      });
    </script>"""

    d = probe(page, NOSE)
    check('the sparkle is on the nose by default — it is the signature',
          d['sparkle'] and 'polygon' in (d['sparkleClip'] or '')
          and '255, 255, 255' in (d['sparkleColor'] or ''),
          f"clip {'set' if d['sparkleClip'] else 'none'}, colour {d['sparkleColor']}")

    check('an oval nose keeps the single smile, with no whiskers or philtrum',
          'hp-pp--nose-oval' in d['cls'] and d['whiskers'] == 0
          and d['noseClip'] == 'none' and d['philtrum'] == 'none'
          and d['lips'] == 0 and d['smile'] != 'none',
          f"{d['whiskers']} whiskers, philtrum {d['philtrum']}, {d['lips']} lips, "
          f"smile {d['smile']}")

    d = probe(build({'settings': {'nose_style': 'diamond'}}, 'diamond'), NOSE)
    check('the bunny nose is cut to a point and brings whiskers',
          'polygon' in d['noseClip'] and d['whiskers'] == 6,
          f"nose clip {'a polygon' if 'polygon' in d['noseClip'] else d['noseClip']}, "
          f"{d['whiskers']} whisker lines")

    check('the bunny gets a philtrum and two lips instead of the single smile',
          d['philtrum'] != 'none' and d['lips'] == 2 and d['smile'] == 'none',
          f"philtrum {d['philtrum']}, {d['lips']} lips, single smile {d['smile']}")

    # The mouth has to be one mark, not three. This is measured rather than
    # eyeballed because the parts can sit a few pixels apart and still look
    # deliberate in a thumbnail — and because the primitive that was here
    # before drew about ninety degrees rather than a half ellipse, putting the
    # lips' ends thirteen pixels below where the geometry said they were.
    JOIN = """<script>
      window.addEventListener('load', function () {
        function r(sel) {
          var b = document.querySelector(sel).getBoundingClientRect();
          return { t: b.top, b: b.bottom, l: b.left, r: b.right };
        }
        var p = r('.hp-pp__philtrum'), L = r('.hp-pp__lip--l'), R = r('.hp-pp__lip--r');
        document.title = 'RESULT' + JSON.stringify({
          dy: Math.round(Math.abs(L.t - p.b)),
          dyR: Math.round(Math.abs(R.t - p.b)),
          dxL: Math.round(Math.abs(L.r - (p.l + p.r) / 2)),
          dxR: Math.round(Math.abs(R.l - (p.l + p.r) / 2)),
          // Wider than deep, or it reads as a bowl rather than a smile.
          ratio: Math.round(((L.r - L.l) / (L.b - L.t)) * 10) / 10
        });
      });
    </script>"""
    d = probe(build({'settings': {'nose_style': 'diamond'}}, 'join'), JOIN)
    check('the lips meet the philtrum exactly, so the mouth is one mark',
          d['dy'] <= 1 and d['dyR'] <= 1 and d['dxL'] <= 1 and d['dxR'] <= 1,
          f"vertical gap {d['dy']}px and {d['dyR']}px, "
          f"horizontal {d['dxL']}px and {d['dxR']}px")

    check('each lip is a wide sweep rather than a deep bowl',
          d['ratio'] >= 2.5, f"{d['ratio']}x wider than deep")

    d = probe(build({'settings': {'show_sparkle': False}}, 'nosparkle'), NOSE)
    check('the sparkle can be switched off', not d['sparkle'],
          f"sparkle present: {d['sparkle']}")

    # --- the shadow ------------------------------------------------------
    # Comparing the shadow against the colour behind it would mean knowing what
    # is behind it, which depends on where the pin has got to. Comparing the
    # same pixel with the shadow on and off does not: the difference between
    # the two frames is the shadow and nothing else.
    def frame(strength, name, scroll):
        ov = {'settings': {'shadow_strength': strength}}
        return shot(build(ov, name), scroll, name)

    SCROLL = 700
    off = frame(0, 'shadow-off', SCROLL)
    mid = frame(28, 'shadow-mid', SCROLL)
    top = frame(60, 'shadow-max', SCROLL)

    def dome_top(img, x):
        for y in range(img.size[1]):
            if near(img.getpixel((x, y)), PAL, 8):
                return y
        return None

    def drop(a, b, x, y):
        """How much darker b is than a at one pixel."""
        return sum(a.getpixel((x, y))) - sum(b.getpixel((x, y)))

    col = 200                      # clear of the ears, which shadow separately
    y_off, y_mid = dome_top(off, col), dome_top(mid, col)
    check('the shadow changes nothing about where the dome is',
          y_off is not None and y_off == y_mid,
          f"dome top at y={y_off} without it, y={y_mid} with it")

    just_above = max(y_off - 4, 0)
    check('there is a shadow above the dome by default',
          drop(off, mid, col, just_above) > 20,
          f"{drop(off, mid, col, just_above)} darker 4px above the dome")
    check('turning it up makes it deeper, not wider',
          drop(off, top, col, just_above) > drop(off, mid, col, just_above),
          f"60% is {drop(off, top, col, just_above)} deep against 28%'s "
          f"{drop(off, mid, col, just_above)}")
    check('it fades out rather than ending on a line',
          all(drop(off, mid, col, max(y_off - d, 0)) >= drop(off, mid, col, max(y_off - d - 8, 0))
              for d in range(4, 40, 8)),
          'each step up from the dome is lighter than the last: '
          + ', '.join(str(drop(off, mid, col, max(y_off - d, 0))) for d in range(4, 44, 8)))
    check('and is gone well before the top of the section above',
          drop(off, mid, col, max(y_off - 60, 0)) <= 4,
          f"{drop(off, mid, col, max(y_off - 60, 0))} darker 60px up")

    # An outer box-shadow is clipped to outside the border box, so the flat
    # bottom edge should be clean. Scrolling down to it is no good — Chromium
    # does not repaint after a programmatic scroll under a virtual time budget
    # and the frame comes back blank — so the section above is dropped to
    # nothing instead and the whole panel starts in view.
    foot_off = shot(build({'settings': {'shadow_strength': 0}}, 'foot-off', above_h=0),
                    0, 'foot-off')
    foot_max = shot(build({'settings': {'shadow_strength': 60}}, 'foot-max', above_h=0),
                    0, 'foot-max')
    edge = None
    for y in range(foot_max.size[1] - 1, 0, -1):
        if near(foot_max.getpixel((col, y)), PAL, 8):
            edge = y
            break
    rows = list(range(edge + 2, min(edge + 30, foot_max.size[1]))) if edge else []
    worst = max((drop(foot_off, foot_max, col, y) for y in rows), default=None)
    check('nothing leaks onto the section below, even at full strength',
          edge is not None and rows and worst is not None and worst <= 3,
          f"panel ends at y={edge}; worst of the {len(rows)} rows under it is {worst}")

    EAR = """<script>
      var e = document.querySelector('.hp-pp__ear');
      document.title = 'RESULT' + JSON.stringify({
        ear: getComputedStyle(e).boxShadow,
        panel: getComputedStyle(document.querySelector('.hp-pp')).boxShadow
      });
    </script>"""
    d = probe(build({}, 'shadow-ear'), EAR)
    check('the ears cast one too, so they do not stay flat on a lifted dome',
          d['ear'] != 'none', f"ear box-shadow: {d['ear']}")
    check('both are the ink colour rather than black',
          d['panel'].startswith('rgba(47, 51, 38') and d['ear'].startswith('rgba(47, 51, 38'),
          f"panel {d['panel'].split(')')[0]})")

    print(f"\n{sum(res)} passed, {len(res) - sum(res)} failed")
