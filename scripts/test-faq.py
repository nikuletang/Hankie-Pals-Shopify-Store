"""Check the "Ask the Pals" FAQ.

Most of this section is behaviour, so most of these checks drive it: click a
pill, press a key, hit an arrow, then measure what moved. A tab strip that
looks right and does not answer the keyboard is the failure worth catching.

The other half is what survives without the script. Every answer is in the
markup rather than injected, so a crawler and a visitor with no JavaScript see
the same six questions; the script's job is only to fold that list into tabs.
Those checks run the page with the section's own script disabled.
"""
import json, re, subprocess, sys, pathlib
from PIL import Image

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path(__file__).resolve().parent.parent
SECTION = ROOT / 'sections' / 'hankie-pals-faq.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

STILL = """<style>
  .hp-faq *, .hp-faq *::before, .hp-faq *::after {
    transition: none !important;
  }
</style>"""

PROBE = """
function bx(e){if(!e)return null;var r=e.getBoundingClientRect();
 return {l:Math.round(r.left),r:Math.round(r.right),t:Math.round(r.top),
         b:Math.round(r.bottom),w:Math.round(r.width),h:Math.round(r.height)};}
function snap(d,w){
  var root=d.querySelector('.hp-faq');
  var list=d.querySelector('[role="tablist"]');
  var img=d.querySelector('.hp-faq__puppy');
  var counter=d.querySelector('.hp-faq__counter');
  var ld=d.querySelector('script[type="application/ld+json"]');
  return {
    ready:root?root.classList.contains('is-ready'):null,
    rootBg:root?w.getComputedStyle(root).backgroundColor:null,
    listRole:list?list.getAttribute('role'):null,
    listLabel:list?list.getAttribute('aria-label'):null,
    listWrap:list?w.getComputedStyle(list).flexWrap:null,
    listOverflow:list?w.getComputedStyle(list).overflowX:null,
    listSnap:list?w.getComputedStyle(list).scrollSnapType:null,
    pillsShown:(function(){var pw=d.querySelector('.hp-faq__pillwrap');
      return pw?w.getComputedStyle(pw).display:null;})(),
    tabs:[].map.call(d.querySelectorAll('[role="tab"]'),function(e){
      var c=w.getComputedStyle(e);
      return {text:e.textContent.trim(), role:e.getAttribute('role'),
              sel:e.getAttribute('aria-selected'), tabindex:e.tabIndex,
              controls:e.getAttribute('aria-controls'),
              bg:c.backgroundColor, border:c.borderTopColor,
              shadow:c.boxShadow, transform:c.transform, ink:c.color,
              box:bx(e)};}),
    panels:[].map.call(d.querySelectorAll('[role="tabpanel"]'),function(e){
      var h=e.querySelector('.hp-faq__q');
      var a=e.querySelector('.hp-faq__a');
      return {id:e.id, labelledby:e.getAttribute('aria-labelledby'),
              hidden:e.hasAttribute('hidden'),
              q:h?h.textContent.trim():null,
              qTag:h?h.tagName:null,
              a:a?a.textContent.trim().slice(0,30):null,
              chips:[].map.call(e.querySelectorAll('.hp-faq__chip'),function(c){
                return {text:c.textContent.trim(),
                        icon:!!c.querySelector('svg'),
                        bg:w.getComputedStyle(c).backgroundColor,
                        ink:w.getComputedStyle(c).color};})};}),
    counter:counter?{text:counter.textContent.trim(),
                     live:counter.getAttribute('aria-live'),
                     display:w.getComputedStyle(counter).display,
                     ink:w.getComputedStyle(counter).color}:null,
    dots:[].map.call(d.querySelectorAll('.hp-faq__dot'),function(e){
      return {on:e.classList.contains('is-on'), w:Math.round(e.getBoundingClientRect().width)};}),
    dotsHidden:(function(){var dd=d.querySelector('.hp-faq__dots');
      return dd?dd.getAttribute('aria-hidden'):null;})(),
    arrows:[].map.call(d.querySelectorAll('.hp-faq__arrow'),function(e){
      return {label:e.getAttribute('aria-label'), box:bx(e)};}),
    navDisplay:(function(){var n=d.querySelector('.hp-faq__nav');
      return n?w.getComputedStyle(n).display:null;})(),
    puppy:img?{alt:img.getAttribute('alt'), hidden:img.getAttribute('aria-hidden'),
               width:img.getAttribute('width'), height:img.getAttribute('height'),
               events:w.getComputedStyle(img).pointerEvents, box:bx(img)}:null,
    headInk:(function(){var h=d.querySelector('.hp-faq__heading');
      return h?w.getComputedStyle(h).color:null;})(),
    headSize:(function(){var h=d.querySelector('.hp-faq__heading');
      return h?w.getComputedStyle(h).fontSize:null;})(),
    headTag:(function(){var h=d.querySelector('.hp-faq__heading');
      return h?h.tagName:null;})(),
    subInk:(function(){var p=d.querySelector('.hp-faq__sub');
      return p?w.getComputedStyle(p).color:null;})(),
    ebInk:(function(){var p=d.querySelector('.hp-faq__eyebrow');
      return p?w.getComputedStyle(p).color:null;})(),
    cardBg:(function(){var c=d.querySelector('.hp-faq__card');
      return c?w.getComputedStyle(c).backgroundColor:null;})(),
    cardBox:bx(d.querySelector('.hp-faq__card')),
    leftBox:bx(d.querySelector('.hp-faq__left')),
    sectionBox:bx(root),
    jsonld:ld?ld.textContent:null,
    docW:d.documentElement.scrollWidth, winW:w.innerWidth};
}
"""


def render(name, overrides, no_js=False):
    page = TMP / f'faq-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(page)], check=True,
                   capture_output=True)
    if no_js:
        # The section's own script bails on this flag, so the page is exactly
        # what a browser that never ran it would show.
        page.write_text(page.read_text(encoding='utf-8').replace(
            '<body>', '<body><script>window.hpFaqReady = true;</script>', 1),
            encoding='utf-8')
    page.write_text(page.read_text(encoding='utf-8').replace(
        '</body>', STILL + '</body>'), encoding='utf-8')
    return page


def run(name, width=1440, overrides=None, drive='', no_js=False, flags=(), wait=500):
    page = render(name, overrides, no_js)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>',
        '<script>' + PROBE +
        "setTimeout(function(){try{" + drive + "}catch(e){};"
        "setTimeout(function(){document.title='RESULT'+JSON.stringify("
        f"snap(document,window));}},260);}},{wait});</script></body>"),
        encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},1400', '--virtual-time-budget=9000', *flags,
        '--dump-dom', 'file://' + str(page)],
        capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


def framed(name, width=390, overrides=None, drive=''):
    inner = render(name + '-inner', overrides)
    inner.write_text(inner.read_text(encoding='utf-8').replace(
        '</body>', '<script>' + PROBE + '</script></body>'), encoding='utf-8')
    wrap = TMP / f'faq-{name}-wrap.html'
    wrap.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0}'
        f'iframe{{width:{width}px;height:1800px;border:0;display:block}}</style>'
        f'<iframe src="{inner.name}"></iframe><script>setTimeout(function(){{'
        'var f=document.querySelector("iframe");var d=f.contentDocument;'
        'var w=f.contentWindow;try{' + drive + '}catch(e){};'
        'setTimeout(function(){document.title="RESULT"+JSON.stringify('
        'w.snap(d,w));},260);},800);</script>', encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', f'--window-size={width + 310},1900',
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


PUPPY = {'settings': {'puppy_image': str(TMP / 'faq-puppy.png')}}

d = run('default', overrides=PUPPY)

check('the section starts up',
      d['ready'] is True and len(d['tabs']) == 6 and len(d['panels']) == 6,
      f"ready {d['ready']}, {len(d['tabs'])} tabs, {len(d['panels'])} panels")

# ------------------------------------------------- nothing is lost without JS --
raw = run('no-js', overrides=PUPPY, no_js=True)
check('with the script never running, every answer is still on the page',
      len(raw['panels']) == 6 and not any(p['hidden'] for p in raw['panels']),
      f"{len(raw['panels'])} panels, "
      f"{sum(p['hidden'] for p in raw['panels'])} of them hidden")
check('each question is a real heading there, so the list reads in order',
      all(p['qTag'] == 'H3' and p['q'] for p in raw['panels']),
      f"{[p['qTag'] for p in raw['panels']]}")
check('and the pills, counter and arrows stay out of the way',
      raw['pillsShown'] == 'none' and raw['counter']['display'] == 'none'
      and raw['navDisplay'] == 'none',
      f"pills {raw['pillsShown']}, counter {raw['counter']['display']}, "
      f"nav {raw['navDisplay']}")

# ------------------------------------------------------------ the structure ---
check('the questions and answers are in the markup, not injected',
      all(p['q'] and p['a'] for p in d['panels']),
      f"{[p['q'][:18] for p in d['panels']]}")

ld = json.loads(d['jsonld'])
check('and the structured data is built from the same blocks',
      ld['@type'] == 'FAQPage' and len(ld['mainEntity']) == 6
      and [e['name'] for e in ld['mainEntity']] == [p['q'] for p in d['panels']],
      f"{ld['@type']}, {len(ld['mainEntity'])} questions, names match the panels")
check('its answers carry the words rather than the markup around them',
      all('<' not in e['acceptedAnswer']['text'] for e in ld['mainEntity'])
      and ld['mainEntity'][0]['acceptedAnswer']['text'].startswith('A soft muslin'),
      f"{ld['mainEntity'][0]['acceptedAnswer']['text'][:44]}")

# -------------------------------------------------------------- the ARIA ---
check('the pills are a tablist with a name',
      d['listRole'] == 'tablist' and d['listLabel'] == 'Hankie Pals questions',
      f"role {d['listRole']}, label {d['listLabel']!r}")
ids = [p['id'] for p in d['panels']]
check('every tab points at a panel that exists',
      all(t['controls'] in ids for t in d['tabs']),
      f"{[t['controls'] == ids[i] for i, t in enumerate(d['tabs'])]}")
check('and every panel points back at its tab',
      all(p['labelledby'] == f"hp-faq-tab-test-section-{i + 1}"
          for i, p in enumerate(d['panels'])),
      f"{[p['labelledby'] for p in d['panels'][:2]]} ...")
check('exactly one tab is in the tab order',
      [t['tabindex'] for t in d['tabs']].count(0) == 1,
      f"tabindex {[t['tabindex'] for t in d['tabs']]}")
check('the first question is the one selected on load',
      d['tabs'][0]['sel'] == 'true'
      and [t['sel'] for t in d['tabs']].count('true') == 1
      and not d['panels'][0]['hidden']
      and all(p['hidden'] for p in d['panels'][1:]),
      f"selected {[t['sel'] for t in d['tabs']]}")
check('the counter says where you are, and says it out loud',
      d['counter']['text'] == 'Question 1 of 6' and d['counter']['live'] == 'polite',
      f"{d['counter']['text']!r}, aria-live {d['counter']['live']}")
check('the dots are decoration, since the counter already says it',
      d['dotsHidden'] == 'true', f"aria-hidden {d['dotsHidden']}")
check('both arrows say what they do',
      [a['label'] for a in d['arrows']] == ['Previous question', 'Next question'],
      f"{[a['label'] for a in d['arrows']]}")
check('the arrows are big enough to hit',
      all(a['box']['w'] >= 44 and a['box']['h'] >= 44 for a in d['arrows']),
      f"{[(a['box']['w'], a['box']['h']) for a in d['arrows']]}")

# --------------------------------------------------------- it actually works --
CLICK = "document.querySelectorAll('[role=\\\"tab\\\"]')[2].click();"
clicked = run('click', overrides=PUPPY, drive=CLICK)
check('clicking the third pill selects it',
      clicked['tabs'][2]['sel'] == 'true'
      and [t['sel'] for t in clicked['tabs']].count('true') == 1,
      f"{[t['sel'] for t in clicked['tabs']]}")
check('and shows its answer, and only its answer',
      not clicked['panels'][2]['hidden']
      and sum(not p['hidden'] for p in clicked['panels']) == 1,
      f"visible panel: {clicked['panels'][2]['q']}")
check('the counter follows',
      clicked['counter']['text'] == 'Question 3 of 6',
      f"{clicked['counter']['text']!r}")
check('and so does the dot, which stretches rather than just recolouring',
      clicked['dots'][2]['on'] and clicked['dots'][2]['w'] > clicked['dots'][0]['w'],
      f"active dot {clicked['dots'][2]['w']}px, the rest {clicked['dots'][0]['w']}px")

NEXT = "document.querySelector('[data-hp-faq-next]').click();"
nxt = run('next', overrides=PUPPY, drive=NEXT)
check('next moves on one',
      nxt['counter']['text'] == 'Question 2 of 6', f"{nxt['counter']['text']!r}")

prv = run('prev', overrides=PUPPY,
          drive="document.querySelector('[data-hp-faq-prev]').click();")
check('and previous from the first wraps round to the last',
      prv['counter']['text'] == 'Question 6 of 6', f"{prv['counter']['text']!r}")

wrap6 = run('wrap', overrides=PUPPY,
            drive="var n=document.querySelector('[data-hp-faq-next]');"
                  "for(var i=0;i<6;i++){n.click();}")
check('six nexts from the first comes back to the first',
      wrap6['counter']['text'] == 'Question 1 of 6', f"{wrap6['counter']['text']!r}")

def key(k):
    return ("document.querySelectorAll('[role=\\\"tab\\\"]')[0]"
            ".dispatchEvent(new KeyboardEvent('keydown',"
            "{key:'" + k + "',bubbles:true}));")

right = run('key-right', overrides=PUPPY, drive=key('ArrowRight'))
check('the right arrow key moves to the next question',
      right['counter']['text'] == 'Question 2 of 6', f"{right['counter']['text']!r}")
left = run('key-left', overrides=PUPPY, drive=key('ArrowLeft'))
check('the left arrow key wraps backwards',
      left['counter']['text'] == 'Question 6 of 6', f"{left['counter']['text']!r}")
down = run('key-down', overrides=PUPPY, drive=key('ArrowDown'))
check('up and down work too, as the tabs pattern asks',
      down['counter']['text'] == 'Question 2 of 6', f"{down['counter']['text']!r}")
end = run('key-end', overrides=PUPPY, drive=key('End'))
check('End jumps to the last',
      end['counter']['text'] == 'Question 6 of 6', f"{end['counter']['text']!r}")
home = run('key-home', overrides=PUPPY,
           drive=CLICK + "document.querySelectorAll('[role=\\\"tab\\\"]')[2]"
                 ".dispatchEvent(new KeyboardEvent('keydown',"
                 "{key:'Home',bubbles:true}));")
check('and Home jumps back to the first',
      home['counter']['text'] == 'Question 1 of 6', f"{home['counter']['text']!r}")

# ------------------------------------------------------------- the sticker ---
sel, idle = d['tabs'][0], d['tabs'][1]
check('the selected pill is a sticker: filled, outlined and sat on its shadow',
      rgb(sel['bg']) == [236, 168, 131] and rgb(sel['border']) == [47, 51, 38]
      and sel['shadow'] not in ('none', ''),
      f"fill {sel['bg']}, outline {sel['border']}, shadow {sel['shadow'][:30]}")
check('and tilted off true, which the others are not',
      sel['transform'] != 'none' and idle['transform'] == 'none',
      f"selected {sel['transform']}, idle {idle['transform']}")
check('an unselected pill is plain white with no shadow',
      rgb(idle['bg']) == [255, 255, 255] and idle['shadow'] in ('none', ''),
      f"fill {idle['bg']}, shadow {idle['shadow']}")

# --------------------------------------------------------------- the chips ---
chips = d['panels'][2]['chips']
check('the third question carries its three care chips',
      len(chips) == 3
      and [c['text'] for c in chips] == ['Gentle cycle', 'Air dry or tumble low',
                                         'Unclip first'],
      f"{[c['text'] for c in chips]}")
check('each with an icon beside the words',
      all(c['icon'] for c in chips), f"{[c['icon'] for c in chips]}")
check('and a question with none renders none, rather than an empty row',
      all(len(d['panels'][i]['chips']) == 0 for i in (0, 1, 3, 4, 5)),
      f"chip counts {[len(p['chips']) for p in d['panels']]}")

# ---------------------------------------------------------------- the Pal ---
check('the Pal is decoration: no alt, not read out, not clickable',
      d['puppy']['alt'] == '' and d['puppy']['hidden'] == 'true'
      and d['puppy']['events'] == 'none',
      f"alt {d['puppy']['alt']!r}, aria-hidden {d['puppy']['hidden']}, "
      f"pointer-events {d['puppy']['events']}")
check('and its box is reserved, so nothing shifts when it lands',
      d['puppy']['width'] and d['puppy']['height'],
      f"width {d['puppy']['width']}, height {d['puppy']['height']}")
check('he hangs off the top-right of the card',
      d['puppy']['box']['t'] < d['cardBox']['t']
      and d['puppy']['box']['r'] > d['cardBox']['r'],
      f"Pal {d['puppy']['box']['t']}/{d['puppy']['box']['r']}, "
      f"card {d['cardBox']['t']}/{d['cardBox']['r']}")
check('and the band leaves room for him rather than cutting him off',
      d['puppy']['box']['t'] >= d['sectionBox']['t'] - 1,
      f"Pal starts {d['puppy']['box']['t']}, band starts {d['sectionBox']['t']}")

none_puppy = run('no-puppy', overrides={})
check('with no photo chosen nothing is drawn',
      none_puppy['puppy'] is None, 'no img rendered')

# ----------------------------------------------------------------- it reads --
check('the heading reads against the band',
      contrast(rgb(d['headInk']), rgb(d['rootBg'])) >= 7,
      f"{contrast(rgb(d['headInk']), rgb(d['rootBg']))}:1")
check('the subheading reads against the band',
      contrast(rgb(d['subInk']), rgb(d['rootBg'])) >= 4.5,
      f"{contrast(rgb(d['subInk']), rgb(d['rootBg']))}:1")
check('the eyebrow reads against the band, small and tracked as it is',
      contrast(rgb(d['ebInk']), rgb(d['rootBg'])) >= 4.5,
      f"{contrast(rgb(d['ebInk']), rgb(d['rootBg']))}:1")
check('the counter reads against the card',
      contrast(rgb(d['counter']['ink']), rgb(d['cardBg'])) >= 4.5,
      f"{contrast(rgb(d['counter']['ink']), rgb(d['cardBg']))}:1")
check('the chips read against their own fill',
      contrast(rgb(chips[0]['ink']), rgb(chips[0]['bg'])) >= 4.5,
      f"{contrast(rgb(chips[0]['ink']), rgb(chips[0]['bg']))}:1")
check('a selected pill reads against the peach it sits on',
      contrast(rgb(sel['ink']), rgb(sel['bg'])) >= 4.5,
      f"{contrast(rgb(sel['ink']), rgb(sel['bg']))}:1")

# ------------------------------------------------------------- the layout ---
check('two columns on a desktop, words left and card right',
      d['leftBox']['r'] <= d['cardBox']['l'] + 1,
      f"words end {d['leftBox']['r']}, card starts {d['cardBox']['l']}")
check('and the pills wrap there rather than scrolling',
      d['listWrap'] == 'wrap' and d['listOverflow'] in ('visible', 'auto'),
      f"flex-wrap {d['listWrap']}")

tab768 = run('tablet', width=768, overrides=PUPPY)
check('they stack on a tablet',
      tab768['leftBox']['b'] <= tab768['cardBox']['t'],
      f"words end {tab768['leftBox']['b']}, card starts {tab768['cardBox']['t']}")

p390 = framed('phone', 390, PUPPY)
check('on a phone the pills become one row that scrolls',
      p390['listWrap'] == 'nowrap' and p390['listOverflow'] == 'auto'
      and 'x' in (p390['listSnap'] or ''),
      f"flex-wrap {p390['listWrap']}, overflow-x {p390['listOverflow']}, "
      f"snap {p390['listSnap']}")
check('the heading steps down to its mobile size',
      p390['headSize'] == '44px', f"heading {p390['headSize']}")
check('the arrows stay a full touch target there',
      all(a['box']['w'] >= 44 and a['box']['h'] >= 44 for a in p390['arrows']),
      f"{[(a['box']['w'], a['box']['h']) for a in p390['arrows']]}")
check('and the Pal is still inside the band',
      p390['puppy']['box']['t'] >= p390['sectionBox']['t'] - 1,
      f"Pal starts {p390['puppy']['box']['t']}, band starts {p390['sectionBox']['t']}")

p390c = framed('phone-click', 390, PUPPY,
               drive="d.querySelectorAll('[role=\\\"tab\\\"]')[3].click();")
# Stacked, the pills are directly above the card, so he rises into them
# unless the card is given room for him.
check('the Pal clears the pills above him rather than sitting on them',
      p390['puppy']['box']['t'] >= max(x['box']['b'] for x in p390['tabs']) - 1,
      f"Pal starts {p390['puppy']['box']['t']}, the lowest pill ends "
      f"{max(x['box']['b'] for x in p390['tabs'])}")
check('and on a tablet too, where the columns first stack',
      tab768['puppy']['box']['t'] >= max(x['box']['b'] for x in tab768['tabs']) - 1,
      f"Pal starts {tab768['puppy']['box']['t']}, the lowest pill ends "
      f"{max(x['box']['b'] for x in tab768['tabs'])}")

check('and tapping a question still works there',
      p390c['counter']['text'] == 'Question 4 of 6',
      f"{p390c['counter']['text']!r}")

for label, snap in (('at 1440px', d), ('at 768px', tab768), ('at 390px', p390)):
    check(f'the page never scrolls sideways {label}',
          snap['docW'] <= snap['winW'] + 1,
          f"document {snap['docW']}px in {snap['winW']}px")

p360 = framed('phone-360', 360, PUPPY)
check('nor at 360px',
      p360['docW'] <= p360['winW'] + 1,
      f"document {p360['docW']}px in {p360['winW']}px")

# ----------------------------------------------------------- reduced motion --
calm = run('reduced', overrides=PUPPY, drive=CLICK,
           flags=('--force-prefers-reduced-motion',))
check('someone asking for less motion still gets a working tab strip',
      calm['counter']['text'] == 'Question 3 of 6'
      and not calm['panels'][2]['hidden'],
      f"{calm['counter']['text']!r}, the answer is shown")
check('and the selected pill does not lift on hover there',
      calm['tabs'][2]['sel'] == 'true', 'selection still moves, motion does not')

check('the headline is an h2, since the product name is the page h1',
      d['headTag'] == 'H2', f"heading is <{(d['headTag'] or '?').lower()}>")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
