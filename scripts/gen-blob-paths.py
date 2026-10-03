"""Two closed organic blobs from per-direction radii.

Catmull-Rom through the ring points, converted to cubic bezier, so the curve
is smooth and closed with no hand-tuned handles. Authored on a 0..100 grid:
the outline SVG uses viewBox="0 0 100 100" and the clipPath scales the same
path by 0.01 into objectBoundingBox space, so there is one source of truth.
"""
import math

def ring(radii, cx=50.0, cy=50.0, rot=-90.0):
    n = len(radii)
    pts = []
    for i, r in enumerate(radii):
        a = math.radians(rot + 360.0 * i / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def catmull_path(pts, tension=1.0):
    n = len(pts)
    d = f"M {pts[0][0]:.2f} {pts[0][1]:.2f}"
    for i in range(n):
        p0 = pts[(i - 1) % n]; p1 = pts[i]
        p2 = pts[(i + 1) % n]; p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / (6.0 * tension),
              p1[1] + (p2[1] - p0[1]) / (6.0 * tension))
        c2 = (p2[0] - (p3[0] - p1[0]) / (6.0 * tension),
              p2[1] - (p3[1] - p1[1]) / (6.0 * tension))
        d += (f" C {c1[0]:.2f} {c1[1]:.2f}, {c2[0]:.2f} {c2[1]:.2f},"
              f" {p2[0]:.2f} {p2[1]:.2f}")
    return d + " Z"

# Eight directions, clockwise from top. Deliberately different profiles so the
# peach reads as an uneven halo rather than a uniform ring.
#            N    NE    E    SE    S    SW    W    NW
BACK  = [48.0, 44.0, 49.0, 46.0, 47.0, 50.0, 48.5, 43.0]
PHOTO = [47.0, 48.5, 44.0, 49.0, 45.0, 43.0, 47.5, 48.0]

back  = catmull_path(ring(BACK))
photo = catmull_path(ring(PHOTO))
print("BACK  =", back)
print()
print("PHOTO =", photo)
print()

# The photo blob is drawn at 420/480 of the back blob's box, inset 30px, so in
# the back blob's own 0..100 space the photo's radii are scaled by 420/480.
k = 420.0 / 480.0
gaps = [(b - p * k) * 480.0 / 100.0 for b, p in zip(BACK, PHOTO)]
names = ['N ', 'NE', 'E ', 'SE', 'S ', 'SW', 'W ', 'NW']
print("peach visible around the photo, in px at the 480px size:")
for nm, g in zip(names, gaps):
    print(f"  {nm}  {g:6.1f}px")
print(f"\n  thinnest {min(gaps):.1f}px   thickest {max(gaps):.1f}px"
      f"   ratio {max(gaps)/min(gaps):.2f}x")
