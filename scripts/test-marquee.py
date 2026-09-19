"""Check the marquee's loop arithmetic, which is the only part that can be
subtly wrong: a shift that is not exactly one run's width shows as a jump once
per loop, and content narrower than the screen slides a gap across itself.
"""
import json, subprocess, sys, pathlib, re
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/marquee.liquid'
HERE = pathlib.Path(__file__).resolve().parent

PROBE = """<script>
setTimeout(function () {
  var el = document.querySelector('hp-marquee');
  var track = el.querySelector('.hp-mq__track');
  var runs = track.children.length;
  var run = track.children[0].getBoundingClientRect().width;
  var trackW = track.getBoundingClientRect().width;
  var cs = getComputedStyle(el);
  var endPct = parseFloat(cs.getPropertyValue('--hp-mq-end'));
  document.title = 'RESULT' + JSON.stringify({
    runs: runs,
    run: Math.round(run * 100) / 100,
    trackW: Math.round(trackW * 100) / 100,
    // What the animation actually travels, in px.
    shift: Math.round(Math.abs(endPct) / 100 * trackW * 100) / 100,
    dur: cs.getPropertyValue('--hp-mq-dur').trim(),
    band: Math.round(el.getBoundingClientRect().width),
    stroke: getComputedStyle(document.querySelector('.hp-mq__text--outline') ||
                            document.querySelector('.hp-mq__text')).webkitTextStrokeWidth,
    firstColor: getComputedStyle(document.querySelector('.hp-mq__text')).color,
    overflowX: cs.overflowX,
    // The space actually rendered between consecutive items. The arithmetic
    // checks below all hold at zero spacing, so this is the one that catches
    // an item rule cancelling it.
    spacings: (function () {
      var kids = track.children[0].children, out = [];
      for (var i = 1; i < kids.length; i++) {
        out.push(Math.round((kids[i].getBoundingClientRect().left -
                             kids[i - 1].getBoundingClientRect().right) * 10) / 10);
      }
      return out;
    })(),
    // Space carried after the last item, so runs do not butt together.
    tailSpace: (function () {
      var g = track.children[0], kids = g.children;
      if (!kids.length) return null;
      return Math.round((g.getBoundingClientRect().right -
                         kids[kids.length - 1].getBoundingClientRect().right) * 10) / 10;
    })(),
    // The animation is on the track, not on the custom element around it.
    anim: getComputedStyle(track).animationName + ' ' +
          getComputedStyle(track).animationDirection,
    trackTransform: getComputedStyle(track).transform === 'none' ? 'none' : 'set'
  });
}, 1200);
</script>"""

def run(overrides, name, width=1200, flags=()):
    page = HERE / f'mq-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>'),
                    encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},400', '--virtual-time-budget=4000', *flags,
        '--dump-dom', 'file://' + str(page)], capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))

res = []
def check(label, ok, detail):
    res.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")

# Long content, so no cloning is needed.
LONG = {'blocks': [{'type': 'text', 'settings': {'text': 'Soft on little noses and always within reach'}},
                   {'type': 'text', 'settings': {'text': 'Made in small batches', 'style': 'outline'}},
                   {'type': 'text', 'settings': {'text': 'Washable and reusable forever'}}]}

d = run(LONG, 'long')
check('the track is an exact multiple of one run',
      abs(d['trackW'] - d['run'] * d['runs']) < 0.5,
      f"{d['runs']} runs x {d['run']}px = {round(d['run']*d['runs'],2)} vs track {d['trackW']}")
check('the animation travels exactly one run (no jump per loop)',
      abs(d['shift'] - d['run']) < 0.5,
      f"shift {d['shift']}px vs run {d['run']}px")
check('duration comes from the measured run at the speed set',
      abs(float(d['dur'].rstrip('s')) - d['run'] / 60.0) < 0.05,
      f"{d['dur']} for {d['run']}px at 60px/s = {round(d['run']/60.0, 2)}s")

# One short phrase: the run is far narrower than the band, so it must be cloned.
SHORT = {'blocks': [{'type': 'text', 'settings': {'text': 'Hi'}}]}
d = run(SHORT, 'short')
check('short content is repeated until it covers the band twice',
      d['trackW'] >= d['band'] * 2 - 1 and d['runs'] > 2,
      f"run {d['run']}px, {d['runs']} runs, track {d['trackW']}px vs band {d['band']}px")
check('cloned runs keep the loop exact',
      abs(d['shift'] - d['run']) < 0.5,
      f"shift {d['shift']}px vs run {d['run']}px")

# Same content on a narrow screen needs fewer clones, and still loops exactly.
d = run(SHORT, 'shortnarrow', width=400)
check('narrow screen: still covers twice over and loops exactly',
      d['trackW'] >= d['band'] * 2 - 1 and abs(d['shift'] - d['run']) < 0.5,
      f"{d['runs']} runs, track {d['trackW']}px vs band {d['band']}px, shift {d['shift']}px")

# Direction and outline.
d = run(dict(LONG, settings={'direction': 'right'}), 'right')
check('right-to-left setting reverses the animation',
      'reverse' in d['anim'], d['anim'])

d = run(LONG, 'outline')
check('outlined text is stroked, not just coloured',
      d['stroke'] not in ('', '0px'), f"-webkit-text-stroke-width {d['stroke']}")

# Reduced motion: stopped, and reachable by hand.
d = run(LONG, 'reduced', flags=['--force-prefers-reduced-motion'])
check('reduced motion: animation off, no transform, scrollable by hand',
      d['anim'].startswith('none') and d['trackTransform'] == 'none'
      and d['overflowX'] in ('auto', 'scroll'),
      f"animation {d['anim']}, transform {d['trackTransform']}, overflow-x {d['overflowX']}")

d = run(LONG, 'normalmotion')
check('normal motion: the animation is actually running',
      d['anim'].startswith('hp-mq-run') and 'normal' in d['anim'], d['anim'])

# --- Spacing actually rendered -------------------------------------------
# The bug this catches: .hp-mq__text set `margin: 0` at the same specificity as
# the rule that spaced the items, two lines later, so every text ran into the
# next one while images kept their spacing.
TEXT_ONLY = {'settings': {'gap': 48}, 'blocks': [
    {'type': 'text', 'settings': {'text': 'Soft on little noses'}},
    {'type': 'text', 'settings': {'text': 'Always within reach'}},
    {'type': 'text', 'settings': {'text': 'Made in small batches'}}]}
d = run(TEXT_ONLY, 'spacetext')
check('text to text is spaced by the setting',
      d['spacings'] and all(abs(x - 48) < 1 for x in d['spacings']),
      f"gaps between items: {d['spacings']} (wanted 48 each)")
check('a run carries trailing space, so runs do not butt together',
      d['tailSpace'] is not None and abs(d['tailSpace'] - 48) < 1,
      f"trailing space {d['tailSpace']} (wanted 48)")

MIXED = {'settings': {'gap': 48}, 'blocks': [
    {'type': 'text', 'settings': {'text': 'Soft on little noses'}},
    {'type': 'image', 'settings': {'image': 'mark-ink.png'}},
    {'type': 'text', 'settings': {'text': 'Always within reach'}},
    {'type': 'image', 'settings': {'image': 'mark-ink.png'}}]}
d = run(MIXED, 'spacemix')
check('text and image are spaced the same either way round',
      d['spacings'] and all(abs(x - 48) < 1 for x in d['spacings']),
      f"gaps: {d['spacings']} (text-image, image-text, text-image)")

d = run({'settings': {'gap': 120}, 'blocks': TEXT_ONLY['blocks']}, 'space120')
check('changing the setting changes the rendered spacing',
      d['spacings'] and all(abs(x - 120) < 1 for x in d['spacings']),
      f"gaps at the 120px setting: {d['spacings']}")

# And the loop must still be exact now that spacing is padding, not margin.
d = run(MIXED, 'mixexact')
check('the loop is still exactly one run with the new spacing',
      abs(d['shift'] - d['run']) < 0.5 and abs(d['trackW'] - d['run'] * d['runs']) < 0.5,
      f"shift {d['shift']}px, run {d['run']}px, track {d['trackW']} vs {round(d['run']*d['runs'],2)}")

print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
