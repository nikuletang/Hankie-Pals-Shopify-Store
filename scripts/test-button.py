"""Check that there is one button on this site.

Every section that has a button links assets/hp-button.css and sets two colours;
nothing else about the button is a per-section decision. This suite renders each
of those sections for real, links the real stylesheet, and compares the computed
style of every button against every other one — which is the check that would
have caught the drift this replaces, where four sections had three sizes, two
shapes and two casings between them.
"""
import json, subprocess, sys, pathlib, re

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

# Sections are found, not listed. A new section with a button is picked up and
# held to the same rules without anyone remembering to add it here — which is
# the only version of "consistent" that survives the next section.
SECTION_DIR = ROOT / 'sections'
LINK = "{{ 'hp-button.css' | asset_url | stylesheet_tag }}"

def has_button(src):
    """A call to action, which is what the shared button is for.

    Not simply a <button>: solution-tabs' tab is a full-width card you click to
    switch panels and why-choose's is a text link. Those are controls, not calls
    to action, and turning them into pills would be worse, not more consistent.
    What marks a real one is the section offering a label and a link for it.
    """
    return ('hp-btn' in src or '"id": "button_label"' in src
            or '"id": "btn_fill"' in src)

# Most sections need a label before they draw anything; a few need more.
EXTRA = {
    'pals-picker': {'blocks': [{'type': 'pal', 'settings': {
        'name': 'Pip', 'link': '#', 'link_label': 'Meet Pip'}}]},
}

SECTIONS = {}
for f in sorted(SECTION_DIR.glob('*.liquid')):
    src = f.read_text(encoding='utf-8')
    if not has_button(src):
        continue
    ov = {'settings': {'button_label': 'Shop the Pals'}}
    ov.update(EXTRA.get(f.stem, {}))
    SECTIONS[f.stem] = ov

PROBE = """<script>
// A button in every state the stylesheet has to cover, including the ones no
// section can reach without a live product.
var probe = document.createElement('div');
probe.id = 'probe';
probe.style.cssText = 'position:absolute;left:-9999px;top:0';
probe.innerHTML =
  '<a class="hp-btn" id="p-base">Base</a>' +
  '<a class="hp-btn hp-btn--lg" id="p-lg">Large</a>' +
  '<a class="hp-btn hp-btn--sm" id="p-sm">Small</a>' +
  '<a class="hp-btn hp-btn--ghost" id="p-ghost">Ghost</a>' +
  '<button class="hp-btn" id="p-off" disabled>Sold out</button>';
document.body.appendChild(probe);

function read(el) {
  var c = getComputedStyle(el);
  return {
    id: el.id || el.className,
    radius: c.borderTopLeftRadius,
    borderW: c.borderTopWidth,
    borderC: c.borderTopColor,
    shadow: c.boxShadow,
    padY: c.paddingTop,
    padX: c.paddingLeft,
    fontSize: c.fontSize,
    fontWeight: c.fontWeight,
    family: c.fontFamily,
    tracking: c.letterSpacing,
    transform: c.textTransform,
    bg: c.backgroundColor,
    ink: c.color,
    drop: c.getPropertyValue('--hp-btn-drop').trim(),
    transition: c.transitionProperty,
    display: c.display
  };
}

// What the shared rules say for states a headless run cannot enter.
function rulesFor(sel) {
  var out = {};
  for (var i = 0; i < document.styleSheets.length; i++) {
    var sheet = document.styleSheets[i], rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }
    if (!rules) continue;
    for (var j = 0; j < rules.length; j++) {
      var r = rules[j];
      if (r.selectorText === sel) {
        out.transform = r.style.transform || out.transform;
        out.shadow = r.style.boxShadow || out.shadow;
        out.outline = r.style.outline || out.outline;
      }
    }
  }
  return out;
}

setTimeout(function () {
  var buttons = [].map.call(document.querySelectorAll('.hp-btn'), read);
  document.title = 'RESULT' + JSON.stringify({
    // If the stylesheet did not load, every button matches every other one at
    // the browser's defaults and every comparison below passes for free.
    sheetLoaded: (function () {
      for (var i = 0; i < document.styleSheets.length; i++) {
        var h = document.styleSheets[i].href || '';
        if (h.indexOf('hp-button.css') !== -1) {
          try { return document.styleSheets[i].cssRules.length > 0; }
          catch (e) { return false; }
        }
      }
      return false;
    })(),
    buttons: buttons,
    hover: rulesFor('.hp-btn:hover'),
    active: rulesFor('.hp-btn:active'),
    focus: rulesFor('.hp-btn:focus-visible')
  });
}, 600);
</script>"""


def run(section, overrides, width=1280, flags=()):
    page = TMP / f'btn-{section}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'),
                    str(ROOT / 'sections' / f'{section}.liquid'),
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>'),
                    encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},900', '--virtual-time-budget=4000', '--allow-file-access-from-files',
        *flags, '--dump-dom', 'file://' + str(page)],
        capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + section)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def rgb(s):
    n = [int(x) for x in re.findall(r'\d+', s)[:3]]
    return n


def contrast(a, b):
    def lum(c):
        c = [x / 255 for x in c]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return round((l1 + 0.05) / (l2 + 0.05), 2)


# ------------------------------------------------- before the browser ----
# Two things a rendered page cannot tell you: whether a section that has no
# button today would get the right one tomorrow, and whether a section is
# quietly redrawing the button underneath the shared rules.
missing = [f.stem for f in sorted(SECTION_DIR.glob('*.liquid'))
           if has_button(f.read_text(encoding='utf-8'))
           and LINK not in f.read_text(encoding='utf-8')]
check('every section with a button links the shared stylesheet',
      not missing,
      f"{len(SECTIONS)} sections with buttons: {', '.join(SECTIONS)}"
      if not missing else 'not linked: ' + ', '.join(missing))

ON_CLASS = re.compile(r'class="[^"]*\bhp-btn\b')
unclassed = [f.stem for f in sorted(SECTION_DIR.glob('*.liquid'))
             if has_button(f.read_text(encoding='utf-8'))
             and not ON_CLASS.search(f.read_text(encoding='utf-8'))]
check('and puts every button on the shared class',
      not unclassed,
      'all of them' if not unclassed else 'not on hp-btn: ' + ', '.join(unclassed))

# A section may place its button and may hand it colours. Setting any of these
# on a button selector is drawing a second button.
BANNED = ('border-radius', 'box-shadow', 'text-transform', 'letter-spacing',
          'font-size', 'padding', 'background')
redrawn = []
for f in sorted(SECTION_DIR.glob('*.liquid')):
    src = f.read_text(encoding='utf-8')
    if not ON_CLASS.search(src):
        continue
    for m in re.finditer(r'^( *)(\.hp-[a-z-]+__(?:cta|button)\b[^{]*)\{([^}]*)\}',
                         src, re.M):
        body = m.group(3)
        for prop in BANNED:
            # --hp-btn-padding-y and the like are how a section is meant to ask.
            if re.search(r'(?<!-)\b' + prop + r'\s*:', body):
                redrawn.append(f"{f.stem}: {m.group(2).strip()} sets {prop}")
check('no section redraws the button under the shared rules',
      not redrawn,
      'none' if not redrawn else '; '.join(redrawn))

data = {name: run(name, ov) for name, ov in SECTIONS.items()}

check('every section loads the shared stylesheet',
      all(d['sheetLoaded'] for d in data.values()),
      ', '.join(f"{k} {'yes' if v['sheetLoaded'] else 'NO'}" for k, v in data.items()))

# Buttons that belong to a section, not to the probe.
real = {k: [b for b in v['buttons'] if not b['id'].startswith('p-')] for k, v in data.items()}
check('every section has at least one button on the shared class',
      all(len(v) > 0 for v in real.values()),
      ', '.join(f"{k}: {len(v)}" for k, v in real.items()))

everything = [(k, b) for k, v in real.items() for b in v]

# The properties that make it the same button. Padding and size are allowed to
# differ, but only by size class, which the probe checks separately.
# Tracking is declared in em, so it resolves to a different number of pixels at
# each size. The ratio is the thing that has to match.
for _, b in everything:
    b['trackRatio'] = round(float(b['tracking'][:-2]) / float(b['fontSize'][:-2]), 3)

for prop, label in (('radius', 'corner radius'), ('borderW', 'outline weight'),
                    ('borderC', 'outline colour'), ('transform', 'capitalisation'),
                    ('trackRatio', 'letter spacing, as a share of the size'),
                    ('fontWeight', 'weight'), ('family', 'typeface')):
    values = {b[prop] for _, b in everything}
    check(f'the {label} is the same in every section',
          len(values) == 1,
          '; '.join(f"{k}: {b[prop]}" for k, b in everything) if len(values) > 1
          else f"{everything[0][1][prop]} everywhere ({len(everything)} buttons)")

check('the pill is a pill, so the stylesheet really is in force',
      all(b['radius'] == '999px' for _, b in everything),
      f"{ {b['radius'] for _, b in everything} }")

shadows = {b['shadow'].split(')')[-1].strip() for _, b in everything}
check('every shadow is hard, straight down, and unblurred',
      all(re.fullmatch(r'0px \d+px 0px 0px', b['shadow'].split(') ')[-1].strip())
          for _, b in everything),
      '; '.join(f"{k}: {b['shadow'].split(') ')[-1].strip()}" for k, b in everything))

check('the shadow is the same colour as the outline',
      all(b['shadow'].startswith(b['borderC'].replace('rgb', 'rgb')) or
          rgb(b['shadow']) == rgb(b['borderC']) for _, b in everything),
      '; '.join(f"{k}: shadow {rgb(b['shadow'])} outline {rgb(b['borderC'])}"
                for k, b in everything))

worst = min((contrast(rgb(b['ink']), rgb(b['bg'])), k, b['id'])
            for k, b in everything if b['bg'] != 'rgba(0, 0, 0, 0)')
check('the label clears 4.5:1 on every fill in use',
      worst[0] >= 4.5,
      f"lowest {worst[0]}:1 ({worst[1]}, {worst[2]}); "
      + ', '.join(f"{k} {contrast(rgb(b['ink']), rgb(b['bg']))}" for k, b in everything
                  if b['bg'] != 'rgba(0, 0, 0, 0)'))

# ---------------------------------------------------------------- states --
d = data['hero-split']
probe = {b['id']: b for b in d['buttons'] if b['id'].startswith('p-')}
check('the press travels exactly the height of the shadow',
      d['active']['transform'] == 'translateY(var(--hp-btn-drop))' and
      re.fullmatch(r'0(px)? 0(px)? 0(px)? 0(px)? var\(--hp-btn-line\)',
                   d['active']['shadow'].strip()),
      f"active: transform {d['active']['transform']}, box-shadow {d['active']['shadow']}")
check('hover lifts and lengthens the shadow rather than moving it sideways',
      d['hover']['transform'] == 'translateY(-2px)' and '0 calc' in d['hover']['shadow'],
      f"hover: transform {d['hover']['transform']}, box-shadow {d['hover']['shadow']}")
check('focus draws a ring in the outline colour',
      'var(--hp-btn-line)' in (d['focus'].get('outline') or ''),
      f"focus outline: {d['focus'].get('outline')}")

check('the three sizes step in the right direction',
      float(probe['p-sm']['padX'][:-2]) < float(probe['p-base']['padX'][:-2])
      < float(probe['p-lg']['padX'][:-2]) and
      float(probe['p-sm']['fontSize'][:-2]) < float(probe['p-lg']['fontSize'][:-2]),
      f"small {probe['p-sm']['padY']}/{probe['p-sm']['padX']} at {probe['p-sm']['fontSize']}, "
      f"default {probe['p-base']['padY']}/{probe['p-base']['padX']} at {probe['p-base']['fontSize']}, "
      f"large {probe['p-lg']['padY']}/{probe['p-lg']['padX']} at {probe['p-lg']['fontSize']}")
check('each size keeps a shadow in proportion to itself',
      all(probe[k]['drop'] for k in ('p-sm', 'p-base', 'p-lg')) and
      int(probe['p-sm']['drop'][:-2]) < int(probe['p-lg']['drop'][:-2]),
      f"small {probe['p-sm']['drop']}, default {probe['p-base']['drop']}, large {probe['p-lg']['drop']}")
check('the quiet one keeps the outline and drops the fill',
      probe['p-ghost']['bg'] == 'rgba(0, 0, 0, 0)' and
      probe['p-ghost']['radius'] == probe['p-base']['radius'] and
      probe['p-ghost']['borderW'] == probe['p-base']['borderW'],
      f"ghost: background {probe['p-ghost']['bg']}, outline {probe['p-ghost']['borderW']} "
      f"{probe['p-ghost']['radius']}")
check('a sold-out button sits flat, with no shadow to press',
      probe['p-off']['shadow'] == 'none' and
      contrast(rgb(probe['p-off']['ink']), rgb(probe['p-off']['bg'])) >= 4.5,
      f"shadow {probe['p-off']['shadow']}, "
      f"{contrast(rgb(probe['p-off']['ink']), rgb(probe['p-off']['bg']))}:1")

rm = run('hero-split', {}, flags=('--force-prefers-reduced-motion',))
check('nothing moves for a visitor who asked for less motion',
      all(b['transition'] == 'none' for b in rm['buttons']),
      f"transition-property {[b['transition'] for b in rm['buttons']][:2]}")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
