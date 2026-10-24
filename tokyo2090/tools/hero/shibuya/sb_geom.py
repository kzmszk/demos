"""Pure-python / numpy geometry helpers (no bpy): sections, polygons, clipping."""
import math
import numpy as np


# ------------------------------------------------------------------ polygons
def area(poly):
    p = np.asarray(poly)
    x = p[:, 0]; y = p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xx = (xj - xi) * (y - yi) / (yj - yi + 1e-30) + xi
            if x < xx:
                inside = not inside
        j = i
    return inside


def points_in_poly(P, poly):
    """vectorised: P (n,2) -> bool (n,)"""
    P = np.asarray(P, dtype=float)
    q = np.asarray(poly, dtype=float)
    x = P[:, 0][:, None]; y = P[:, 1][:, None]
    xi = q[:, 0][None, :]; yi = q[:, 1][None, :]
    xj = np.roll(q[:, 0], 1)[None, :]; yj = np.roll(q[:, 1], 1)[None, :]
    cond = (yi > y) != (yj > y)
    xx = (xj - xi) * (y - yi) / np.where(np.abs(yj - yi) < 1e-30, 1e-30, (yj - yi)) + xi
    cross = cond & (x < xx)
    return (np.count_nonzero(cross, axis=1) % 2) == 1


def in_section(P, loops):
    """loops: list of (poly, is_hole). Even-odd over all loops."""
    P = np.asarray(P, dtype=float)
    c = np.zeros(len(P), dtype=int)
    for poly, _h in loops:
        c += points_in_poly(P, poly)
    return (c % 2) == 1


def simplify(poly, tol=0.2):
    """Douglas-Peucker on a closed ring; also drops near-duplicate points."""
    pts = [tuple(p) for p in poly]
    # dedupe
    out = []
    for p in pts:
        if not out or (abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1])) > 1e-3:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) + abs(out[0][1] - out[-1][1]) < 1e-3:
        out.pop()
    if len(out) < 4:
        return out
    # split ring at the farthest pair to run DP on two open chains
    P = np.array(out)
    i0 = 0
    d = np.hypot(P[:, 0] - P[0, 0], P[:, 1] - P[0, 1])
    i1 = int(np.argmax(d))

    def dp(chain):
        if len(chain) < 3:
            return chain
        a = np.array(chain[0]); b = np.array(chain[-1])
        ab = b - a
        L = np.hypot(*ab)
        C = np.array(chain[1:-1])
        if L < 1e-9:
            dist = np.hypot(C[:, 0] - a[0], C[:, 1] - a[1])
        else:
            dist = np.abs(ab[0] * (C[:, 1] - a[1]) - ab[1] * (C[:, 0] - a[0])) / L
        k = int(np.argmax(dist))
        if dist[k] > tol:
            left = dp(chain[:k + 2])
            right = dp(chain[k + 1:])
            return left[:-1] + right
        return [chain[0], chain[-1]]

    c1 = dp(out[i0:i1 + 1])
    c2 = dp(out[i1:] + [out[0]])
    ring = c1[:-1] + c2[:-1]
    return ring


def clip_halfplane(poly, nx, ny, c):
    """keep part with nx*x+ny*y <= c (Sutherland-Hodgman, one plane)."""
    out = []
    n = len(poly)
    if n == 0:
        return out
    for i in range(n):
        p = poly[i]; q = poly[(i + 1) % n]
        dp_ = nx * p[0] + ny * p[1] - c
        dq = nx * q[0] + ny * q[1] - c
        if dp_ <= 0:
            out.append(p)
        if (dp_ <= 0) != (dq <= 0):
            t = dp_ / (dp_ - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def clip_rect(poly, x0, x1, y0, y1):
    p = clip_halfplane(poly, 1, 0, x1)
    p = clip_halfplane(p, -1, 0, -x0)
    p = clip_halfplane(p, 0, 1, y1)
    p = clip_halfplane(p, 0, -1, -y0)
    return p


def seg_inside_intervals(a, b, loops):
    """parameter intervals [t0,t1] of segment a->b that lie inside the section."""
    ax, ay = a; bx, by = b
    ts = [0.0, 1.0]
    dx = bx - ax; dy = by - ay
    for poly, _h in loops:
        n = len(poly)
        for i in range(n):
            px, py = poly[i]; qx, qy = poly[(i + 1) % n]
            ex = qx - px; ey = qy - py
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            t = ((px - ax) * ey - (py - ay) * ex) / den
            s = ((px - ax) * dy - (py - ay) * dx) / den
            if 0 < t < 1 and 0 <= s <= 1:
                ts.append(t)
    ts = sorted(ts)
    res = []
    for t0, t1 in zip(ts[:-1], ts[1:]):
        if t1 - t0 < 1e-6:
            continue
        tm = 0.5 * (t0 + t1)
        if in_section([(ax + dx * tm, ay + dy * tm)], loops)[0]:
            if res and abs(res[-1][1] - t0) < 1e-9:
                res[-1] = (res[-1][0], t1)
            else:
                res.append((t0, t1))
    return res


# ------------------------------------------------------------------ mesh slicing
def slice_mesh(V, F, z, tol=0.25, min_area=3.0):
    """Cross-section of a triangle mesh at height z -> list of (ring, is_hole) with CCW outers."""
    T = V[F]  # (n,3,3)
    zs = T[:, :, 2]
    m = (zs.min(axis=1) < z) & (zs.max(axis=1) > z)
    T = T[m]
    segs = []
    for tri in T:
        pts = []
        for i in range(3):
            p = tri[i]; q = tri[(i + 1) % 3]
            if (p[2] < z) != (q[2] < z):
                t = (z - p[2]) / (q[2] - p[2])
                pts.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        if len(pts) == 2 and (abs(pts[0][0] - pts[1][0]) + abs(pts[0][1] - pts[1][1])) > 1e-6:
            segs.append(pts)
    if not segs:
        return []
    # chain segments by endpoint keys
    def key(p):
        return (round(p[0] * 50), round(p[1] * 50))
    adj = {}
    for i, (p, q) in enumerate(segs):
        adj.setdefault(key(p), []).append((i, 0))
        adj.setdefault(key(q), []).append((i, 1))
    used = [False] * len(segs)
    rings = []
    for i0 in range(len(segs)):
        if used[i0]:
            continue
        used[i0] = True
        ring = [segs[i0][0], segs[i0][1]]
        start = key(segs[i0][0])
        cur = key(segs[i0][1])
        ok = False
        for _ in range(len(segs) + 2):
            if cur == start:
                ok = True
                break
            nxt = None
            for (j, e) in adj.get(cur, []):
                if not used[j]:
                    nxt = (j, e)
                    break
            if nxt is None:
                break
            j, e = nxt
            used[j] = True
            other = segs[j][1 - e]
            ring.append(other)
            cur = key(other)
        if ok:
            ring = ring[:-1]
        if len(ring) >= 3:
            rings.append(ring)
    # simplify, drop slivers
    out = []
    for r in rings:
        r = simplify(r, tol)
        if len(r) >= 3 and abs(area(r)) >= min_area:
            out.append(r)
    # hole classification: nested depth parity
    res = []
    for i, r in enumerate(out):
        c = np.mean(np.array(r), axis=0)
        # a robust interior probe: centroid may lie outside for concave rings; use a vertex nudged inward
        depth = 0
        probe = _probe_point(r)
        for j, o in enumerate(out):
            if i != j and abs(area(o)) > abs(area(r)) and point_in_poly(probe, o):
                depth += 1
        hole = depth % 2 == 1
        a = area(r)
        if (a < 0) != hole:   # outers CCW (a>0), holes CW
            r = r[::-1]
        res.append((r, hole))
    return res


def _probe_point(r):
    P = np.array(r)
    a = area(r)
    sgn = 1 if a > 0 else -1
    # midpoint of the longest edge nudged toward the interior
    L = np.hypot(*(np.roll(P, -1, axis=0) - P).T)
    i = int(np.argmax(L))
    p = P[i]; q = P[(i + 1) % len(P)]
    m = 0.5 * (p + q)
    d = (q - p) / max(L[i], 1e-9)
    nrm = np.array([-d[1], d[0]]) * sgn   # left normal for CCW = interior
    return tuple(m + nrm * 0.05)


def dominant_angle(loops):
    """angle (rad) of the dominant edge direction modulo 90 deg, length-weighted."""
    acc = np.zeros(2)
    for poly, _h in loops:
        P = np.array(poly)
        E = np.roll(P, -1, axis=0) - P
        L = np.hypot(E[:, 0], E[:, 1])
        ang = np.arctan2(E[:, 1], E[:, 0]) * 4.0
        acc += np.array([np.sum(L * np.cos(ang)), np.sum(L * np.sin(ang))])
    return math.atan2(acc[1], acc[0]) / 4.0


def loops_area(loops):
    return sum(area(p) for p, _h in loops)
