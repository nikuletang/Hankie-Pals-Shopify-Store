"""Check the story timeline.

The claim worth settling is that the dotted line goes through the cards. The
cards are placed from the step's index and the path is generated from the same
numbers, so the two agree by construction -- which is exactly the kind of
agreement that stops being true the moment either side is edited. So the check
reads the card centres off the rendered page, converts them into the path's
own coordinates, and compares them with the points the path actually passes
through.

The staircase is absolute, so the other half is that it still holds together
at two steps and at six, where none of the brief's four fixed positions apply.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path(__file__).resolve().parent.parent
SECTION = ROOT / 'sections' / 'story-timeline.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

# A transition sits at an arbitrary frame under a virtual time budget, so the
# reveal is stood down before anything is measured. Its own checks render
# without this.
STILL = """<style>
  .hp-st--motion .hp-st__step,
  .hp-st--motion .hp-st__line {
    opacity: 1 !important;
    transform: rotate(var(--r)) !important;
    transition: none !important;
  }
  .hp-st--motion .hp-st__line { transform: none !important; }
</style>"""

PROBE = """
function bx(e){if(!e)return null;var r=e.getBoundingClientRect();
 return {l:r.left,r:r.right,t:r.top,b:r.bottom,w:r.width,h:r.height};}
function snap(d,w){
  var root=d.querySelector('.hp-st');
  var stage=d.querySelector('.hp-st__stage');
  var svg=d.querySelector('.hp-st__line');
  var path=d.querySelector('.hp-st__path');
  return {
    rootBg:root?w.getComputedStyle(root).backgroundColor:null,
    motion:root?root.classList.contains('hp-st--motion'):null,
    stageTag:stage?stage.tagName:null,
    stageBox:bx(stage),
    stageDisplay:stage?w.getComputedStyle(stage).display:null,
    stageLine:stage?w.getComputedStyle(stage,'::before').backgroundImage:null,
    hops:(function(){var k=0;[].forEach.call(d.querySelectorAll('.hp-st__step'),
      function(e,i){if(i===0)return;
        var b=w.getComputedStyle(e,'::before').backgroundImage;
        if(b&&b!=='none')k++;});return k;})(),
    hopArt:[].map.call(d.querySelectorAll('.hp-st__step'),function(e,i){
      return i===0?null:w.getComputedStyle(e,'::before').backgroundImage;})
      .filter(function(x){return x!==null;}),
    svgShown:svg?w.getComputedStyle(svg).display:null,
    svgHidden:svg?svg.getAttribute('aria-hidden'):null,
    viewBox:svg?svg.getAttribute('viewBox'):null,
    d:path?path.getAttribute('d'):null,
    stroke:path?{c:w.getComputedStyle(path).stroke,
                 wdt:w.getComputedStyle(path).strokeWidth,
                 dash:w.getComputedStyle(path).strokeDasharray,
                 cap:w.getComputedStyle(path).strokeLinecap,
                 fill:w.getComputedStyle(path).fill}:null,
    circles:[].map.call(d.querySelectorAll('.hp-st__line circle'),function(c){
      return {cx:c.getAttribute('cx'), cy:c.getAttribute('cy'),
              fill:c.getAttribute('fill')};}),
    steps:[].map.call(d.querySelectorAll('.hp-st__step'),function(e){
      var body=e.querySelector('.hp-st__body');
      var photo=e.querySelector('.hp-st__photo');
      var img=e.querySelector('.hp-st__photo img');
      var label=e.querySelector('.hp-st__label');
      var title=e.querySelector('.hp-st__title');
      var text=e.querySelector('.hp-st__text');
      var back=e.querySelector('.hp-st__back');
      var blob=e.querySelector('.hp-st__blob');
      var cs=w.getComputedStyle(e);
      return {tag:e.tagName, box:bx(e), pos:cs.position, transform:cs.transform,
              inView:e.classList.contains('is-in'),
              opacity:cs.opacity,
              bodyBox:bx(body),
              photo:photo?{box:bx(photo), ow:photo.offsetWidth,
                           radius:w.getComputedStyle(photo).borderTopLeftRadius,
                           overflow:w.getComputedStyle(photo).overflow,
                           bg:w.getComputedStyle(photo).backgroundColor}:null,
              imgFit:img?w.getComputedStyle(img).objectFit:null,
              imgAlt:img?img.getAttribute('alt'):null,
              label:label?{text:label.textContent.trim(),
                           bg:w.getComputedStyle(label).backgroundColor,
                           ink:w.getComputedStyle(label).color,
                           bw:w.getComputedStyle(label).borderTopWidth,
                           bc:w.getComputedStyle(label).borderTopColor}:null,
              title:title?title.textContent.trim():null,
              titleTag:title?title.tagName:null,
              titleInk:title?w.getComputedStyle(title).color:null,
              text:text?text.textContent.trim().slice(0,24):null,
              textBox:bx(text),
              textInk:text?w.getComputedStyle(text).color:null,
              back:back?{bg:w.getComputedStyle(back).backgroundColor,
                         transform:w.getComputedStyle(back).transform,
                         radius:w.getComputedStyle(back).borderTopLeftRadius}:null,
              blobRadius:blob?w.getComputedStyle(blob).borderTopLeftRadius:null,
              blobBorder:blob?w.getComputedStyle(blob).borderTopWidth:null,
              blobBorderColor:blob?w.getComputedStyle(blob).borderTopColor:null,
              blobW:blob?blob.offsetWidth:null,
              blobH:blob?blob.offsetHeight:null};}),
    headInk:(function(){var h=d.querySelector('.hp-st__heading');
      return h?w.getComputedStyle(h).color:null;})(),
    headSize:(function(){var h=d.querySelector('.hp-st__heading');
      return h?w.getComputedStyle(h).fontSize:null;})(),
    subInk:(function(){var p=d.querySelector('.hp-st__sub');
      return p?w.getComputedStyle(p).color:null;})(),
    ebBox:bx(d.querySelector('.hp-st__eyebrow')),
    ebRadius:(function(){var e=d.querySelector('.hp-st__eyebrow');
      return e?w.getComputedStyle(e).borderTopLeftRadius:null;})(),
    docW:d.documentElement.scrollWidth, winW:w.innerWidth};
}
"""

STEPS4 = {'blocks': [
    {'type': 'step', 'settings': {'step_label': f'Step 0{i + 1}', 'title': t,
                                  'body': b, 'image': str(TMP / f'st-photo-{i}.png'),
                                  'image_alt': f'Photo {i + 1}'}}
    for i, (t, b) in enumerate([
        ('The problem', 'A busy toddler, a runny nose and never a tissue in sight.'),
        ('The idea', 'Something soft that stays with her.'),
        ('The prototypes', 'Cut, sewn and re-sewn at the kitchen table.'),
        ('The first Pal', 'Toddler-tested, parent-approved.')])]}


def steps(n):
    return {'blocks': [{'type': 'step', 'settings': {
        'step_label': f'Step {i + 1}', 'title': f'Step {i + 1}',
        'body': 'Some words.'}} for i in range(n)]}


def render(name, overrides, still=True, sabotage=None):
    page = TMP / f'stt-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(page)], check=True,
                   capture_output=True)
    if sabotage:
        # Runs before the section's own script, so it meets the broken browser
        # rather than being broken after the fact.
        page.write_text(page.read_text(encoding='utf-8').replace(
            '<body>', f'<body><script>{sabotage}</script>', 1), encoding='utf-8')
    if still:
        page.write_text(page.read_text(encoding='utf-8').replace(
            '</body>', STILL + '</body>'), encoding='utf-8')
    return page


def run(name, width=1440, overrides=None, still=True, flags=(), drive='',
        sabotage=None):
    page = render(name, overrides, still, sabotage)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>',
        '<script>' + PROBE + "setTimeout(function(){try{" + drive + "}catch(e){};"
        "document.title='RESULT'+JSON.stringify(snap(document,window));},600);"
        "</script></body>"), encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},2400', '--virtual-time-budget=9000', *flags,
        '--dump-dom', 'file://' + str(page)],
        capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


def framed(name, width=390, overrides=None):
    inner = render(name + '-inner', overrides)
    inner.write_text(inner.read_text(encoding='utf-8').replace(
        '</body>', '<script>' + PROBE + '</script></body>'), encoding='utf-8')
    wrap = TMP / f'stt-{name}-wrap.html'
    wrap.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0}'
        f'iframe{{width:{width}px;height:3000px;border:0;display:block}}</style>'
        f'<iframe src="{inner.name}"></iframe><script>setTimeout(function(){{'
        'var f=document.querySelector("iframe");document.title="RESULT"+JSON.stringify('
        'f.contentWindow.snap(f.contentDocument,f.contentWindow));},900);</script>',
        encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', f'--window-size={width + 310},3100',
        '--virtual-time-budget=11000', '--dump-dom', 'file://' + str(wrap)],
        capture_output=True, text=True, timeout=200).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def rgb(v):
    return [int(x) for x in re.findall(r'\d+', v)[:3]]


def contrast(a, b):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    def lum(c):
        return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def outside_blob(step, box):
    """How far out of the card's inscribed ellipse a box's worst corner falls.

    The card is a blob, so its bounding box is not its boundary: words can sit
    inside the box and outside the shape, which is what a corner of a rounded
    blob is. The blob's radii are all near 50%, so an ellipse inscribed in the
    card is a fair stand-in for it, and a stricter test than the box.
    """
    c = step['box']
    cx, cy = (c['l'] + c['r']) / 2, (c['t'] + c['b']) / 2
    rx, ry = c['w'] / 2, c['h'] / 2
    worst = 0
    for x in (box['l'], box['r']):
        for y in (box['t'], box['b']):
            worst = max(worst, ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
    return worst


def segments(d):
    """Every cubic as (start, control 1, control 2, end)."""
    nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', d)]
    out, here = [], (nums[0], nums[1])
    rest = nums[2:]
    for i in range(0, len(rest) - 5, 6):
        c1 = (rest[i], rest[i + 1])
        c2 = (rest[i + 2], rest[i + 3])
        end = (rest[i + 4], rest[i + 5])
        out.append((here, c1, c2, end))
        here = end
    return out


def bow_of(seg):
    """How far the middle of a cubic sits off the straight line between its
    ends, and which side it falls on.

    This is the whole difference between a trail and a ruled line: a curve
    that leaves one card horizontally and arrives at the next the same way is
    a symmetric S, and the middle of a symmetric S lies exactly on the chord
    -- which is the only stretch of it the blobs do not cover.
    """
    p0, c1, c2, p3 = seg
    mx = (p0[0] + 3 * c1[0] + 3 * c2[0] + p3[0]) / 8
    my = (p0[1] + 3 * c1[1] + 3 * c2[1] + p3[1]) / 8
    cx, cy = (p0[0] + p3[0]) / 2, (p0[1] + p3[1]) / 2
    dx, dy = mx - cx, my - cy
    side = (p3[0] - p0[0]) * dy - (p3[1] - p0[1]) * dx
    return (dx ** 2 + dy ** 2) ** 0.5, (1 if side > 0 else -1 if side < 0 else 0)


def on_curve(d):
    """The point each cubic lands on -- the last pair in every C segment."""
    pts = []
    for seg in re.findall(r'C\s+([^C]+)', d):
        nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', seg)]
        if len(nums) >= 6:
            pts.append((nums[4], nums[5]))
    return pts


d = run('default', overrides=STEPS4)

check('the steps are an ordered list, so they read in order',
      d['stageTag'] == 'OL' and all(s['tag'] == 'LI' for s in d['steps']),
      f"<{(d['stageTag'] or '?').lower()}> of "
      f"{set(s['tag'] for s in d['steps'])}")
check('four of them, each a step lower than the last',
      len(d['steps']) == 4
      and all(d['steps'][i]['box']['t'] < d['steps'][i + 1]['box']['t']
              for i in range(3)),
      f"tops {[round(s['box']['t']) for s in d['steps']]}")
check('alternating left and right of the stage',
      d['steps'][0]['box']['l'] < d['steps'][1]['box']['l']
      and d['steps'][2]['box']['l'] < d['steps'][1]['box']['l']
      and d['steps'][2]['box']['l'] < d['steps'][3]['box']['l'],
      f"lefts {[round(s['box']['l']) for s in d['steps']]}")
check('and each tilted off true',
      all(s['transform'] != 'none' for s in d['steps']),
      f"{[s['transform'][:22] for s in d['steps'][:2]]} ...")

# ------------------------------------------- the line goes through the cards --
vb = [float(x) for x in d['viewBox'].split()]
sb = d['stageBox']
pts = on_curve(d['d'])
centres = [((s['box']['l'] + s['box']['r']) / 2, (s['box']['t'] + s['box']['b']) / 2)
           for s in d['steps']]
# Screen px -> the path's own units, which is what makes this a real check
# rather than a restatement of the generator.
conv = [((cx - sb['l']) / sb['w'] * vb[2] + vb[0],
         (cy - sb['t']) / sb['h'] * vb[3] + vb[1]) for cx, cy in centres]
worst = max(max(abs(p[0] - c[0]), abs(p[1] - c[1]))
            for p, c in zip(pts, conv))
check('the dotted line passes through the middle of every card',
      len(pts) == 5 and worst <= 3,
      f"worst miss {worst:.1f} units; path {[(round(x), round(y)) for x, y in pts[:4]]}"
      f" against centres {[(round(x), round(y)) for x, y in conv]}")
check('and carries on past the last one rather than stopping on it',
      pts[-1][1] > conv[-1][1] + 100,
      f"tail ends at y {round(pts[-1][1])}, last card centre {round(conv[-1][1])}")

# The segment between two cards is the only part of the trail that shows, so
# it is the part that has to curve.
middles = [bow_of(s) for s in segments(d['d'])[1:-1]]
check('the trail bows away from the straight line between the cards',
      all(off >= 80 for off, _ in middles),
      f"middles sit {[round(off) for off, _ in middles]} units off the chord; "
      f"a symmetric S would be 0")
check('and each stretch swings the opposite way to the last, so none cross',
      all(middles[i][1] == -middles[i + 1][1] for i in range(len(middles) - 1)),
      f"sides {[side for _, side in middles]}")

straightened = run('no-bow', overrides={'settings': {'trail_bow': 0},
                                        'blocks': STEPS4['blocks']})
check('and it can be run straight again from the editor',
      all(off <= 2 for off, _ in
          [bow_of(s) for s in segments(straightened['d'])[1:-1]]),
      f"at 0 the middles sit "
      f"{[round(off) for off, _ in [bow_of(s) for s in segments(straightened['d'])[1:-1]]]}"
      f" units off the chord")

check('the dots are a zero-length dash with a round cap, not a dashed line',
      d['stroke']['dash'].startswith('0') and d['stroke']['cap'] == 'round'
      and d['stroke']['fill'] == 'none',
      f"dasharray {d['stroke']['dash']}, linecap {d['stroke']['cap']}, "
      f"fill {d['stroke']['fill']}")
check('the line is never read out',
      d['svgHidden'] == 'true', f"aria-hidden {d['svgHidden']}")
check('a sage dot starts it and a terracotta one ends it',
      len(d['circles']) == 2
      and d['circles'][0]['fill'] == '#93b276'
      and d['circles'][1]['fill'] == '#e06e4c',
      f"{[c['fill'] for c in d['circles']]}")
check('and the end dot sits where the line ends',
      abs(float(d['circles'][1]['cx']) - pts[-1][0]) <= 1
      and abs(float(d['circles'][1]['cy']) - pts[-1][1]) <= 1,
      f"dot at {d['circles'][1]['cx']},{d['circles'][1]['cy']}, "
      f"line ends {round(pts[-1][0])},{round(pts[-1][1])}")

# ------------------------------------------------------------- the cards ----
check('each blob is an irregular shape, and no two are the same',
      len(set(s['blobRadius'] for s in d['steps'])) == 4
      and all('%' in s['blobRadius'] for s in d['steps']),
      f"{[s['blobRadius'][:14] for s in d['steps']]}")
check('each has an outline',
      all(s['blobBorder'] == '2px' for s in d['steps']),
      f"{[s['blobBorder'] for s in d['steps']]}")
check('the blob behind is a different shape again, and offset',
      all(s['back']['radius'] != s['blobRadius'] for s in d['steps'])
      and all(s['back']['transform'] != 'none' for s in d['steps']),
      'every back blob differs in shape and is moved off the card')
check('and the four brand colours run in order behind them',
      [rgb(s['back']['bg']) for s in d['steps']]
      == [[194, 214, 168], [240, 196, 168], [204, 224, 180], [246, 220, 207]],
      f"{[s['back']['bg'] for s in d['steps']]}")
check('it leans one way on the odd cards and the other on the even ones',
      d['steps'][0]['back']['transform'] != d['steps'][1]['back']['transform'],
      f"odd {d['steps'][0]['back']['transform']}, even {d['steps'][1]['back']['transform']}")

check('the photo is a circle that crops rather than squashes',
      all(s['photo']['radius'] == '50%' and s['photo']['overflow'] == 'hidden'
          and s['imgFit'] == 'cover' for s in d['steps']),
      f"radius {d['steps'][0]['photo']['radius']}, "
      f"object-fit {d['steps'][0]['imgFit']}")
check('at the size the brief asks for',
      all(s['photo']['ow'] == 170 for s in d['steps']),
      f"{[s['photo']['ow'] for s in d['steps']]}px laid out "
      f"({[round(s['photo']['box']['w']) for s in d['steps']]}px measured, which "
      f"is the rotated card's bounding box, not the circle)")
check('every step keeps its words inside the blob',
      all(outside_blob(s, s['textBox']) <= 1 for s in d['steps']),
      f"worst corners {[round(outside_blob(s, s['textBox']), 2) for s in d['steps']]}")
check('and its photo too',
      all(outside_blob(s, s['photo']['box']) <= 1 for s in d['steps']),
      f"worst corners {[round(outside_blob(s, s['photo']['box']), 2) for s in d['steps']]}")

check('and the alt text you type is the alt text that ships',
      [s['imgAlt'] for s in d['steps']] == ['Photo 1', 'Photo 2', 'Photo 3', 'Photo 4'],
      f"{[s['imgAlt'] for s in d['steps']]}")

no_photo = run('no-photo', overrides=steps(4))
check('before a photo is chosen the circle still holds its place',
      all(s['photo']['ow'] == 170 for s in no_photo['steps'])
      and no_photo['steps'][0]['imgFit'] is None,
      f"empty circle {no_photo['steps'][0]['photo']['ow']}px")

check('the last step picks up the peach label, the others stay sage',
      rgb(d['steps'][3]['label']['bg']) == [240, 196, 168]
      and all(rgb(s['label']['bg']) == [194, 214, 168] for s in d['steps'][:3]),
      f"{[s['label']['bg'] for s in d['steps']]}")
check('each title is a heading under the list item',
      all(s['titleTag'] == 'H3' for s in d['steps']),
      f"{[s['titleTag'] for s in d['steps']]}")

long_body = {'blocks': [{'type': 'step', 'settings': {
    'step_label': 'Step 01', 'title': 'A rather longer title than usual',
    'body': 'A much longer body than the others, long enough that it would run '
            'out of the blob if the content box were not held to its width.'}}]}
wordy = run('wordy', overrides=long_body)
st = wordy['steps'][0]
check('a longer step keeps its words inside the blob, not just inside its box',
      outside_blob(st, st['textBox']) <= 1,
      f"the text's worst corner sits at {outside_blob(st, st['textBox']):.2f} of "
      f"the way out of the shape, where 1 is its edge")

long_all = {'blocks': [{'type': 'step', 'settings': {
    'step_label': f'Step 0{i + 1}', 'title': 'A rather longer title than usual',
    'body': 'A much longer body than the others, long enough that it would run '
            'out of the blob if the card could not grow to hold it.'}}
    for i in range(4)]}
grown = run('grown', overrides=long_all)
g_sb = grown['stageBox']
g_vb = [float(x) for x in grown['viewBox'].split()]
g_pts = on_curve(grown['d'])
inside = []
for pt, s in zip(g_pts, grown['steps']):
    px = (pt[0] - g_vb[0]) / g_vb[2] * g_sb['w'] + g_sb['l']
    py = (pt[1] - g_vb[1]) / g_vb[3] * g_sb['h'] + g_sb['t']
    inside.append(s['box']['l'] <= px <= s['box']['r']
                  and s['box']['t'] <= py <= s['box']['b'])
check('the line still runs through a card that has grown, even off its middle',
      all(inside), f"{sum(inside)} of {len(inside)} points land inside their card")
check('a card that grows for its words does not land on the one below it',
      all(grown['steps'][i]['box']['b'] < grown['steps'][i + 2]['box']['t']
          for i in range(2)),
      f"bottoms {[round(s['box']['b']) for s in grown['steps'][:2]]}, tops two "
      f"below {[round(s['box']['t']) for s in grown['steps'][2:]]}")
check('and the ones that do not grow keep the size the brief asks for',
      abs(d['steps'][0]['box']['h'] - 460) <= 24,
      f"a default card is {round(d['steps'][0]['box']['h'])}px tall, including "
      f"what its tilt adds to the measured box")

# -------------------------------------------------- two steps, and six ------
two = run('two', overrides=steps(2))
check('two steps place themselves and the line still joins them',
      len(two['steps']) == 2 and len(on_curve(two['d'])) == 3
      and two['steps'][0]['box']['t'] < two['steps'][1]['box']['t'],
      f"{len(two['steps'])} cards, {len(on_curve(two['d']))} curve segments")

six = run('six', overrides=steps(6))
six_pts = on_curve(six['d'])
six_sb, six_vb = six['stageBox'], [float(x) for x in six['viewBox'].split()]
six_conv = [(((s['box']['l'] + s['box']['r']) / 2 - six_sb['l']) / six_sb['w'] * six_vb[2],
             ((s['box']['t'] + s['box']['b']) / 2 - six_sb['t']) / six_sb['h'] * six_vb[3]
             + six_vb[1]) for s in six['steps']]
six_worst = max(max(abs(p[0] - c[0]), abs(p[1] - c[1]))
                for p, c in zip(six_pts, six_conv))
check('and six do too, with none landing on top of another',
      len(six['steps']) == 6 and six_worst <= 3
      and all(six['steps'][i]['box']['b'] < six['steps'][i + 2]['box']['t']
              for i in range(4)),
      f"worst miss {six_worst:.1f} units across six cards")
check('the stage grows to hold them',
      six['stageBox']['h'] > d['stageBox']['h'] + 400,
      f"six steps {round(six['stageBox']['h'])}px, four {round(d['stageBox']['h'])}px")

# ----------------------------------------------------------------- it reads --
check('the heading reads against the band',
      contrast(rgb(d['headInk']), rgb(d['rootBg'])) >= 7,
      f"{contrast(rgb(d['headInk']), rgb(d['rootBg']))}:1")
check('the subheading reads against the band',
      contrast(rgb(d['subInk']), rgb(d['rootBg'])) >= 4.5,
      f"{contrast(rgb(d['subInk']), rgb(d['rootBg']))}:1")
check('a title reads against the card it sits on',
      contrast(rgb(d['steps'][0]['titleInk']), [255, 255, 255]) >= 7,
      f"{contrast(rgb(d['steps'][0]['titleInk']), [255, 255, 255])}:1")
check('the body text reads against the card',
      contrast(rgb(d['steps'][0]['textInk']), [255, 255, 255]) >= 4.5,
      f"{contrast(rgb(d['steps'][0]['textInk']), [255, 255, 255])}:1")
check('the step label reads against its pill, sage and peach alike',
      min(contrast(rgb(d['steps'][0]['label']['ink']), rgb(d['steps'][0]['label']['bg'])),
          contrast(rgb(d['steps'][3]['label']['ink']), rgb(d['steps'][3]['label']['bg']))) >= 4.5,
      f"sage {contrast(rgb(d['steps'][0]['label']['ink']), rgb(d['steps'][0]['label']['bg']))}:1, "
      f"peach {contrast(rgb(d['steps'][3]['label']['ink']), rgb(d['steps'][3]['label']['bg']))}:1")
check('the eyebrow is a pill',
      float((d['ebRadius'] or '0').rstrip('px')) >= 12, f"radius {d['ebRadius']}")

# -------------------------------------------------------------- stacked ----
p390 = framed('phone', 390, STEPS4)
check('the staircase becomes one column on a phone',
      p390['stageDisplay'] == 'flex'
      and all(p390['steps'][i]['box']['b'] <= p390['steps'][i + 1]['box']['t'] + 1
              for i in range(3)),
      f"display {p390['stageDisplay']}, tops "
      f"{[round(s['box']['t']) for s in p390['steps']]}")
check('with the curve stood down for a curved hop in each gap',
      p390['svgShown'] == 'none' and p390['hops'] == 3
      and all('svg' in (h or '') for h in p390['hopArt']),
      f"svg {p390['svgShown']}, {p390['hops']} hops between four steps")
check('and the hop is drawn, not ruled',
      all('C' in (h or '') for h in p390['hopArt']),
      'each hop is a cubic, so it curves between the two blobs')
check('the cards still zig-zag, and still lean',
      len(set(round(s['box']['l']) for s in p390['steps'])) > 1
      and all(s['transform'] != 'none' for s in p390['steps']),
      f"lefts {[round(s['box']['l']) for s in p390['steps']]}")
check('the photo shrinks to its mobile size',
      all(s['photo']['ow'] == 140 for s in p390['steps']),
      f"{[s['photo']['ow'] for s in p390['steps']]}px")
check('and a card still holds its words inside the blob there',
      all(outside_blob(s, s['textBox']) <= 1 for s in p390['steps']),
      f"worst corners {[round(outside_blob(s, s['textBox']), 2) for s in p390['steps']]}")
check('and its photo',
      all(outside_blob(s, s['photo']['box']) <= 1 for s in p390['steps']),
      f"worst corners {[round(outside_blob(s, s['photo']['box']), 2) for s in p390['steps']]}")

for label, snap in (('at 1440px', d), ('at 390px', p390)):
    check(f'the page never scrolls sideways {label}',
          snap['docW'] <= snap['winW'] + 1,
          f"document {snap['docW']}px in {snap['winW']}px")

p360 = framed('phone-360', 360, STEPS4)
check('nor at 360px',
      p360['docW'] <= p360['winW'] + 1,
      f"document {p360['docW']}px in {p360['winW']}px")

narrow = run('narrow', width=1000, overrides=STEPS4)
check('and the staircase still holds at the width it first appears',
      narrow['docW'] <= narrow['winW'] + 1
      and all(narrow['steps'][i]['box']['t'] < narrow['steps'][i + 1]['box']['t']
              for i in range(3)),
      f"document {narrow['docW']}px in {narrow['winW']}px, tops "
      f"{[round(s['box']['t']) for s in narrow['steps']]}")

# --------------------------------------------------------------- motion ----
live = run('motion', overrides=STEPS4, still=False)
check('the steps arrive as they come into view',
      live['motion'] and all(s['inView'] for s in live['steps']),
      f"is-in on {sum(s['inView'] for s in live['steps'])} of {len(live['steps'])}")

calm = run('reduced', overrides=STEPS4, still=False,
           flags=('--force-prefers-reduced-motion',))
check('someone asking for less motion gets them already in place',
      calm['motion'] is False
      and all(float(s['opacity']) > 0.99 for s in calm['steps']),
      f"motion class {calm['motion']}, "
      f"opacity {[s['opacity'] for s in calm['steps']]}")

blind = run('no-io', overrides=STEPS4, still=False,
            sabotage='delete window.IntersectionObserver;')
check('and a browser with no IntersectionObserver is not left with blanks',
      blind['motion'] is False
      and all(float(s['opacity']) > 0.99 for s in blind['steps']),
      f"motion class {blind['motion']}, "
      f"opacity {[s['opacity'] for s in blind['steps']]}")

broken = run('throws', overrides=STEPS4, still=False,
             sabotage='Object.defineProperty(window,"IntersectionObserver",'
                      '{get:function(){throw new Error("boom");}});')
check('and so is one where setting the observer up throws',
      broken['motion'] is False
      and all(float(s['opacity']) > 0.99 for s in broken['steps']),
      f"motion class {broken['motion']}, "
      f"opacity {[s['opacity'] for s in broken['steps']]}")

off = run('no-motion', overrides={'settings': {'animate': False},
                                  'blocks': STEPS4['blocks']}, still=False)
check('the whole reveal can be turned off',
      off['motion'] is False
      and all(float(s['opacity']) > 0.99 for s in off['steps']),
      f"motion class {off['motion']}")

# --- outlines are their own settings, not the heading colour -----------------
# "Outline and headings" was one colour, so softening the card edge dragged the
# section heading with it. Three settings now, sharing a default.
base = run('lines-default', overrides=STEPS4)
b0 = base['steps'][0]
check('out of the box the card edge, the label and the heading share one ink',
      b0['blobBorderColor'] == 'rgb(47, 52, 39)'
      and b0['label']['bc'] == 'rgb(47, 52, 39)'
      and base['headInk'] == 'rgb(47, 52, 39)',
      f"card {b0['blobBorderColor']}, label {b0['label']['bc']}, "
      f"heading {base['headInk']}")

only_card = run('card-line', overrides={
    'settings': {'card_border_color': '#d88b6d'}, 'blocks': STEPS4['blocks']})
c0 = only_card['steps'][0]
check('the card outline can be changed without touching the heading',
      c0['blobBorderColor'] == 'rgb(216, 139, 109)'
      and only_card['headInk'] == 'rgb(47, 52, 39)'
      and c0['titleInk'] == 'rgb(47, 52, 39)',
      f"card {c0['blobBorderColor']}, heading {only_card['headInk']}, "
      f"title {c0['titleInk']}")

only_ink = run('ink-only', overrides={
    'settings': {'ink_color': '#8a3b2a'}, 'blocks': STEPS4['blocks']})
i0 = only_ink['steps'][0]
check('changing the heading colour no longer repaints the card outline',
      only_ink['headInk'] == 'rgb(138, 59, 42)'
      and i0['blobBorderColor'] == 'rgb(47, 52, 39)'
      and i0['label']['bc'] == 'rgb(47, 52, 39)',
      f"heading {only_ink['headInk']}, card {i0['blobBorderColor']}, "
      f"label {i0['label']['bc']}")

noline = run('no-line', overrides={
    'settings': {'card_border_width': 0}, 'blocks': STEPS4['blocks']})
n0 = noline['steps'][0]
check('the card outline can be removed entirely',
      n0['blobBorder'] == '0px',
      f"border-top-width {n0['blobBorder']}")

# The blob is inset: 0 inside the card, so border-box keeps it the same size
# with or without a border. Worth pinning: a card that shrank by 4px when the
# outline came off would shift every photo and line of copy inside it.
check('removing the outline does not resize the card',
      n0['blobW'] == b0['blobW'] and n0['blobH'] == b0['blobH'],
      f"{n0['blobW']}x{n0['blobH']} with no outline, "
      f"{b0['blobW']}x{b0['blobH']} with one")

check('removing the card outline leaves the step label alone',
      n0['label']['bw'] == b0['label']['bw'] and n0['label']['bw'] != '0px',
      f"label border {n0['label']['bw']}, unchanged from {b0['label']['bw']}")

nolabel = run('no-label-line', overrides={
    'settings': {'label_border_width': 0}, 'blocks': STEPS4['blocks']})
check('the step label outline can be removed on its own',
      nolabel['steps'][0]['label']['bw'] == '0px'
      and nolabel['steps'][0]['blobBorder'] == '2px',
      f"label {nolabel['steps'][0]['label']['bw']}, "
      f"card {nolabel['steps'][0]['blobBorder']}")

thick = run('thick-line', overrides={
    'settings': {'card_border_width': 5}, 'blocks': STEPS4['blocks']})
check('the card outline can be made heavier too',
      thick['steps'][0]['blobBorder'] == '5px',
      f"border-top-width {thick['steps'][0]['blobBorder']}")

# The label is declared at 1.5px and always has been; Chromium floors a
# sub-pixel border to whole CSS px at DPR 1, so 1px is what it has always
# drawn. Checked against the section before this change and it is identical.
check('the defaults are unchanged: 2px on the card, 1.5px declared on the label',
      b0['blobBorder'] == '2px' and b0['label']['bw'] == '1px',
      f"card {b0['blobBorder']}, label {b0['label']['bw']} "
      f"(1.5px declared, floored by the engine as it was before)")


# --- filler drawings ---------------------------------------------------------
# The question these answer is not "is there an svg" but "does it land in space
# that was actually empty". That is settled by rendering the section twice,
# once with the drawings and once without, and asking where the difference
# falls -- which also makes the check independent of how the drawings are
# drawn, so swapping the artwork later cannot quietly break it.
import subprocess as _sp
from PIL import Image, ImageChops

_STEPS = [{'type': 'step', 'settings': {
    'step_label': f'Step {i+1}', 'title': f'Step {i+1} title',
    'body': 'A line of copy that sits in the card and wraps to two lines.'}}
    for i in range(4)]

def _with(extra_section=None, picks=('sketchpad', 'needle', 'droplet', 'clip')):
    blocks = []
    for i, b in enumerate(_STEPS):
        st = dict(b['settings'])
        if picks:
            st['doodle'] = picks[i % len(picks)]
        blocks.append({'type': 'step', 'settings': st})
    o = {'blocks': blocks}
    if extra_section:
        o['settings'] = extra_section
    return o

def _shot(overrides, name, w=1400, h=2400):
    src = render(f'dd-{name}', overrides, still=False)
    png = HERE / f'dd-{name}.png'
    _sp.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
             '--force-prefers-reduced-motion', f'--window-size={w},{h}',
             '--virtual-time-budget=4000', f'--screenshot={png}',
             'file://' + str(src)], capture_output=True)
    return Image.open(png).convert('RGB')

# The drawings sit behind the cards, so a drawing that overlaps one is simply
# hidden by it and leaves no trace in a plain before/after diff -- a check
# written that way can never fail, which two deliberate regressions proved.
# The overlap render lifts the layer in front of the cards first, so anything
# landing on a card shows up and can be counted.
LIFT = '<style>.hp-st__doodles{z-index:5 !important}</style>'

def _lifted(name, overrides, w=1400, h=2400):
    src = render(f'dd-{name}', overrides, still=False)
    src.write_text(src.read_text(encoding='utf-8')
                   .replace('</body>', LIFT + '</body>'), encoding='utf-8')
    png = HERE / f'dd-{name}.png'
    _sp.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
             '--force-prefers-reduced-motion', f'--window-size={w},{h}',
             '--virtual-time-budget=4000', f'--screenshot={png}',
             'file://' + str(src)], capture_output=True)
    return Image.open(png).convert('RGB')

on = _lifted('on', _with())
off = _shot(_with(extra_section={'show_doodles': False}, picks=None), 'off')

diff = ImageChops.difference(on, off)
W, H = on.size
dp, offp = diff.load(), off.load()
changed = on_card = 0
for y in range(H):
    for x in range(W):
        if sum(dp[x, y]) > 18:
            changed += 1
            if all(abs(a - b) <= 2 for a, b in zip(offp[x, y], (255, 255, 255))):
                on_card += 1

check('the drawings actually draw something',
      changed > 2000, f"{changed} pixels added")

check('and not one of them lands on a card',
      on_card == 0,
      f"{on_card} of {changed} drawing pixels fall on a card's fill "
      f"(measured with the layer lifted in front, or overlap would be hidden)")

# A drawing in a middle band is capped to that band. Asking for 460px in a
# gap of about 150 must not produce a 460px drawing sitting under two cards.
big = _lifted('big', _with(extra_section={'doodle_size': 460}))
dbig = ImageChops.difference(big, off)
bp = dbig.load()
spill = 0
for y in range(H):
    for x in range(W):
        if sum(bp[x, y]) > 18 and all(abs(a - b) <= 2 for a, b in zip(offp[x, y], (255, 255, 255))):
            spill += 1
check('asking for a drawing bigger than its gap does not push it under a card',
      spill == 0, f"at the maximum 460px size, {spill} pixels land on a card")

# And the settings reach the markup.
import re as _re
src = render('dd-settings', _with(extra_section={
    'doodle_color': '#aa3366', 'doodle_stroke': 4, 'doodle_opacity': 30}), still=False)
html = src.read_text(encoding='utf-8')
m = _re.search(r'<svg[^>]*class="hp-st__doodles"[^>]*>', html, _re.S)
check('colour and line weight reach the drawing layer',
      m and 'stroke="#aa3366"' in m.group(0) and 'stroke-width="4"' in m.group(0),
      (m.group(0)[:90] + '...') if m else 'no doodle layer rendered')

check('the strength slider reaches the layer',
      '--hp-st-doodle-op: 0.3' in html,
      _re.search(r'--hp-st-doodle-op: [^;]*', html).group(0))

none_html = render('dd-none', _with(picks=None), still=False).read_text(encoding='utf-8')
check('no drawing is picked out of the box, so nothing appears unasked',
      'hp-st__doodles' in none_html and '<g' not in
      _re.search(r'class="hp-st__doodles".*?</svg>', none_html, _re.S).group(0),
      'layer present, no drawings in it')

off_html = render('dd-off', _with(extra_section={'show_doodles': False}), still=False).read_text(encoding='utf-8')
# The class name is in the stylesheet whether or not the layer is drawn, so
# this looks for the markup rather than the string.
_LAYER = _re.compile(r'<svg[^>]*class="hp-st__doodles"')
check('and the whole layer can be switched off',
      not _LAYER.search(off_html) and bool(_LAYER.search(none_html)),
      'no <svg> drawn with the box unticked, one drawn with it ticked')

check('the drawings are hidden where the cards stack',
      '.hp-st__doodles { display: none; }' in off_html
      or '.hp-st__doodles { display: none; }' in none_html,
      'hidden below 990px, where there is no empty column')


print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
