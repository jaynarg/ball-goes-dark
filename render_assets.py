"""Render the ball to raster art: OG card, favicon, app icons.

Panels are exact spherical polygons, not unions of mesh triangles. The vertices of
a spherical Voronoi cell are the circumcenters of the Delaunay triangles around its
seed; join them in order and fan-triangulate. Approximating a cell as "every mesh
triangle nearest this seed" leaves a sawtooth on every edge whose amplitude happens
to equal the seam width — which is what made the old ball look like a blob.
"""
import json, math, pathlib, io, base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = pathlib.Path(__file__).parent
OUT = HERE
TEAMS = json.load(open(HERE / 'data' / 'teams.json', encoding='utf-8'))['teams']
FLAGS = json.load(open(HERE / 'data' / 'flags_b64.json', encoding='utf-8'))

SHRINK = 0.070
STAGE_COL = ['#232C35', '#3C5364', '#7BA0B5', '#F0B429', '#F9802B', '#E8483A', '#FFD84D']
VOID = (8, 12, 16)
GOLD = (240, 180, 41)
SITE = 'ball-goes-dark.vercel.app'

def norm(v):
    m = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    return (v[0]/m, v[1]/m, v[2]/m)
def add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def dot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def lerp(a, b, t): return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)
def hexc(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))

_PHI = (1 + math.sqrt(5)) / 2
ICO_V = [(-1,_PHI,0),(1,_PHI,0),(-1,-_PHI,0),(1,-_PHI,0),(0,-1,_PHI),(0,1,_PHI),
         (0,-1,-_PHI),(0,1,-_PHI),(_PHI,0,-1),(_PHI,0,1),(-_PHI,0,-1),(-_PHI,0,1)]
ICO_F = [(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
         (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]


# ---------------------------------------------------------------- exact cells
def circumcenter(A, B, C):
    """The point on the sphere equidistant from three seeds."""
    v = norm(cross(sub(B, A), sub(C, A)))
    return v if dot(v, A) > 0 else (-v[0], -v[1], -v[2])


def build_cells(seeds, tris):
    """Spherical Voronoi from a known Delaunay triangulation.
    Returns (center, ring) per seed, ring wound CCW as seen from outside."""
    dual = [circumcenter(seeds[a], seeds[b], seeds[c]) for a, b, c in tris]
    inc = [[] for _ in seeds]
    for i, (a, b, c) in enumerate(tris):
        inc[a].append(i); inc[b].append(i); inc[c].append(i)

    cells = []
    for i, c in enumerate(seeds):
        u = cross((0, 0, 1), c)
        if dot(u, u) < 1e-8: u = cross((1, 0, 0), c)
        u = norm(u); w = cross(c, u)
        ring = sorted((dual[t] for t in inc[i]),
                      key=lambda p: math.atan2(dot(p, w), dot(p, u)))
        cells.append((c, ring))
    return cells


def cell_tris(center, ring, shrink, depth=3):
    """Fan the polygon from its center, then subdivide onto the sphere so the panel
    bulges and its edges become true great-circle arcs."""
    r = [norm(lerp(p, center, shrink)) for p in ring]
    tris = [[center, r[i], r[(i+1) % len(r)]] for i in range(len(r))]
    if dot(cross(sub(tris[0][1], tris[0][0]), sub(tris[0][2], tris[0][0])), center) < 0:
        tris = [[a, c, b] for a, b, c in tris]
    for _ in range(depth):
        out = []
        for a, b, c in tris:
            ab, bc, ca = norm(add(a, b)), norm(add(b, c)), norm(add(c, a))
            out += [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]
        tris = out
    return tris


def chamfered_dodecahedron():
    """Goldberg GP(2,0): 12 pentagons at the icosahedron's vertices, 30 hexagons at
    its edge midpoints. Delaunay = the 80 faces of the once-subdivided icosahedron."""
    verts = [norm(v) for v in ICO_V]
    mid = {}
    def midpoint(a, b):
        k = (a, b) if a < b else (b, a)
        if k not in mid:
            verts.append(norm(add(verts[a], verts[b])))
            mid[k] = len(verts) - 1
        return mid[k]
    tris = []
    for a, b, c in ICO_F:
        ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
        tris += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
    assert len(verts) == 42 and len(tris) == 80
    return verts, tris


def truncated_icosahedron():
    """Goldberg GP(1,1), the Telstar: pentagons at the vertices, hexagons at the faces.
    A vertex's Voronoi neighbours are its 5 face centers — much nearer than the adjacent
    vertices — so the Delaunay triangles are (vertex, face, adjacent face)."""
    verts = [norm(v) for v in ICO_V]
    faces = [norm(add(add(verts[a], verts[b]), verts[c])) for a, b, c in ICO_F]
    seeds = verts + faces

    edge_faces = {}
    for fi, (a, b, c) in enumerate(ICO_F):
        for p, q in ((a, b), (b, c), (c, a)):
            edge_faces.setdefault((min(p, q), max(p, q)), []).append(fi)
    tris = []
    for (p, q), (f1, f2) in edge_faces.items():
        tris += [(p, 12 + f1, 12 + f2), (q, 12 + f1, 12 + f2)]
    assert len(seeds) == 32 and len(tris) == 60
    return seeds, tris


# ------------------------------------------------------- assign teams to cells
V42, T42 = chamfered_dodecahedron()
CELLS42 = build_cells(V42, T42)
pent_cells = sorted(CELLS42[:12], key=lambda c: -c[0][1])
hex_cells = sorted(CELLS42[12:], key=lambda c: -c[0][1])
assert all(len(r) == 5 for _, r in pent_cells), 'pentagons must have 5 sides'
assert all(len(r) == 6 for _, r in hex_cells), 'hexagons must have 6 sides'

GROUPS = 'ABCDEFGHIJKL'
key = lambda t: (GROUPS.index(t['group']), t['rank'])
pents = sorted([t for t in TEAMS if t['panel'] and t['winner']], key=key)
hexes = sorted([t for t in TEAMS if t['panel'] and not t['winner']], key=key)
for i, t in enumerate(pents): t['cell'] = pent_cells[i]
for i, t in enumerate(hexes): t['cell'] = hex_cells[i]
ordered = pents + hexes
N = len(ordered)
assert N == 42, N
centroids = [t['cell'][0] for t in ordered]


# ------------------------------------------------------------------- rotation
def rotate(v, yaw, pitch):
    x, y, z = v
    y, z = y*math.cos(pitch) - z*math.sin(pitch), y*math.sin(pitch) + z*math.cos(pitch)
    x, z = x*math.cos(yaw) + z*math.sin(yaw), -x*math.sin(yaw) + z*math.cos(yaw)
    return (x, y, z)

lit = [i for i in range(N) if ordered[i]['lit']]
best, bestscore = (0, 0), -99
for yi in range(72):
    for pi in range(-8, 9):
        yaw, pitch = yi*math.pi/36, pi*math.pi/24
        s = sum(max(0, rotate(centroids[i], yaw, pitch)[2])**1.6 for i in lit)
        s += 0.06 * sum(max(0, rotate(centroids[i], yaw, pitch)[2]) for i in range(N))
        if s > bestscore: bestscore, best = s, (yaw, pitch)
YAW, PITCH = best
print(f'rotation yaw={math.degrees(YAW):.0f}deg pitch={math.degrees(PITCH):.0f}deg '
      f'| lit facing camera: {sum(1 for i in lit if rotate(centroids[i],YAW,PITCH)[2] > .15)}/{len(lit)}')

LIGHT = norm((-0.45, 0.62, 0.78))
MONO_F = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
DJV = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def label_tile(code, h):
    """Flag over three-letter code, h px tall. Mirrors the page's 192px sprite."""
    k = h / 192.0
    W = int(150 * k)
    im = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fw, fh = int(112 * k), int(84 * k)
    fx, fy = (W - fw) // 2, int(28 * k)
    flag = Image.open(io.BytesIO(base64.b64decode(FLAGS[code]))).convert('RGB').resize((fw, fh), Image.LANCZOS)
    pad = max(1, int(2 * k))
    d.rectangle([fx-pad, fy-pad, fx+fw+pad, fy+fh+pad], fill=(10, 15, 20, 255))
    im.paste(flag, (fx, fy))
    d.rectangle([fx-pad, fy-pad, fx+fw+pad, fy+fh+pad], outline=(255, 255, 255, 78), width=max(1, int(2*k)))
    f = ImageFont.truetype(MONO_F, max(6, int(40 * k)))
    ty = fy + fh + int(28 * k)
    for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
        d.text((W/2+dx, ty+dy), code, font=f, fill=(10, 15, 20, 235), anchor='mm')
    d.text((W/2, ty), code, font=f, fill=(244, 248, 250, 255), anchor='mm')
    return im


def render_ball(px, ss=4, labels=True):
    S = px * ss
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    rad = S * 0.478
    d.ellipse([cx-rad*0.995, cy-rad*0.995, cx+rad*0.995, cy+rad*0.995], fill=(6, 9, 12, 255))

    tris = []
    for i in range(N):
        col = hexc(STAGE_COL[ordered[i]['stage']])
        center, ring = ordered[i]['cell']
        for f in cell_tris(center, ring, SHRINK):
            rc = rotate(norm(add(add(f[0], f[1]), f[2])), YAW, PITCH)
            if rc[2] <= 0.02: continue
            tris.append((rc[2], f, col, ordered[i]['lit'], rc))

    tris.sort(key=lambda t: t[0])
    for _, f, col, is_lit, n in tris:
        lam = max(0.0, dot(n, LIGHT))
        rim = max(0.0, 1 - n[2]) ** 3 * 0.35
        sh = 0.30 + 0.78 * lam
        r = min(255, int(col[0]*sh + 90*rim))
        g = min(255, int(col[1]*sh + 120*rim))
        b = min(255, int(col[2]*sh + 150*rim))
        if is_lit:
            r = min(255, int(r*0.42 + 250*0.62))
            g = min(255, int(g*0.42 + 218*0.62))
            b = min(255, int(b*0.42 + 74*0.52))
        pts = [(cx + rotate(v, YAW, PITCH)[0]*rad, cy - rotate(v, YAW, PITCH)[1]*rad) for v in f]
        d.polygon(pts, fill=(r, g, b, 255))

    glow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in lit:
        rv = rotate(centroids[i], YAW, PITCH)
        if rv[2] <= 0.12: continue
        gx, gy = cx + rv[0]*rad, cy - rv[1]*rad
        gr = rad * 0.17 * rv[2]
        gd.ellipse([gx-gr, gy-gr, gx+gr, gy+gr], fill=(255, 205, 90, 90))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(S/26)))

    if labels:
        tiles = []
        for i in range(N):
            rv = rotate(centroids[i], YAW, PITCH)
            a = max(0.0, min(1.0, (rv[2] - 0.42) / 0.30))
            if a <= 0.05: continue
            tiles.append((rv[2], i, a, rv))
        tiles.sort(key=lambda t: t[0])
        for _, i, a, rv in tiles:
            t = label_tile(ordered[i]['code'], int(rad * 0.235))
            if a < 1.0:
                t.putalpha(t.getchannel('A').point(lambda v, a=a: int(v * a)))
            img.alpha_composite(t, (int(cx + rv[0]*rad*1.04 - t.width/2),
                                    int(cy - rv[1]*rad*1.04 - t.height/2)))
    return img.resize((px, px), Image.LANCZOS)


def render_football(px, ss=6, rim=True):
    """The Telstar: 12 black pentagons, 20 white hexagons, one pentagon gold."""
    seeds, tris_idx = truncated_icosahedron()
    cells = build_cells(seeds, tris_idx)
    assert all(len(r) == 5 for _, r in cells[:12])
    assert all(len(r) == 6 for _, r in cells[12:])

    hero = max(range(12), key=lambda i: cells[i][0][1])
    dx, dy, dz = cells[hero][0]
    pitch = math.atan2(dy, dz) + math.radians(7)
    yaw = math.atan2(-dx, math.hypot(dy, dz))

    S = px * ss
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    rad = S * 0.485
    d.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], fill=(26, 26, 26, 255))

    tris = []
    for i, (center, ring) in enumerate(cells):
        col = (255, 216, 77) if i == hero else ((22, 22, 22) if i < 12 else (250, 250, 250))
        for f in cell_tris(center, ring, 0.055):
            rc = rotate(norm(add(add(f[0], f[1]), f[2])), yaw, pitch)
            if rc[2] <= 0.02: continue
            tris.append((rc[2], f, col, rc))

    tris.sort(key=lambda t: t[0])
    for _, f, col, n in tris:
        sh = 0.62 + 0.44 * max(0.0, dot(n, (-0.3, 0.45, 0.84)))
        c = tuple(min(255, int(v * sh)) for v in col)
        pts = [(cx + rotate(v, yaw, pitch)[0]*rad, cy - rotate(v, yaw, pitch)[1]*rad) for v in f]
        d.polygon(pts, fill=c + (255,))

    if rim:   # without this the white hexagons run to the edge and vanish on white
        d.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], outline=(26, 26, 26, 255),
                  width=max(2, int(S * 0.018)))
    return img.resize((px, px), Image.LANCZOS)


def track(d, xy, text, font, fill, sp=0):
    """DejaVu has no letter-spacing, so draw it a glyph at a time."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + sp
    return x


# ------------------------------------------------------------------ OG card
W, H = 1200, 630
og = Image.new('RGB', (W, H), VOID)
d = ImageDraw.Draw(og)
for y in range(H):
    v = int(6 * (1 - y / H))
    d.line([(0, y), (W, y)], fill=(VOID[0]+v, VOID[1]+v, VOID[2]+v))

BALL_PX = 560
ball = render_ball(BALL_PX)
og.paste(ball, (W - BALL_PX - 14, (H - BALL_PX)//2), ball)

f_eye  = ImageFont.truetype(MONO_F, 25)
f_disp = ImageFont.truetype(DJV, 78)
f_by   = ImageFont.truetype(MONO_F, 17)
f_dek  = ImageFont.truetype(DJV, 21)
f_url  = ImageFont.truetype(MONO_F, 20)

x0 = 140
track(d, (x0, 128), 'FIFA WORLD CUP 26', f_eye, (139, 156, 169), sp=5.5)
d.text((x0, 186), 'THE BALL', font=f_disp, fill=(230, 237, 242))
d.text((x0, 264), 'GOES ', font=f_disp, fill=(230, 237, 242))
d.text((x0 + d.textlength('GOES ', font=f_disp), 264), 'DARK', font=f_disp, fill=GOLD)
track(d, (x0, 372), 'CREATED BY JAY NARGUNDKAR', f_by, (123, 140, 153), sp=2.4)
d.text((x0, 416), 'A panel dims when a country goes home.', font=f_dek, fill=(123, 140, 153))
d.text((x0, 448), 'Who will be the last one still lit?', font=f_dek, fill=(230, 237, 242))
track(d, (x0, 520), SITE, f_url, GOLD, sp=1.6)
og.save(OUT / 'og.png', optimize=True)


# ------------------------------------------------------------------ icons
def icon(px, bleed=0.88, bg=(255, 255, 255)):
    """The clean football, not the 42-panel data ball. White plate because iOS masks
    the corners onto whatever wallpaper you have."""
    im = Image.new('RGBA', (px, px), bg + (255,))
    b = render_football(int(px * bleed))
    shadow = Image.new('RGBA', (px, px), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    r = b.width / 2
    sd.ellipse([px/2-r, px/2-r+px*0.030, px/2+r, px/2+r+px*0.030], fill=(96, 106, 116, 92))
    shadow = shadow.filter(ImageFilter.GaussianBlur(px * 0.026))
    im = Image.alpha_composite(im, shadow)
    o = (px - b.width) // 2
    im.paste(b, (o, o), b)
    return im.convert('RGB')

icon(180).save(OUT / 'apple-touch-icon.png', optimize=True)
icon(192).save(OUT / 'icon-192.png', optimize=True)
icon(512).save(OUT / 'icon-512.png', optimize=True)

render_football(256).save(OUT / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
render_football(32).save(OUT / 'favicon-32.png', optimize=True)
render_football(180).save(OUT / 'favicon.png', optimize=True)

for n in ['og.png','apple-touch-icon.png','icon-192.png','icon-512.png',
          'favicon.ico','favicon-32.png','favicon.png']:
    print(f'  {n:24} {(OUT / n).stat().st_size:>7,} bytes')
