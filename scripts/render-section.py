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
    return {r['id']: r.get('default', '') for r in rows if r.get('type') != 'header'}


settings = defaults(schema.get('settings', []))
settings.update(overrides.get('settings', {}))

block_schema = {b['type']: b for b in schema.get('blocks', [])}
blocks = []
preset_blocks = overrides.get('blocks')
if preset_blocks is None:
    preset_blocks = (schema.get('presets') or [{}])[0].get('blocks', [])
for i, pb in enumerate(preset_blocks):
    bs = defaults(block_schema[pb['type']].get('settings', []))
    bs.update(pb.get('settings', {}))
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

html = env.from_string(body).render(section={
    'settings': settings,
    'blocks': blocks,
    'id': 'test-section',
    'shopify_attributes': '',
}, request={'design_mode': False})

page = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
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
