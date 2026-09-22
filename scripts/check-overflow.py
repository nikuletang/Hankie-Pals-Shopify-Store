"""Does any section make the page scroll sideways on a phone?

Horizontal overflow is a property of the whole document, not of the section
that causes it. A reader who drags the page sideways and finds a strip of
empty background beside the header has no way of knowing that the culprit is
a section far below -- and neither does anyone reading a bug report about it.
So this checks every section on its own, at a real phone width, and names the
elements that reach past the edge.

Three of these have shipped already:

  - the header, whose icon pills grew when the shared stylesheet loaded last
    and pushed the hamburger off the right edge;
  - the feature collage, whose pills were anchored by their middles and hung
    off the screen near an edge;
  - the solution tabs, which slide in FROM the right and stand outside the
    section for the length of the animation.

Headless Chromium will not open a window under 500px and 500px is wide enough
to hide all three, so each page is measured inside an iframe of the true width.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')
WIDTHS = (390, 360)

# A section that needs a setting before it renders anything worth measuring.
OVERRIDES = {
    'hp-header': {'settings': {'menu': 'main-menu'}},
    'hero-split': {'settings': {'mobile_layout': 'stack'}},
}

PROBE = '''<script>
setTimeout(function () {
  var vw = document.documentElement.clientWidth, bad = [];
  var all = document.querySelectorAll('*');
  for (var i = 0; i < all.length; i++) {
    var e = all[i], r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.right > vw + 0.5) {
      bad.push({ tag: e.tagName.toLowerCase(),
                 cls: (e.className || '').toString().slice(0, 48),
                 l: Math.round(r.left), r: Math.round(r.right),
                 pos: getComputedStyle(e).position });
    }
  }
  document.title = 'RESULT' + JSON.stringify({
    vw: vw, docW: document.documentElement.scrollWidth, over: bad.slice(0, 6) });
}, 700);
</script>'''


def scan(section, width):
    page = TMP / f'ov-{section}-{width}.html'
    r = subprocess.run([sys.executable, str(HERE / 'render-section.py'),
                        str(ROOT / 'sections' / f'{section}.liquid'),
                        json.dumps(OVERRIDES.get(section, {})), str(page)],
                       capture_output=True)
    if r.returncode != 0:
        return None, r.stderr.decode()[-200:]
    page.write_text(page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>'),
                    encoding='utf-8')
    wrap = TMP / f'ov-{section}-{width}-wrap.html'
    wrap.write_text(
        '<!doctype html><meta charset="utf-8"><style>html,body{margin:0}'
        f'iframe{{width:{width}px;height:1600px;border:0;display:block}}</style>'
        f'<iframe src="{page.name}"></iframe><script>setTimeout(function(){{'
        'document.title=document.querySelector("iframe").contentDocument.title;'
        '}, 1400);</script>', encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', f'--window-size={width + 310},1700',
        '--virtual-time-budget=9000', '--dump-dom', 'file://' + str(wrap)],
        capture_output=True, text=True, timeout=240).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        return None, 'no measurement came back'
    return json.loads(m.group(1)), None


def main():
    sections = sorted(p.stem for p in (ROOT / 'sections').glob('*.liquid'))
    problems = 0
    for s in sections:
        for w in WIDTHS:
            d, err = scan(s, w)
            if d is None:
                print(f"FAIL  {s} at {w}px: {err}")
                problems += 1
                continue
            over = d['docW'] - d['vw']
            if over > 0:
                problems += 1
                print(f"FAIL  {s} makes the page {over}px wider than a {w}px phone")
                for b in d['over']:
                    print(f"        {b['tag']} .{b['cls']} ({b['pos']}) "
                          f"runs {b['l']} to {b['r']}")
    print(f"\n{len(sections)} section(s) at {', '.join(str(w) for w in WIDTHS)}px, "
          f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
