"""Render any of these sections to a standalone HTML page.

Settings come from the schema's own defaults and blocks from the first preset,
merged over the block schema's defaults — which is exactly what Shopify builds
when the section is added from the theme editor. Shopify's tags and filters are
stubbed only far enough to produce markup a browser can lay out.
"""
import json, re, sys, pathlib

src_path = pathlib.Path(sys.argv[1])
overrides = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
out = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else '/tmp/section.html')

src = src_path.read_text(encoding='utf-8')
schema = json.loads(re.search(r'{% schema %}(.*?){% endschema %}', src, re.S).group(1))


def defaults(rows):
    # A setting with no default is nil on the store, and Shopify counts nil as
    # blank. python-liquid does not, so an unset setting is passed as '' here:
    # both are blank, and every `!= blank` branch then takes the same side it
    # takes on the real store.
    # Keyed on having an id rather than on not being a 'header': `paragraph`
    # and `header` are both informational and carry no id, and Shopify may add
    # more of them. Anything without an id is not a setting.
    return {r['id']: r.get('default', '') for r in rows if r.get('id')}


def types(rows):
    return {r['id']: r.get('type') for r in rows if r.get('id')}


# Globals a section can reach for. Enough shape to render, not enough to be
# mistaken for the real thing: a menu with two links, a couple of policies.
def _link(title, url, links=()):
    return {'title': title, 'url': url, 'links': list(links), 'active': False,
            'child_active': False}


CART = {'item_count': 0, 'items': []}

# A stand-in for the one product this store sells. Three variants, so a
# section that resolves variants by name has something to resolve against;
# `overrides['product']` replaces it for the cases that need a different shape
# (a single variant, a combined title, a sold-out one).
def _variant(vid, title, option1, price=2400, available=True, was=None):
    # `compare_at_price` carries the price rather than nil when there is no
    # sale on. On the store it really is nil and `nil > price` is false, but
    # python-liquid raises on that comparison instead of answering it, so a
    # truthful nil would fail a section whose Liquid is correct. Same number,
    # same branch taken, no false alarm.
    return {'id': vid, 'title': title, 'option1': option1, 'option2': None,
            'option3': None, 'price': price, 'compare_at_price': was or price,
            'available': available, 'featured_image': None,
            'url': f'/products/hankie-pals?variant={vid}'}


PRODUCT = {
    'title': 'Hankie Pals',
    'handle': 'hankie-pals',
    'url': '/products/hankie-pals',
    'available': True,
    'variants': [_variant(101, 'Bunny', 'Bunny'),
                 _variant(102, 'Cow', 'Cow'),
                 _variant(103, 'Dog', 'Dog')],
}

SHOP = {
    'name': 'Totterful',
    'policies': [{'title': 'Refund policy', 'url': '/policies/refund-policy'},
                 {'title': 'Privacy policy', 'url': '/policies/privacy-policy'},
                 {'title': 'Terms of service', 'url': '/policies/terms-of-service'}],
    'enabled_payment_types': [],
}

def resolve_products(bag, kinds):
    """A product setting holds a handle in the theme's JSON; Liquid is handed
    the product itself. Without this, product.variants is nil and every
    variant-resolving branch takes the wrong side."""
    for key, kind in kinds.items():
        if kind == 'product':
            bag[key] = PRODUCT


def resolve_menus(bag, kinds):
    """A link_list setting holds a handle in the theme's JSON, but Liquid is
    handed the menu itself. Without this, block.settings.menu.links is nil and
    a footer full of menus renders as a footer full of nothing — while still
    looking like a footer."""
    for key, kind in kinds.items():
        if kind == 'link_list':
            bag[key] = LINKLISTS.get(bag.get(key), '')


LINKLISTS = {
    'main-menu': {'title': 'Shop', 'links': [_link('Home', '/'), _link('Catalog', '/collections/all'),
                                             _link('Contact', '/pages/contact')]},
    'footer': {'title': 'Help', 'links': [_link('Shipping', '/pages/shipping'),
                                          _link('Care', '/pages/care')]},
}


# A suite can blank the store's menus to stand in for a shop whose main menu
# is empty -- the one case where a header with a link_list fallback still has
# nothing to draw.
if 'linklists' in overrides:
    LINKLISTS = {k: v for k, v in overrides['linklists'].items()}

settings = defaults(schema.get('settings', []))
settings.update(overrides.get('settings', {}))
resolve_menus(settings, types(schema.get('settings', [])))
if 'product' in overrides:
    PRODUCT = overrides['product']
resolve_products(settings, types(schema.get('settings', [])))

block_schema = {b['type']: b for b in schema.get('blocks', [])}
blocks = []
preset_blocks = overrides.get('blocks')
if preset_blocks is None:
    preset_blocks = (schema.get('presets') or [{}])[0].get('blocks', [])
for i, pb in enumerate(preset_blocks):
    rows = block_schema[pb['type']].get('settings', [])
    bs = defaults(rows)
    bs.update(pb.get('settings', {}))
    resolve_menus(bs, types(rows))
    # Shopify gives every block an id, and sections key their per-block CSS off
    # it. Stable and short here, so a failure names a block you can find.
    blocks.append({'settings': bs, 'type': pb['type'], 'id': f'block{i + 1}',
                   'shopify_attributes': ''})

body = re.sub(r'{% schema %}.*?{% endschema %}', '', src, flags=re.S)
body = body.replace('{% style %}', '<style>').replace('{% endstyle %}', '</style>')

# Shopify-only tags python-liquid has never heard of. Only the markup they emit
# matters for layout, so they are reduced to it before parsing.
body = re.sub(r'{%-?\s*form\b.*?-?%}', '<form>', body, flags=re.S)
body = re.sub(r'{%-?\s*endform\s*-?%}', '</form>', body)

from liquid import Environment
env = Environment()
env.add_filter('image_url', lambda v, **kw: str(v))
env.add_filter('placeholder_svg_tag',
               lambda v, cls='': f'<svg class="{cls}" viewBox="0 0 60 60"><rect width="60" height="60"/></svg>')
env.add_filter('money', lambda v: f'${int(v)/100:,.2f}')
env.add_filter('default_errors', lambda v: '; '.join(v) if v else '')


def color_modify(value, prop, amount):
    """Shopify's colour filter, far enough for layout. Only alpha is used in
    these sections, and only on a hex colour."""
    v = str(value).strip()
    if prop != 'alpha' or not v.startswith('#'):
        return v
    h = v.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {amount})'


env.add_filter('color_modify', color_modify)
# Shopify returns the translation; returning nothing here lets a `| default:`
# behind it do the work, which is how these sections are written.
env.add_filter('t', lambda v, **kw: '')

# Sections link the shared button stylesheet through the assets folder. Pointing
# it at the real file is what lets the suite measure the button a visitor gets
# rather than a copy of it.
ASSETS = pathlib.Path(__file__).resolve().parent.parent / 'assets'
env.add_filter('asset_url', lambda v: 'file://' + str(ASSETS / str(v)))
env.add_filter('stylesheet_tag', lambda v: f'<link rel="stylesheet" href="{v}">')


def image_tag(url, **kw):
    cls = kw.get('class', '')
    rest = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items() if k != 'class')
    return f'<img src="{url}" class="{cls}" {rest}>'


env.add_filter('image_tag', image_tag)

# A Shopify form object. Passed through from the overrides so a suite can put
# the form in its posted and its errored state, which no amount of rendering
# the page normally will reach.
FORM = {'posted_successfully?': False, 'errors': None, 'email': ''}
FORM.update(overrides.get('form', {}))

html = env.from_string(body).render(shop=SHOP, linklists=LINKLISTS, form=FORM,
                                    cart=dict(CART, **overrides.get('cart', {})),
                                    routes={'root_url': '/', 'cart_url': '/cart',
                                            'cart_add_url': '/cart/add',
                                            'search_url': '/search'},
                                    settings={},
                                    section={
    'settings': settings,
    'blocks': blocks,
    'id': 'test-section',
    'shopify_attributes': '',
}, request={'design_mode': False})

page = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  /* Dawn's own reset, so a section lays out here the way it will there.
     Without the border-box line, `width: 100%` plus padding overflows in this
     page and nowhere else -- inventing overflow bugs that do not exist on the
     store, which is worse than missing one. */
  *, *::before, *::after {{ box-sizing: border-box; }}

  /* Dawn's root: 1rem renders at 10px, so any stray rem shows up here the way
     it would on the real store. */
  html {{ font-size: calc(var(--font-body-scale, 1) * 62.5%); }}
  body {{ margin: 0; --font-body-scale: 1; --font-heading-scale: 1;
          --font-heading-weight: 700;
          --font-heading-family: Futura, "Century Gothic", system-ui, sans-serif;
          --font-body-family: ui-rounded, "Segoe UI Rounded", system-ui, sans-serif; }}
</style>
</head><body>{html}</body></html>"""

out.write_text(page, encoding='utf-8')
print(out)
