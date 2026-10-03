"""Check that no section can paint into another.

A section with positioned children and no stacking context of its own does not
keep its layers to itself: they are ordered against the whole page. A panel in
the hero is then in the same stack as a product grid five sections down, and
whichever the painting algorithm favours wins -- which is how a hero's
background came to show through the products on the home page.

Reproduced before it was fixed: with a hero and the grid overlapping, six of
nine points sampled inside the overlap were the hero's panel rather than the
grid. After, none were.

This is a source check: it reads the stylesheet rather than rendering, because
the fault only shows when two particular sections happen to overlap, and the
point is that no pair ever can.
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'sections'

problems = []
checked = 0
for path in sorted(ROOT.glob('*.liquid')):
    css = re.search(r'\{%\s*style\s*%\}(.*?)\{%\s*endstyle\s*%\}',
                    path.read_text(encoding='utf-8'), re.S)
    if not css:
        continue
    style = css.group(1)
    root_rule = None
    for sel, body in re.findall(r'(?m)^\s*(\.[A-Za-z0-9_-]+)\s*\{(.*?)^\s*\}', style, re.S):
        if '__' in sel or '--' in sel:
            continue
        root_rule = (sel, body)
        break
    if not root_rule:
        continue
    checked += 1
    sel, body = root_rule

    # Anything inside that is taken out of normal flow, or given a layer.
    layered = re.findall(r'z-index:\s*(-?\d+)', style)
    positioned = re.findall(r'position:\s*(absolute|fixed|sticky)', style)
    if not layered and not positioned:
        continue

    makes_context = bool(
        re.search(r'isolation:\s*isolate', body)
        or re.search(r'z-index:\s*-?\d+', body)
        or re.search(r'(filter|transform|contain|mix-blend-mode):', body))
    if not makes_context:
        problems.append(
            f"{path.name}: {sel} has positioned or layered children "
            f"(z-index {sorted(set(layered)) or 'none'}, "
            f"{len(positioned)} out-of-flow) but makes no stacking context, so "
            f"they are ordered against every other section on the page")

print()
for p in problems:
    print(p)
print(f"\n{checked} section root(s) checked, {len(problems)} problem(s)")
sys.exit(0 if not problems else 1)
