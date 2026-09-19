"""Check the Pal reveal: the scroll arithmetic, and whether the body actually
covers the screen at the end.

Coverage is the one that fails silently — a Pal that stops just short leaves
slivers of the old background in the corners, which looks like a rendering bug
rather than a missing setting. So it is read off the pixels, not asserted.
"""
import json, subprocess, sys, pathlib, re
from PIL import Image

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/pal-reveal.liquid'
HERE = pathlib.Path(__file__).resolve().parent
PAL = (207, 225, 185)      # #CFE1B9, the Pal's default body
STAGE = (252, 251, 246)    # #FCFBF6, the background behind the first half


def page(overrides, name):
    p = HERE / f'pr-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps(overrides), str(p)], check=True, capture_output=True)
    return p


def shot(src, progress, name, w=1200, h=800, flags=()):
    """Freeze the reveal at a given progress and photograph it."""
    pose = """<script>
      window.addEventListener('load', function () {
        var root = document.querySelector('.hp-rv');
        root.style.setProperty('--p', '%s');
      });
    </script>""" % progress
    out = HERE / f'pr-{name}.html'
    out.write_text(pathlib.Path(src).read_text(encoding='utf-8')
                   .replace('</body>', pose + '</body>'), encoding='utf-8')
    png = HERE / f'pr-{name}.png'
    subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                    f'--window-size={w},{h}', '--virtual-time-budget=3000', *flags,
                    f'--screenshot={png}', 'file://' + str(out)], capture_output=True)
    return Image.open(png).convert('RGB')


def near(px, ref, tol=12):
    return all(abs(a - b) <= tol for a, b in zip(px, ref))


_viewport = {}


def viewport(src, w, h, flags=()):
    """The area the page actually renders into.

    A --window-size screenshot is the whole window: headless keeps some of it
    for chrome and the scrollbar takes more, so the image's corners are not the
    viewport's corners. Sampling those instead of these is what made a working
    reveal look like it covered nothing.
    """
    key = (w, h, tuple(flags))
    if key in _viewport:
        return _viewport[key]
    script = ("<script>window.addEventListener('load', function(){"
              "document.title='RESULT'+JSON.stringify("
              "{w: document.documentElement.clientWidth,"
              " h: document.documentElement.clientHeight});});</script>")
    out = pathlib.Path(str(src).replace('.html', f'.vp{w}x{h}.html'))
    out.write_text(pathlib.Path(src).read_text(encoding='utf-8')
                   .replace('</body>', script + '</body>'), encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                          f'--window-size={w},{h}', '--virtual-time-budget=3000', *flags,
                          '--dump-dom', 'file://' + str(out)],
                         capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('could not read the viewport size')
    _viewport[key] = json.loads(m.group(1))
    return _viewport[key]


def corners(img, vp):
    """The four corners of the rendered viewport, just inside its edges."""
    x1, y1 = 3, 3
    x2, y2 = vp['w'] - 4, vp['h'] - 4
    return {'TL': img.getpixel((x1, y1)), 'TR': img.getpixel((x2, y1)),
            'BL': img.getpixel((x1, y2)), 'BR': img.getpixel((x2, y2))}


def shot_framed(src, progress, name, fw, fh):
    """Photograph the section inside a frame of an exact size.

    The frame sits at the top left with nothing around it, so its own box is
    the rectangle (0, 0, fw, fh) of the resulting image.
    """
    pose = """<script>
      window.addEventListener('load', function () {
        document.querySelector('.hp-rv').style.setProperty('--p', '%s');
      });
    </script>""" % progress
    inner = HERE / f'pr-{name}-inner.html'
    inner.write_text(pathlib.Path(src).read_text(encoding='utf-8')
                     .replace('</body>', pose + '</body>'), encoding='utf-8')
    wrap = HERE / f'pr-{name}-wrap.html'
    wrap.write_text(
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        'html,body{margin:0;padding:0;background:#ff00ff}'
        f'iframe{{width:{fw}px;height:{fh}px;border:0;display:block}}'
        '</style></head><body>'
        f'<iframe src="{inner.name}" scrolling="no"></iframe></body></html>',
        encoding='utf-8')
    png = HERE / f'pr-{name}.png'
    subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                    '--allow-file-access-from-files', f'--window-size={fw + 220},{fh + 200}',
                    '--virtual-time-budget=3000', f'--screenshot={png}',
                    'file://' + str(wrap)], capture_output=True)
    return Image.open(png).convert('RGB')


def probe(src, script, flags=()):
    out = pathlib.Path(str(src).replace('.html', '.probe.html'))
    out.write_text(pathlib.Path(src).read_text(encoding='utf-8')
                   .replace('</body>', script + '</body>'), encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                          '--window-size=1200,800', '--virtual-time-budget=4000', *flags,
                          '--dump-dom', 'file://' + str(out)],
                         capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement back')
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


if __name__ == '__main__':
    src = page({}, 'base')

    # --- Coverage, at several window shapes -------------------------------
    # Headless refuses a window under 500px wide, so a real phone width is
    # tested through an iframe of that size: inside it, innerWidth is 390 and
    # the section measures exactly what it would on the phone.
    img = shot_framed(src, 1, 'cover-phone', 390, 780)
    c = {'TL': img.getpixel((3, 3)), 'TR': img.getpixel((386, 3)),
         'BL': img.getpixel((3, 776)), 'BR': img.getpixel((386, 776))}
    bad = {k: v for k, v in c.items() if not near(v, PAL)}
    check('covered at the end — phone 390x780 (in a frame of that size)',
          not bad, f"corners {c}" if bad else "all four corners are the Pal colour")

    for w, h, tag in [(1200, 800, 'wide'), (1600, 700, 'letterbox'),
                      (900, 1100, 'tall')]:
        img = shot(src, 1, f'cover-{tag}', w=w, h=h)
        vp = viewport(src, w, h)
        c = corners(img, vp)
        bad = {k: v for k, v in c.items() if not near(v, PAL)}
        check(f'covered at the end — {tag} {w}x{h}', not bad,
              f"viewport {vp['w']}x{vp['h']}, corners {c}" if bad
              else f"viewport {vp['w']}x{vp['h']}, all four corners are the Pal colour")

    # --- At the start it is the background, not the Pal --------------------
    img = shot(src, 0, 'start')
    c = corners(img, viewport(src, 1200, 800))
    check('at the start every corner is the background, not the Pal',
          all(near(v, STAGE) for v in c.values()),
          f"corners {c} vs stage {STAGE}")

    # --- The two halves trade places ---------------------------------------
    READ = """<script>
      window.addEventListener('load', function () {
        var root = document.querySelector('.hp-rv');
        function at(p) {
          root.style.setProperty('--p', p);
          void document.body.offsetHeight;
          var b = getComputedStyle(document.querySelector('.hp-rv__before'));
          var a = getComputedStyle(document.querySelector('.hp-rv__after'));
          return { before: Math.round(parseFloat(b.opacity) * 100) / 100,
                   after: Math.round(parseFloat(a.opacity) * 100) / 100 };
        }
        var out = { live: root.classList.contains('hp-rv--live'),
                    smax: parseFloat(getComputedStyle(root).getPropertyValue('--hp-rv-smax')),
                    p0: at(0), p50: at(0.5), p100: at(1) };
        document.title = 'RESULT' + JSON.stringify(out);
      });
    </script>"""
    d = probe(src, READ)
    check('the script switches the section to its pinned form', d['live'], f"hp-rv--live: {d['live']}")
    check('at the start: first half visible, second not',
          d['p0']['before'] == 1 and d['p0']['after'] == 0, str(d['p0']))
    check('at the end: first half gone, second fully in',
          d['p100']['before'] == 0 and d['p100']['after'] == 1, str(d['p100']))
    check('halfway: the first half has already cleared out',
          d['p50']['before'] == 0, f"halfway {d['p50']}")
    check('the scale needed is measured, not guessed',
          d['smax'] and d['smax'] > 1, f"--hp-rv-smax = {round(d['smax'], 2)}")

    # --- Scroll arithmetic --------------------------------------------------
    # getBoundingClientRect is synchronous after a programmatic scroll, so this
    # needs no animation frames, unlike anything observer-driven.
    SCROLL = """<script>
      window.addEventListener('load', function () {
        var el = document.querySelector('hp-pal-reveal');
        var root = document.querySelector('.hp-rv');
        var travel = root.getBoundingClientRect().height - el.getBoundingClientRect().height;
        function at(y) { window.scrollTo(0, y); return Math.round(el.progress() * 1000) / 1000; }
        document.title = 'RESULT' + JSON.stringify({
          travel: Math.round(travel),
          top: at(0), quarter: at(travel * 0.25), half: at(travel * 0.5),
          end: at(travel), past: at(travel + 800)
        });
      });
    </script>"""
    d = probe(src, SCROLL)
    check('progress runs 0 to 1 across the track and clamps past it',
          d['top'] == 0 and abs(d['quarter'] - 0.25) < 0.02
          and abs(d['half'] - 0.5) < 0.02 and d['end'] == 1 and d['past'] == 1,
          f"travel {d['travel']}px -> 0:{d['top']} 25%:{d['quarter']} "
          f"50%:{d['half']} 100%:{d['end']} past:{d['past']}")

    # --- Reduced motion: stays as two readable halves -----------------------
    RM = """<script>
      window.addEventListener('load', function () {
        var root = document.querySelector('.hp-rv');
        document.title = 'RESULT' + JSON.stringify({
          live: root.classList.contains('hp-rv--live'),
          stagePos: getComputedStyle(document.querySelector('.hp-rv__stage')).position,
          before: getComputedStyle(document.querySelector('.hp-rv__before')).opacity,
          after: getComputedStyle(document.querySelector('.hp-rv__after')).opacity
        });
      });
    </script>"""
    d = probe(src, RM, flags=['--force-prefers-reduced-motion'])
    check('reduced motion: nothing pinned, both halves readable',
          not d['live'] and d['stagePos'] == 'relative'
          and float(d['before']) == 1 and float(d['after']) == 1,
          f"live {d['live']}, stage {d['stagePos']}, before {d['before']}, after {d['after']}")

    print(f"\n{sum(res)} passed, {len(res) - sum(res)} failed")
