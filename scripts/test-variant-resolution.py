"""Run the section's own variant-resolution Liquid against mock products.

The {%- liquid ... -%} block is lifted verbatim out of the section file, so this
exercises the shipped code rather than a Python restatement of it.
"""
import re, pathlib
from liquid import Environment

src = pathlib.Path('/home/user/hankie-pals-shopify-store/sections/variant-grid.liquid').read_text()
block = re.search(r'(\{%-\s*liquid\s*\n\s*assign b = block\.settings.*?-%\})', src, re.S).group(1)

env = Environment()
env.add_filter("money", lambda cents: f"${cents / 100:,.2f}")

template = env.from_string(block + """
{{- variant.id | default: 'none' }}|{{ variant_name }}|{{ card_title }}|{{ card_url }}|{{ unresolved }}|{{ a11y_name }}""")


class V(dict):
    """Mock drop. Dunder lookups must raise so the engine's protocol checks
    (__liquid__, __html__) fall through instead of finding None."""
    def __getattr__(self, k):
        if k.startswith("__"):
            raise AttributeError(k)
        return self.get(k)


def variant(vid, title, option1, price=2400, available=True):
    return V(id=vid, title=title, option1=option1, price=price, available=available,
             compare_at_price=None, featured_image=None)


def product(title, variants, handle="hankie-pals"):
    return V(title=title, url=f"/products/{handle}", variants=variants,
             featured_image=None, images=[])


def run(prod, settings, index0=0):
    out = template.render(
        product=prod,
        block=V(settings=V(**settings)),
        forloop=V(index0=index0, index=index0 + 1),
    ).strip()
    vid, name, title, url, unresolved, a11y = out.split("|")
    return {"id": vid, "name": name, "title": title, "url": url,
            "unresolved": unresolved == "true", "a11y": a11y}


PALS = product("Hankie Pals", [
    variant(101, "Bunny", "Bunny"),
    variant(102, "Cow", "Cow"),
    variant(103, "Dog", "Dog", price=2650),
])
COMBO = product("Hankie Pals", [
    variant(201, "Bunny / Small", "Bunny"),
    variant(202, "Cow / Small", "Cow"),
])
SINGLE = product("Hankie Pals", [variant(301, "Default Title", "Default Title")])

cases = [
    ("exact name resolves",            PALS,  {"variant_title": "Cow"},      1, {"id": "102"}),
    ("wrong case resolves",            PALS,  {"variant_title": "bUnNy"},    0, {"id": "101"}),
    ("padded name resolves",           PALS,  {"variant_title": "  Dog  "},  2, {"id": "103"}),
    ("first option resolves a combo",  COMBO, {"variant_title": "Bunny"},    0, {"id": "201"}),
    ("full combined title resolves",   COMBO, {"variant_title": "cow / small"}, 1, {"id": "202"}),
    ("blank falls back to position 1", PALS,  {"variant_title": ""},         0, {"id": "101"}),
    ("blank falls back to position 3", PALS,  {"variant_title": ""},         2, {"id": "103"}),
    ("unknown name resolves nothing",  PALS,  {"variant_title": "Otter"},    0, {"id": "none", "unresolved": True}),
    ("beyond the variant count",       COMBO, {"variant_title": ""},         5, {"id": "none"}),
]

passed = failed = 0
for name, prod, settings, i, expect in cases:
    got = run(prod, settings, i)
    ok = all(str(got[k]) == str(v) for k, v in expect.items())
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   got {got}"))
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)

checks = [
    ("label reads Product — Variant",
     run(PALS, {"variant_title": "Cow"}, 1)["title"] == "Hankie Pals — Cow"),
    ("no variant name on a single-variant product",
     run(SINGLE, {"variant_title": ""}, 0)["name"] == ""),
    ("Default Title never reaches the label",
     "Default Title" not in run(SINGLE, {"variant_title": ""}, 0)["title"]),
    ("custom label text wins",
     run(PALS, {"variant_title": "Dog", "display_title": "Meet Dog"}, 2)["title"] == "Meet Dog"),
    ("url carries this card's variant",
     run(PALS, {"variant_title": "Dog"}, 2)["url"] == "/products/hankie-pals?variant=103"),
    ("each card gets a different url",
     len({run(PALS, {"variant_title": v}, i)["url"]
          for i, v in enumerate(["Bunny", "Cow", "Dog"])}) == 3),
    ("accessible name carries product, variant and a formatted price",
     run(PALS, {"variant_title": "Dog"}, 2)["a11y"] == "Hankie Pals — Dog, $26.50"),
    ("a sold out card says so in its accessible name",
     "sold out" in run(product("Hankie Pals", [variant(401, "Bunny", "Bunny", available=False)]),
                       {"variant_title": "Bunny"}, 0)["a11y"]),
    ("an unresolved card gets no url",
     run(PALS, {"variant_title": "Otter"}, 0)["url"] == ""),
    ("a card past the variant count gets no url",
     run(COMBO, {"variant_title": ""}, 5)["url"] == ""),
]
for name, ok in checks:
    print(("PASS  " if ok else "FAIL  ") + name)
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)

print(f"\n{passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
