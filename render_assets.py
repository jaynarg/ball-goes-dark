"""Render the ball to raster art: OG card, favicon, app icons.

Reuses the exact geometry from the page — Fibonacci seeds sorted north-to-south,
groups dealt in order, nearest-seed Voronoi partition, 6.2% shrink toward each
region's own center — so the icon is a picture of the real thing, not a mock-up.
"""
import json, math, pathlib, io, base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = pathlib.Path(__file__).parent
OUT = HERE
TEAMS = json.load(open(HERE / 'data' / 'teams.json', encoding='utf-8'))['teams']
FLAGS = json.load(open(HERE / 'data' / 'flags_b64.json', encoding='utf-8'))
SHRINK = 0.062
STAGE_COL = ['#232C35', '#3C5364', '#7BA0B5', '#F0B429', '#F9802B', '#E8483A', '#FFD84D']
VOID = (8, 12, 16)
GOLD = (240, 180, 41)
SITE = 'ball-goes-dark.vercel.app'

V = lambda *a: tuple(a)
def norm(v):
    m = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    return (v[0]/m, v[1]/m, v[2]/m)
def add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def dot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def lerp(a, b, t): return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)
def hexc(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))

# ---- seeds: identical to the page. Chamfered dodecahedron, Goldberg GP(2,0):
#      12 pentagons at the icosahedron's vertices (the group winners),
#      30 hexagons at its edge midpoints.
_PHI = (1 + math.sqrt(5)) / 2
ICO_V = [(-1,_PHI,0),(1,_PHI,0),(-1,-_PHI,0),(1,-_PHI,0),(0,-1,_PHI),(0,1,_PHI),
         (0,-1,-_PHI),(0,1,-_PHI),(_PHI,0,-1),(_PHI,0,1),(-_PHI,0,-1),(-_PHI,0,1)]
ICO_F = [(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
         (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]

pent_seeds = sorted((norm(v) for v in ICO_V), key=lambda v: -v[1])
_edges = set()
for a, b, c in ICO_F:
    for p, q in ((a,b),(b,c),(c,a)): _edges.add(tuple(sorted((p, q))))
hex_seeds = sorted((norm(add(ICO_V[p], ICO_V[q])) for p, q in _edges), key=lambda v: -v[1])
assert len(pent_seeds) == 12 and len(hex_seeds) == 30

GROUPS = 'ABCDEFGHIJKL'
key = lambda t: (GROUPS.index(t['group']), t['rank'])
pents = sorted([t for t in TEAMS if t['panel'] and t['winner']], key=key)
hexes = sorted([t for t in TEAMS if t['panel'] and not t['winner']], key=key)
for i, t in enumerate(pents): t['seed'] = pent_seeds[i]
for i, t in enumerate(hexes): t['seed'] = hex_seeds[i]
ordered = pents + hexes
N = len(ordered)
assert N == 42, N

# ---- icosphere ----
def icosphere(depth):
    t = (1 + math.sqrt(5)) / 2
    base = [(-1,t,0),(1,t,0),(-1,-t,0),(1,-t,0),(0,-1,t),(0,1,t),(0,-1,-t),(0,1,-t),
            (t,0,-1),(t,0,1),(-t,0,-1),(-t,0,1)]
    Vs = [norm(v) for v in base]
    idx = [(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
           (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
    F = [[Vs[a], Vs[b], Vs[c]] for a, b, c in idx]
    for _ in range(depth):
        nf = []
        for a, b, c in F:
            ab, bc, ca = norm(add(a,b)), norm(add(b,c)), norm(add(c,a))
            nf += [[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]
        F = nf
    return F

FACES = icosphere(4)                       # 5,120 tris is plenty for raster
buckets = [[] for _ in range(N)]
for f in FACES:
    c = norm(add(add(f[0], f[1]), f[2]))
    best = max(range(N), key=lambda i: dot(c, ordered[i]['seed']))
    buckets[best].append(f)

centroids = []
for i in range(N):
    acc = (0, 0, 0)
    for f in buckets[i]:
        for v in f: acc = add(acc, v)
    centroids.append(norm(acc))

# ---- rotation: show as many lit panels as possible ----
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
print(f'rotation yaw={math.degrees(YAW):.0f}° pitch={math.degrees(PITCH):.0f}° '
      f'lit facing camera: {sum(1 for i in lit if rotate(centroids[i],YAW,PITCH)[2] > .15)}/{len(lit)}')

LIGHT = norm((-0.45, 0.62, 0.78))

MONO_F = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'

def label_tile(code, h):
    """Flag over three-letter code, sized to h px tall. Mirrors the sprite the page
    builds on a 192px canvas: flag 112x84 at y=28, text baseline 28px below it."""
    k = h / 192.0
    W = int(150 * k)
    im = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fw, fh = int(112 * k), int(84 * k)
    fx, fy = (W - fw) // 2, int(28 * k)

    flag = Image.open(io.BytesIO(base64.b64decode(FLAGS[code]))).convert('RGB')
    flag = flag.resize((fw, fh), Image.LANCZOS)
    pad = max(1, int(2 * k))
    d.rectangle([fx - pad, fy - pad, fx + fw + pad, fy + fh + pad], fill=(10, 15, 20, 255))
    im.paste(flag, (fx, fy))
    d.rectangle([fx - pad, fy - pad, fx + fw + pad, fy + fh + pad],
                outline=(255, 255, 255, 78), width=max(1, int(2 * k)))

    f = ImageFont.truetype(MONO_F, max(6, int(40 * k)))
    ty = fy + fh + int(28 * k)
    for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):                    # cheap dark halo
        d.text((W/2 + dx, ty + dy), code, font=f, fill=(10, 15, 20, 235), anchor='mm')
    d.text((W/2, ty), code, font=f, fill=(244, 248, 250, 255), anchor='mm')
    return im


def render_ball(px, ss=4, labels=True):
    """Orthographic render, supersampled, transparent background."""
    S = px * ss
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    rad = S * 0.478

    # the dark inner sphere the seams show through
    d.ellipse([cx-rad*0.995, cy-rad*0.995, cx+rad*0.995, cy+rad*0.995], fill=(6, 9, 12, 255))

    tris = []
    for i in range(N):
        col = hexc(STAGE_COL[ordered[i]['stage']])
        c = centroids[i]
        for f in buckets[i]:
            shrunk = [norm(lerp(v, c, SHRINK)) for v in f]
            rc = rotate(norm(add(add(*shrunk[:2]), shrunk[2])), YAW, PITCH)
            if rc[2] <= 0.02: continue                  # back hemisphere
            tris.append((rc[2], shrunk, col, ordered[i]['lit'], rc))

    tris.sort(key=lambda t: t[0])                       # painter's algorithm
    for _, shrunk, col, is_lit, rc in tris:
        n = rc
        lam = max(0.0, dot(n, LIGHT))
        rim = max(0.0, 1 - n[2]) ** 3 * 0.35            # cool edge light
        sh = 0.30 + 0.78 * lam
        r = min(255, int(col[0]*sh + 90*rim))
        g = min(255, int(col[1]*sh + 120*rim))
        b = min(255, int(col[2]*sh + 150*rim))
        if is_lit:                                       # the emissive floor
            r = min(255, int(r*0.42 + 250*0.62))
            g = min(255, int(g*0.42 + 218*0.62))
            b = min(255, int(b*0.42 +  74*0.52))
        pts = []
        for v in shrunk:
            rv = rotate(v, YAW, PITCH)
            pts.append((cx + rv[0]*rad, cy - rv[1]*rad))
        d.polygon(pts, fill=(r, g, b, 255))

    # bloom off the lit panels
    glow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in lit:
        rv = rotate(centroids[i], YAW, PITCH)
        if rv[2] <= 0.12: continue
        gx, gy = cx + rv[0]*rad, cy - rv[1]*rad
        gr = rad * 0.17 * rv[2]
        gd.ellipse([gx-gr, gy-gr, gx+gr, gy+gr], fill=(255, 205, 90, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(S/26))
    img = Image.alpha_composite(img, glow)

    if labels:
        # Billboards: constant screen size, faded out as they rotate toward the limb.
        # Sprite scale is 0.235 world units and the sphere is radius 1, so the tile is
        # 0.235 * rad tall on screen. Same fade curve as the page: (f - .30) / .30.
        tiles = []
        for i in range(N):
            rv = rotate(centroids[i], YAW, PITCH)
            a = max(0.0, min(1.0, (rv[2] - 0.42) / 0.30))
            if a <= 0.05: continue
            tiles.append((rv[2], i, a, rv))
        tiles.sort(key=lambda t: t[0])                    # far labels first
        for _, i, a, rv in tiles:
            h = int(rad * 0.235)
            t = label_tile(ordered[i]['code'], h)
            if a < 1.0:
                alpha = t.getchannel('A').point(lambda v, a=a: int(v * a))
                t.putalpha(alpha)
            x = int(cx + rv[0]*rad*1.04 - t.width/2)
            y = int(cy - rv[1]*rad*1.04 - t.height/2)
            img.alpha_composite(t, (x, y))

    return img.resize((px, px), Image.LANCZOS)

def icosa():
    t = (1 + math.sqrt(5)) / 2
    base = [(-1,t,0),(1,t,0),(-1,-t,0),(1,-t,0),(0,-1,t),(0,1,t),(0,-1,-t),(0,1,-t),
            (t,0,-1),(t,0,1),(-t,0,-1),(-t,0,1)]
    Vs = [norm(v) for v in base]
    idx = [(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
           (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
    return Vs, idx


def render_football(px, ss=6, rim=True):
    """A truncated icosahedron — the Telstar ball everyone actually draws.

    Voronoi over the icosahedron's 12 vertices and 20 face centers yields exactly
    that solid: a pentagon around every vertex, a hexagon around every face. Twelve
    black pentagons, twenty white hexagons. One pentagon is gold.

    `rim` strokes the silhouette. Without it the white hexagons run straight to the
    edge and the ball vanishes on a white background.
    """
    S = px * ss
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    rad = S * 0.485

    Vs, idx = icosa()
    pent = [v for v in Vs]                                       # 12 pentagon centers
    hexa = [norm(add(add(Vs[a], Vs[b]), Vs[c])) for a, b, c in idx]   # 20 hexagon centers
    cells = pent + hexa
    is_pent = [True]*12 + [False]*20

    # Turn the ball so one pentagon looks straight at us; that one goes gold.
    # rotate() applies pitch about X, then yaw about Y. To send d to (0,0,1):
    #   pitch = atan2(dy, dz)      zeroes the y component
    #   yaw   = atan2(-dx, z')     zeroes the x component, z' = hypot(dy, dz)
    hero = max(range(12), key=lambda i: pent[i][1])
    dx, dy, dz = pent[hero]
    pitch2 = math.atan2(dy, dz)
    yaw = math.atan2(-dx, math.hypot(dy, dz))
    pitch2 += math.radians(7)          # a few degrees of tilt so it isn't dead-on

    buckets = [[] for _ in cells]
    for f in icosphere(4):
        c = norm(add(add(f[0], f[1]), f[2]))
        buckets[max(range(len(cells)), key=lambda i: dot(c, cells[i]))].append(f)

    d.ellipse([cx-rad*1.0, cy-rad*1.0, cx+rad*1.0, cy+rad*1.0], fill=(26, 26, 26, 255))  # seam color

    tris = []
    for i, cell in enumerate(cells):
        acc = (0, 0, 0)
        for f in buckets[i]:
            for v in f: acc = add(acc, v)
        c = norm(acc)
        col = (255, 216, 77) if i == hero else ((22, 22, 22) if is_pent[i] else (250, 250, 250))
        for f in buckets[i]:
            shrunk = [norm(lerp(v, c, 0.055)) for v in f]
            rc = rotate(norm(add(add(*shrunk[:2]), shrunk[2])), yaw, pitch2)
            if rc[2] <= 0.02: continue
            tris.append((rc[2], shrunk, col, rc))

    tris.sort(key=lambda t: t[0])
    for _, shrunk, col, n in tris:
        sh = 0.62 + 0.44 * max(0.0, dot(n, (-0.3, 0.45, 0.84)))
        c = tuple(min(255, int(v * sh)) for v in col)
        pts = [(cx + rotate(v, yaw, pitch2)[0]*rad, cy - rotate(v, yaw, pitch2)[1]*rad) for v in shrunk]
        d.polygon(pts, fill=c + (255,))

    if rim:
        w = max(2, int(S * 0.018))
        d.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], outline=(26, 26, 26, 255), width=w)
    return img.resize((px, px), Image.LANCZOS)


def render_mark(px, ss=6):
    """Favicon mark: the same ball, reduced to 12 facets so it survives 16px.
    One facet is gold — the last panel still lit."""
    S = px * ss
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    rad = S * 0.495
    d.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], fill=(11, 17, 22, 255))

    M = 12
    ms = []
    for i in range(M):
        y = 1 - (i / (M - 1)) * 2
        r = math.sqrt(max(0, 1 - y*y)); th = GA * i
        ms.append(norm((math.cos(th)*r, y, math.sin(th)*r)))
    # the gold facet is whichever one points most directly at the viewer
    hero = max(range(M), key=lambda i: ms[i][2] * 0.75 + ms[i][1] * 0.25)

    mb = [[] for _ in range(M)]
    for f in icosphere(4):
        c = norm(add(add(f[0], f[1]), f[2]))
        mb[max(range(M), key=lambda i: dot(c, ms[i]))].append(f)

    tris = []
    for i in range(M):
        c = norm(add(add(*[add(add(*f[:2]), f[2]) for f in mb[i]][:2]), (0,0,0))) if False else ms[i]
        acc = (0,0,0)
        for f in mb[i]:
            for v in f: acc = add(acc, v)
        c = norm(acc)
        col = (255, 216, 77) if i == hero else (44, 56, 68)
        for f in mb[i]:
            shrunk = [norm(lerp(v, c, 0.075)) for v in f]
            rc = norm(add(add(*shrunk[:2]), shrunk[2]))
            if rc[2] <= 0.02: continue
            tris.append((rc[2], shrunk, col, rc))
    tris.sort(key=lambda t: t[0])
    for _, shrunk, col, n in tris:
        sh = 0.42 + 0.72 * max(0.0, dot(n, (-0.35, 0.5, 0.79)))
        c = tuple(min(255, int(v * sh)) for v in col)
        pts = [(cx + v[0]*rad, cy - v[1]*rad) for v in shrunk]
        d.polygon(pts, fill=c + (255,))
    return img.resize((px, px), Image.LANCZOS)


DJV  = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'

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
for y in range(H):                                   # faint vertical lift
    v = int(6 * (1 - y / H))
    d.line([(0, y), (W, y)], fill=(VOID[0]+v, VOID[1]+v, VOID[2]+v))

BALL_PX = 560
ball = render_ball(BALL_PX, ss=4, labels=True)
og.paste(ball, (W - BALL_PX - 14, (H - BALL_PX)//2), ball)

f_eye  = ImageFont.truetype(MONO, 25)
f_disp = ImageFont.truetype(DJV, 78)
f_by   = ImageFont.truetype(MONO, 17)
f_dek  = ImageFont.truetype(DJV, 21)
f_url  = ImageFont.truetype(MONO, 20)

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

# ------------------------------------------------------------ icons
def icon(px, bleed=0.88, bg=(255, 255, 255)):
    """The clean football, not the 42-panel data ball — at icon sizes the panels are
    noise. White plate because iOS masks the corners and drops it onto whatever
    wallpaper you have, where a near-black ball on a near-black square disappears."""
    im = Image.new('RGBA', (px, px), bg + (255,))
    b = render_football(int(px * bleed))

    shadow = Image.new('RGBA', (px, px), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    r = b.width / 2
    sd.ellipse([px/2 - r, px/2 - r + px*0.030, px/2 + r, px/2 + r + px*0.030],
               fill=(96, 106, 116, 92))
    shadow = shadow.filter(ImageFilter.GaussianBlur(px * 0.026))
    im = Image.alpha_composite(im, shadow)

    o = (px - b.width) // 2
    im.paste(b, (o, o), b)
    return im.convert('RGB')

icon(180).save(OUT / 'apple-touch-icon.png', optimize=True)   # iOS home screen / Shortcuts
icon(192).save(OUT / 'icon-192.png', optimize=True)
icon(512).save(OUT / 'icon-512.png', optimize=True)

# favicon: a classic Telstar ball, transparent background so it reads on a light
# or dark browser tab. Drawn fresh at each size instead of downscaled from one.
render_football(256).save(OUT / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
render_football(32).save(OUT / 'favicon-32.png', optimize=True)
render_football(180).save(OUT / 'favicon.png', optimize=True)

for n in ['og.png','apple-touch-icon.png','icon-192.png','icon-512.png','favicon.ico','favicon-32.png','favicon.png']:
    p = OUT / n
    print(f'  {p.name:24} {p.stat().st_size:>7,} bytes')
