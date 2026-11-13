"""Simple 2-layer grid router for board2.kicad_pcb (run with KiCad's python after gen_pcb.py).
GND is NOT routed: it becomes a copper pour on F.Cu + B.Cu.  Everything else is A* routed on a 0.25 mm grid.
Usage: python route.py   (reads+rewrites board2.kicad_pcb)
"""
import pcbnew, os, heapq, math, sys
import numpy as np
from pcbnew import FromMM as mm, ToMM as tomm, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "board2.kicad_pcb")
G = 0.25                 # grid pitch (mm)
CLR = 0.5                # routing clearance (mm) incl. grid-snap margin
VIA_D, VIA_DRILL = 0.8, 0.4
EDGE = 0.8               # keep copper this far from board edge
WIDTH = {"GND": 0.8, "V12S": 0.8, "IGN": 0.8, "VJ2": 0.8, "VD": 0.8, "VF": 0.8}
DEFAULT_W = 0.3
GND = "GND"

b = pcbnew.LoadBoard(PCB)
bb = b.GetBoardEdgesBoundingBox()
X0, Y0 = tomm(bb.GetX()), tomm(bb.GetY())
NX = int(tomm(bb.GetWidth()) / G) + 1
NY = int(tomm(bb.GetHeight()) / G) + 1

def cell(x, y):
    return int(round((x - X0) / G)), int(round((y - Y0) / G))
def pos(ix, iy):
    return X0 + ix * G, Y0 + iy * G

# remove old tracks/zones from a previous run
for t in list(b.GetTracks()):
    b.Remove(t)
for z in list(b.Zones()):
    b.Remove(z)

netcodes = {}
for name, ni in b.GetNetInfo().NetsByName().items():
    if str(name):
        netcodes[str(name)] = ni.GetNetCode()
code2name = {v: k for k, v in netcodes.items()}
NID = {n: i + 1 for i, n in enumerate(sorted(netcodes))}   # 0 = free, -1 = foreign obstacle

own = [np.zeros((NX, NY), np.int16), np.zeros((NX, NY), np.int16)]   # per layer owner
xx, yy = np.meshgrid(np.arange(NX), np.arange(NY), indexing="ij")

def paint(layer_idx, x, y, r_mm, nid):
    ix, iy = cell(x, y)
    rc = r_mm / G
    r = int(math.ceil(rc)) + 1
    x0, x1 = max(0, ix - r), min(NX, ix + r + 1)
    y0, y1 = max(0, iy - r), min(NY, iy + r + 1)
    sub = (xx[x0:x1, y0:y1] - ix) ** 2 + (yy[x0:x1, y0:y1] - iy) ** 2 <= rc * rc
    own[layer_idx][x0:x1, y0:y1][sub] = nid

padzone = np.zeros((NX, NY), bool)
pads = {}   # net name -> list of (x,y)
for fp in b.GetFootprints():
    for p in fp.Pads():
        c = p.GetPosition()
        x, y = tomm(c.x), tomm(c.y)
        if not (X0 <= x <= X0 + tomm(bb.GetWidth()) and Y0 <= y <= Y0 + tomm(bb.GetHeight())):
            continue   # parked off the board: not routed
        sz = p.GetSize()
        r = max(tomm(sz.x), tomm(sz.y)) / 2 * (1.2 if p.GetShape() != pcbnew.PAD_SHAPE_CIRCLE else 1.0)
        dr = p.GetDrillSize(); r = max(r, max(tomm(dr.x), tomm(dr.y)) / 2)   # NPTH holes: keep clear of the drill
        n = p.GetNetname()
        nid = NID.get(n, -1) if n else -1
        for li in (0, 1):
            paint(li, x, y, r, nid)
        _ix, _iy = cell(x, y); _rc = (r + VIA_D / 2 + 0.15) / G; _r = int(_rc) + 1
        _sx = slice(max(0, _ix - _r), _ix + _r + 1); _sy = slice(max(0, _iy - _r), _iy + _r + 1)
        padzone[_sx, _sy] |= ((xx[_sx, _sy] - _ix) ** 2 + (yy[_sx, _sy] - _iy) ** 2) <= _rc * _rc
        padzone[max(0,_ix-_r):_ix+_r+1, max(0,_iy-_r):_iy+_r+1] |= ((xx[max(0,_ix-_r):_ix+_r+1, max(0,_iy-_r):_iy+_r+1]-_ix)**2 + (yy[max(0,_ix-_r):_ix+_r+1, max(0,_iy-_r):_iy+_r+1]-_iy)**2) <= _rc*_rc if False else padzone[max(0,_ix-_r):_ix+_r+1, max(0,_iy-_r):_iy+_r+1]
        if n:
            pads.setdefault(n, []).append((x, y))

# board-edge margin = foreign obstacle
edge = np.zeros((NX, NY), bool)
m = int(EDGE / G)
edge[:m, :] = edge[-m:, :] = True
edge[:, :m] = edge[:, -m:] = True

def dilate(mask, r):
    rc = r / G
    ri = int(math.ceil(rc))
    out = mask.copy()
    for dx in range(-ri, ri + 1):
        for dy in range(-ri, ri + 1):
            if dx * dx + dy * dy <= rc * rc and (dx or dy):
                sh = np.zeros_like(mask)
                xs0, xs1 = max(0, dx), NX + min(0, dx)
                ys0, ys1 = max(0, dy), NY + min(0, dy)
                sh[xs0:xs1, ys0:ys1] = mask[xs0 - dx:xs1 - dx, ys0 - dy:ys1 - dy]
                out |= sh
    return out

def route_net(name):
    w = WIDTH.get(name, DEFAULT_W)
    nid = NID[name]
    h = w / 2
    blk = []
    for li in (0, 1):
        other = (own[li] != 0) & (own[li] != nid)
        blk.append(dilate(other, h + CLR) | edge)
    viablk = [dilate((own[li] != 0) & (own[li] != nid), VIA_D / 2 + CLR) | edge for li in (0, 1)]
    viab = viablk[0] | viablk[1] | padzone
    pts = pads[name]
    if len(pts) < 2:
        return True, []
    tree = set()   # (layer, ix, iy)
    segs, vias = [], []
    start = cell(*pts[0])
    for li in (0, 1):
        tree.add((li, *start))
    remaining = pts[1:]
    ok = True
    while remaining:
        # nearest remaining pad to the tree
        tarr = np.array([(c[1], c[2]) for c in tree])
        best = None
        for p in remaining:
            c = np.array(cell(*p))
            d = np.abs(tarr - c).sum(1).min()
            if best is None or d < best[0]:
                best = (d, p)
        p = best[1]
        remaining.remove(p)
        sx, sy = cell(*p)
        c = np.array((sx, sy))
        tgt = tarr[np.abs(tarr - c).sum(1).argmin()]
        # A*
        openh = []
        dist = {}
        prev = {}
        for li in (0, 1):
            s = (li, sx, sy)
            dist[s] = 0
            heapq.heappush(openh, (abs(sx - tgt[0]) + abs(sy - tgt[1]), 0, s, None))
        found = None
        pop = 0
        while openh:
            f, gd, s, d = heapq.heappop(openh)
            if dist.get(s, 1e18) < gd:
                continue
            pop += 1
            if pop > 600000:
                break
            if s in tree and s != (s[0], sx, sy):
                found = s
                break
            li, ix, iy = s
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = ix + ddx, iy + ddy
                if not (0 <= nx < NX and 0 <= ny < NY):
                    continue
                if blk[li][nx, ny] and (li, nx, ny) not in tree:
                    continue
                cost = 1 + (0 if (li == 0) == (ddx != 0) else 0.4)   # prefer F horizontal / B vertical
                if d is not None and d != (ddx, ddy):
                    cost += 2
                ns = (li, nx, ny)
                nd = gd + cost
                if nd < dist.get(ns, 1e18):
                    dist[ns] = nd
                    prev[ns] = (s, d)
                    heapq.heappush(openh, (nd + abs(nx - tgt[0]) + abs(ny - tgt[1]), nd, ns, (ddx, ddy)))
            # via
            if not viab[ix, iy] or (0, ix, iy) in tree or True:
                if not viab[ix, iy]:
                    ns = (1 - li, ix, iy)
                    nd = gd + 12
                    if nd < dist.get(ns, 1e18):
                        dist[ns] = nd
                        prev[ns] = (s, "via")
                        heapq.heappush(openh, (nd + abs(ix - tgt[0]) + abs(iy - tgt[1]), nd, ns, None))
        if not found:
            print(f"  FAILED {name}: pad at {p}")
            ok = False
            continue
        # backtrack
        path = [found]
        while path[-1] in prev:
            s, d = prev[path[-1]]
            path.append(s)
            if s[1:] == (sx, sy) and (s not in prev):
                break
        path.reverse()
        for a, bnode in zip(path, path[1:]):
            if a[0] != bnode[0]:
                x, y = pos(a[1], a[2])
                vias.append((x, y))
                for li in (0, 1):
                    paint(li, x, y, VIA_D / 2, nid)
            else:
                x1, y1 = pos(a[1], a[2]); x2, y2 = pos(bnode[1], bnode[2])
                segs.append((a[0], x1, y1, x2, y2, w))
                paint(a[0], x1, y1, h, nid); paint(a[0], x2, y2, h, nid)
        for s in path:
            tree.add(s)
        # real pad centre -> snapped cell stub
        px, py = p
        qx, qy = pos(sx, sy)
        if abs(px - qx) > 1e-3 or abs(py - qy) > 1e-3:
            for li in (0, 1):
                segs.append((li, px, py, qx, qy, w)) if li == path[0][0] else None
    # stub from first pad
    return ok, (segs, vias, pts[0])

LAY = [pcbnew.F_Cu, pcbnew.B_Cu]

def add_track(li, x1, y1, x2, y2, w, code):
    if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
        return
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(VECTOR2I(mm(x1), mm(y1))); t.SetEnd(VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(w)); t.SetLayer(LAY[li]); t.SetNetCode(code); b.Add(t)

def add_via(x, y, code):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetNetCode(code); b.Add(v)

order = sorted([n for n in pads], key=lambda n: (0 if n == GND else 1 if n in WIDTH else 2, -len(pads[n])))
fails = 0
for n in order:
    print("routing", n, len(pads[n]), "pads")
    ok, res = route_net(n)
    if not ok:
        fails += 1
    if not res:
        continue
    segs, vias, first = res
    code = netcodes[n]
    for (li, x1, y1, x2, y2, w) in segs:
        add_track(li, x1, y1, x2, y2, w, code)
    for (x, y) in vias:
        add_via(x, y, code)
    # stub from first pad centre to its snapped cell on both layers
    sx, sy = cell(*first); qx, qy = pos(sx, sy)
    for li in (0, 1):
        add_track(li, first[0], first[1], qx, qy, WIDTH.get(n, DEFAULT_W), code)

# GND pour on both layers
W_, H_ = tomm(bb.GetWidth()), tomm(bb.GetHeight())
for li in (0, 1):
    z = pcbnew.ZONE(b)
    z.SetLayer(LAY[li]); z.SetNetCode(netcodes[GND])
    z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ol = z.Outline(); ol.NewOutline()
    for (x, y) in [(X0 + 0.5, Y0 + 0.5), (X0 + W_ - 0.5, Y0 + 0.5), (X0 + W_ - 0.5, Y0 + H_ - 0.5), (X0 + 0.5, Y0 + H_ - 0.5)]:
        ol.Append(mm(x), mm(y))
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(PCB)
print("done; failed nets:", fails)
