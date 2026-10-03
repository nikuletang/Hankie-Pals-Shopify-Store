"""Which card images are fetched eagerly, and which are deferred.

This section sits directly below the hero on the homepage. A lazy primary
image is not requested until the scroll reaches it, so the media box holds
nothing while it decodes — on iOS that reads as a flash of the hero as the
section comes up. The primary photo therefore loads eagerly and the hover
photo, which is invisible until hover and never used on a phone, does not.

Asserted against the rendered markup rather than the source text, so the
check fails if the attribute stops reaching the <img> for any reason, not
only if someone edits the word 'eager'.
"""
import json, subprocess, sys, pathlib, re

SECTION = '/home/user/hankie-pals-shopify-store/sections/variant-grid.liquid'
HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path('/tmp/claude-0')

# Both pickers filled, so the hover <img> is rendered at all: it is wrapped in
# `if hover != blank` and would otherwise be absent, and an absent tag would
# pass a "hover is not eager" check while asserting nothing.
BLOCKS = [{'type': 'variant', 'settings': {
    'image': {'src': 'primary.png'}, 'hover_image': {'src': 'hover.png'},
}}]


def render(name, blocks):
    page = TMP / f'vgl-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps({'blocks': blocks}), str(page)],
                   check=True, capture_output=True)
    return page.read_text(encoding='utf-8')


def loading_of(html, cls):
    """The loading attribute on the <img> carrying `cls`, or None."""
    for tag in re.findall(r'<img\b[^>]*>', html):
        if cls in tag:
            m = re.search(r'loading="([^"]*)"', tag)
            return m.group(1) if m else ''
    return None


res = []
def check(label, ok, detail):
    res.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


html = render('both', BLOCKS)

primary = loading_of(html, 'hp-vg__img--primary')
hover = loading_of(html, 'hp-vg__img--hover')

check('the card photo is rendered at all',
      primary is not None,
      f"primary img {'found' if primary is not None else 'MISSING'}")

check('the card photo is fetched eagerly',
      primary == 'eager',
      f'loading={primary!r} (want "eager" — lazy here is the hero-flash bug)')

check('the hover photo is rendered at all',
      hover is not None,
      f"hover img {'found' if hover is not None else 'MISSING'}")

check('the hover photo is still deferred',
      hover == 'lazy',
      f'loading={hover!r} (want "lazy" — phones never hover, so it is waste)')

check('the two photos do not share a loading mode',
      primary != hover,
      f'primary={primary!r}  hover={hover!r}')

failed = res.count(False)
print(f"\n{res.count(True)} passed, {failed} failed")
sys.exit(1 if failed else 0)
