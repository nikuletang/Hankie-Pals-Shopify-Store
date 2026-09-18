"""Screenshot each divider shape and read the pixels back.

A divider that paints nothing still renders a perfectly plausible coloured
band, so nothing short of looking at the pixels proves the shape is there.
"""
import json, subprocess, sys, pathlib, collections
from PIL import Image

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/section-divider.liquid'
HERE = pathlib.Path(__file__).resolve().parent
TOP, BOTTOM = (255, 0, 0), (0, 0, 255)   # loud test colours, easy to count


def shot(overrides, name, width=1200):
    page = HERE / f'div-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps({'settings': overrides}), str(page)],
                   check=True, capture_output=True)
    png = HERE / f'div-{name}.png'
    subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                    f'--window-size={width},260', '--virtual-time-budget=3000',
                    f'--screenshot={png}', 'file://' + str(page)], capture_output=True)
    return Image.open(png).convert('RGB')


def classify(px):
    # Anti-aliased edges sit between the two, so each pixel goes to whichever
    # it is nearer rather than being counted as a third colour.
    dt = sum((a - b) ** 2 for a, b in zip(px, TOP))
    db = sum((a - b) ** 2 for a, b in zip(px, BOTTOM))
    return 'top' if dt < db else 'bottom'


def runs(img, y):
    w = img.width
    out = []
    for x in range(w):
        c = classify(img.getpixel((x, y)))
        if not out or out[-1][0] != c:
            out.append([c, 1])
        else:
            out[-1][1] += 1
    return out


BASE = {'top_color': '#FF0000', 'bottom_color': '#0000FF', 'height': 80,
        'repeat_mode': 'stretch', 'repeats': 5}

results = []


def check(label, ok, detail):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


if __name__ == '__main__':
    # Every shape: the band must be the lower colour at its bottom edge and
    # show some of the upper colour at its top, or no shape was drawn.
    for shape in ['torn', 'zigzag', 'spikes', 'wave', 'scallop', 'slant', 'arch']:
        img = shot(dict(BASE, shape=shape), shape)
        band = [ [classify(img.getpixel((x, y))) for x in range(0, img.width, 4)]
                 for y in range(0, 80) ]
        top_row = collections.Counter(band[1])
        bottom_row = collections.Counter(band[78])
        mid = collections.Counter(band[40])
        both_at_mid = mid['top'] > 0 and mid['bottom'] > 0
        check(f'{shape}: shape is painted, band ends in the lower colour',
              top_row['top'] > 0 and bottom_row['bottom'] > 0
              and (both_at_mid or shape in ('slant',)),
              f"top row {dict(top_row)}  middle {dict(mid)}  bottom row {dict(bottom_row)}")

    # Peak count: 5 repeats of the zigzag should give 5 runs of the top colour.
    img = shot(dict(BASE, shape='zigzag', repeats=5), 'count5')
    r = [seg for seg in runs(img, 20) if seg[0] == 'top']
    check('stretch mode: 5 peaks asked for, 5 drawn', len(r) == 5,
          f'{len(r)} runs of the upper colour across 1200px')

    img = shot(dict(BASE, shape='zigzag', repeats=9), 'count9')
    r = [seg for seg in runs(img, 20) if seg[0] == 'top']
    check('stretch mode: 9 peaks asked for, 9 drawn', len(r) == 9,
          f'{len(r)} runs')

    # Same setting, different viewport: the count must not move.
    img = shot(dict(BASE, shape='zigzag', repeats=5), 'count5w', width=600)
    r = [seg for seg in runs(img, 20) if seg[0] == 'top']
    check('stretch mode: still 5 peaks at half the viewport width', len(r) == 5,
          f'{len(r)} runs across 600px')

    # Fixed mode: a 300px tile across 1200px is 4 peaks; across 600px, 2.
    img = shot(dict(BASE, shape='zigzag', repeat_mode='fixed', tile_width=300), 'fix1200')
    a = len([seg for seg in runs(img, 20) if seg[0] == 'top'])
    img = shot(dict(BASE, shape='zigzag', repeat_mode='fixed', tile_width=300), 'fix600', width=600)
    b = len([seg for seg in runs(img, 20) if seg[0] == 'top'])
    check('fixed mode: peak width holds, count follows the width', a == 4 and b == 2,
          f'1200px -> {a} peaks, 600px -> {b} peaks')

    # Pointing up: the colours swap over, so the band's top edge is the lower
    # colour and the shape rises into it.
    img = shot(dict(BASE, shape='torn', direction='up'), 'up')
    top_row = collections.Counter(classify(img.getpixel((x, 1))) for x in range(0, img.width, 4))
    bot_row = collections.Counter(classify(img.getpixel((x, 78))) for x in range(0, img.width, 4))
    check('pointing up: band is the upper colour, shape rises into it',
          top_row['top'] > 0 and bot_row['bottom'] > 0 and bot_row['bottom'] > bot_row['top'],
          f'top row {dict(top_row)}  bottom row {dict(bot_row)}')

    # Height: the painted band has to be exactly what was asked for.
    for h in (40, 160):
        img = shot(dict(BASE, shape='zigzag', height=h), f'h{h}')
        rows = [y for y in range(img.height)
                if any(classify(img.getpixel((x, y))) == 'top' for x in range(0, img.width, 8))
                or any(classify(img.getpixel((x, y))) == 'bottom' for x in range(0, img.width, 8))]
        # The page below the band is white, which classifies as neither; find
        # where the coloured band stops instead.
        band_h = 0
        for y in range(img.height):
            px = img.getpixel((img.width // 2, y))
            if px == (255, 255, 255):
                break
            band_h += 1
        check(f'height {h}px: band measures {band_h}px', abs(band_h - h) <= 1,
              f'asked {h}, measured {band_h}')

    # A seam shows as a sudden full-height break; the tile's ends must match.
    img = shot(dict(BASE, shape='torn', repeats=4), 'seam')
    heights = []
    for x in range(0, img.width, 3):
        col = 0
        for y in range(80):
            if classify(img.getpixel((x, y))) == 'top':
                col += 1
        heights.append(col)
    jumps = [abs(heights[i] - heights[i - 1]) for i in range(1, len(heights))]
    check('torn tile is seamless: no sudden full-height break',
          max(jumps) < 30, f'largest step between adjacent columns: {max(jumps)}px')

    print()
    print(f'{sum(results)} passed, {len(results) - sum(results)} failed')
