"""Check the mailing-list sign-up on the Pal reveal.

A sign-up form is the one thing on this site that can look completely right and
collect nothing, so most of this is about the parts you cannot see: that it is
Shopify's own customer form rather than a hand-rolled POST, that the field is
named what Shopify reads, that it carries the tag the list is built from, and
that the states nobody reaches by scrolling — posted, and refused — say
something.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
SECTION = ROOT / 'sections' / 'pal-reveal.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

PROBE = """<script>
setTimeout(function () {
  var email = document.querySelector('.hp-rv__email');
  var label = email ? document.querySelector('label[for="' + email.id + '"]') : null;
  var btn = document.querySelector('.hp-rv__row .hp-btn');
  var tags = document.querySelector('input[name="contact[tags]"]');
  var row = document.querySelector('.hp-rv__row');
  var field = email ? getComputedStyle(email) : null;

  function box(el) {
    var r = el.getBoundingClientRect();
    return { l: Math.round(r.left), r: Math.round(r.right),
             t: Math.round(r.top), b: Math.round(r.bottom),
             w: Math.round(r.width), h: Math.round(r.height) };
  }

  document.title = 'RESULT' + JSON.stringify({
    hasField: !!email,
    hasButtonCta: !!document.querySelector('.hp-rv__cta'),
    id: email ? email.id : null,
    type: email ? email.getAttribute('type') : null,
    name: email ? email.getAttribute('name') : null,
    required: email ? email.hasAttribute('required') : null,
    autocomplete: email ? email.getAttribute('autocomplete') : null,
    value: email ? email.getAttribute('value') : null,
    tags: tags ? tags.value : null,
    label: label ? { text: label.textContent.trim(),
                     display: getComputedStyle(label).display,
                     visibility: getComputedStyle(label).visibility,
                     w: Math.round(label.getBoundingClientRect().width) } : null,
    fontSize: field ? field.fontSize : null,
    fieldBg: field ? field.backgroundColor : null,
    fieldInk: field ? field.color : null,
    hint: email ? getComputedStyle(email, '::placeholder').color : null,
    fieldBox: email ? box(email) : null,
    btnBox: btn ? box(btn) : null,
    btnClass: btn ? btn.className : null,
    btnType: btn ? btn.getAttribute('type') : null,
    rowWraps: row ? getComputedStyle(row).flexWrap : null,
    msgs: [].map.call(document.querySelectorAll('.hp-rv__msg'), function (p) {
      return { role: p.getAttribute('role'), text: p.textContent.trim() }; }),
    docW: document.documentElement.scrollWidth,
    winW: window.innerWidth
  });
}, 500);
</script>"""


def run(overrides, name, width=1280):
    page = TMP / f'su-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>'),
                    encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},900', '--virtual-time-budget=3000', '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def rgb(s):
    return [int(x) for x in re.findall(r'\d+', s)[:3]]


def contrast(a, b):
    def lum(c):
        c = [x / 255 for x in c]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return round((l1 + 0.05) / (l2 + 0.05), 2)


# ----------------------------------------------- what the page cannot show ---
src = SECTION.read_text(encoding='utf-8')
check("it is Shopify's own customer form, not a POST written here",
      "{%- form 'customer'" in src and 'action=' not in src,
      "form 'customer' posts to /contact and creates the customer itself")
check('the address is tagged newsletter, which is the list Shopify Email sends to',
      'name="contact[tags]" value="newsletter"' in src,
      'hidden contact[tags] = newsletter')
check('the form id is scoped to the section, so two on a page do not collide',
      "'RevealSignup-' | append: section.id" in src
      and "'RevealEmail-' | append: section.id" in src,
      'both the form and the field append section.id')

# ------------------------------------------------------------- the field ----
d = run({}, 'default')
check('the sign-up is what comes last, not the button',
      d['hasField'] and not d['hasButtonCta'],
      f"field present: {d['hasField']}, button present: {d['hasButtonCta']}")
check('the field is named what Shopify reads',
      d['name'] == 'contact[email]' and d['type'] == 'email',
      f"{d['type']} named {d['name']}")
check('it is required, and offers the browser a saved address',
      d['required'] and d['autocomplete'] == 'email',
      f"required={d['required']}, autocomplete={d['autocomplete']}")
check('it carries the newsletter tag through',
      d['tags'] == 'newsletter', f"contact[tags] = {d['tags']}")
check('it has a label a screen reader will read',
      d['label'] and d['label']['text'] and d['label']['display'] != 'none'
      and d['label']['visibility'] != 'hidden',
      f"label \"{d['label']['text'] if d['label'] else None}\", "
      f"{d['label']['w'] if d['label'] else '-'}px wide, "
      f"display {d['label']['display'] if d['label'] else '-'}")
check('which is hidden from everyone else rather than removed',
      d['label']['w'] <= 2, f"{d['label']['w']}px wide on screen")

# 16px is the threshold below which iOS Safari zooms the page on focus and
# does not zoom back out.
check('the field is at least 16px, so a phone does not zoom in on focus',
      float(d['fontSize'][:-2]) >= 16, f"{d['fontSize']}")
check('and is a comfortable height to tap',
      d['fieldBox']['h'] >= 44, f"{d['fieldBox']['h']}px tall")
check('the submit is the site button',
      'hp-btn' in (d['btnClass'] or '') and d['btnType'] == 'submit',
      f"class \"{d['btnClass']}\", type {d['btnType']}")
check('field and button sit on one line on a desktop',
      abs(d['fieldBox']['t'] - d['btnBox']['t']) < 30
      and d['btnBox']['l'] >= d['fieldBox']['r'],
      f"field {d['fieldBox']['l']}–{d['fieldBox']['r']}, button starts {d['btnBox']['l']}")

# ---------------------------------------------------------------- reading ---
bg = rgb(d['fieldBg'])
check('what they type clears 4.5:1 in the field',
      contrast(rgb(d['fieldInk']), bg) >= 4.5,
      f"{contrast(rgb(d['fieldInk']), bg)}:1")
check('and the placeholder does too, which is the one that usually does not',
      contrast(rgb(d['hint']), bg) >= 4.5,
      f"{contrast(rgb(d['hint']), bg)}:1 — Firefox dims placeholders on its own, "
      f"so the opacity is pinned back to 1")

# ------------------------------------------------------- states and widths --
posted = run({'form': {'posted_successfully?': True}}, 'posted')
check('it says something once they have signed up',
      any(m['role'] == 'status' and m['text'] for m in posted['msgs']),
      f"{[m['text'] for m in posted['msgs']]}")
errored = run({'form': {'errors': ['Email is invalid'], 'email': 'nope@'}}, 'errors')
check('and says what went wrong when Shopify refuses it',
      any(m['role'] == 'alert' and 'invalid' in m['text'].lower() for m in errored['msgs']),
      f"{[(m['role'], m['text']) for m in errored['msgs']]}")
check('keeping what they typed, so they are not starting again',
      errored['value'] == 'nope@', f"field value after the refusal: {errored['value']!r}")
check('nothing is said before they have done anything',
      d['msgs'] == [], f"{len(d['msgs'])} messages on a fresh page")

back = run({'settings': {'cta_style': 'button'}}, 'button')
check('the button is still there for anyone who wants it back',
      back['hasButtonCta'] and not back['hasField'],
      'cta_style: button brings back the link')
unset = run({'settings': {'cta_style': ''}}, 'unset')
check('a section saved before this setting existed gets the sign-up, not nothing',
      unset['hasField'] and not unset['hasButtonCta'],
      "nil is compared against 'button', so it falls to the sign-up")

for w in (1280, 990, 750, 500):
    n = run({}, f'w{w}', width=w)
    check(f'nothing runs off the edge at {w}px',
          n['docW'] <= n['winW'] and n['fieldBox']['l'] >= 0,
          f"document {n['docW']}px in {n['winW']}px, field starts at {n['fieldBox']['l']}")

phone = run({}, 'phone', width=500)
check('field and button stack rather than squeezing on a phone',
      phone['btnBox']['t'] >= phone['fieldBox']['b'] - 4
      or phone['btnBox']['l'] >= phone['fieldBox']['r'],
      f"field ends y={phone['fieldBox']['b']}, button starts y={phone['btnBox']['t']}")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
