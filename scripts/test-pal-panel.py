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



    # --- The outline -------------------------------------------------------
    # The hankie narrows at the top and flares out to a point at each side.
    # A border radius can only bow outwards, so what is checked here is the
    # thing a radius could not have produced: a head narrower than the body,
    # and a shoulder where it reaches full width.
    # A shallow head and almost nothing above it, so the whole outline down to
    # the shoulder fits on one screen and can be read in a single frame.
    img = shot(build({'settings': {'show_face': False, 'dome_height': 35}},
                     'shape', above_h=20), 0, 'shape', w=1200, h=1000)
    vpw = 1185

    def row_extent(y):
        """Leftmost and rightmost Pal pixel on this row."""
        xs = [x for x in range(0, vpw, 3) if near(img.getpixel((x, y)), PAL)]
        return (min(xs), max(xs)) if xs else None

    def first_row():
        for y in range(0, 900):
            if row_extent(y):
                return y
        return None

    top = first_row()
    check('the outline starts somewhere down the page, not at full width',
          top is not None, f'first Pal pixel at y={top}')

    widths = {}
    # The last one is deliberately past the shoulder, which sits about
    # 0.35 of the viewport height down at this setting.
    for dy in (4, 40, 90, 160, 250, 400):
        ext = row_extent(top + dy)
        widths[dy] = (ext[1] - ext[0]) if ext else None

    head = widths[4]
    body = widths[400]
    check('the head is narrower than the body',
          head is not None and body is not None and head < body * 0.75,
          '  '.join(f'{dy}px down: {w}px wide' for dy, w in widths.items()))

    check('it widens all the way down to the shoulder, never narrowing',
          all(widths[a] <= widths[b] + 2
              for a, b in zip([4, 40, 90, 160, 250], [40, 90, 160, 250, 400])),
          'widths in order: ' + ', '.join(str(widths[d]) for d in (4, 40, 90, 160, 250, 400)))

    check('it reaches the full width of the screen by the shoulder',
          body is not None and body >= vpw - 12,
          f'{body}px of a {vpw}px viewport')

    ext = row_extent(top + 90)
    check('the outline is symmetric about the centre',
          ext is not None and abs((ext[0] + ext[1]) / 2 - vpw / 2) <= 6,
          f'left {ext[0]}, right {ext[1]}, centre {(ext[0]+ext[1])//2} vs {vpw//2}')

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
        check(f'at {vh}vh the shoulder measures {want}px, which is what the pin reads',
              abs(d['gauge'] - want) <= 2, f"gauge {d['gauge']}px")
        check(f'the face sits 22% down the head at {vh}vh',
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

    print(f"\n{sum(res)} passed, {len(res) - sum(res)} failed")
