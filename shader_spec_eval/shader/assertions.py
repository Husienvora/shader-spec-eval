"""Property assertions on a rendered frame.

This is the actual contribution. A reference-image diff measures "did you write
the same shader I wrote" — but many correct shaders reach the same look through
different maths, and a one-pixel offset tanks an MSE score while looking perfect.

So instead we assert properties derived from the *specification*:

    "the centre is red"
    "the image has 4-fold symmetry"
    "brightness increases left to right"
    "the frame changes when time advances"

Every assertion is objective, implementation-agnostic, and cannot be satisfied by
a shader that merely looks plausible. A task lists the properties its spec
implies, and the shader either has them or it does not.
"""

from __future__ import annotations

from dataclasses import dataclass

from .render import Frame, RenderResult


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


# --------------------------------------------------------------------------
# Sanity — cheap gates that catch the common failure modes
# --------------------------------------------------------------------------

def not_blank(frame: Frame, min_unique: int = 2) -> Check:
    """A UNIFORM frame means the shader did nothing.

    Default is 2, not 8: a correct checkerboard or hard-edged SDF has exactly
    two colours. Requiring 8 would fail correct answers — it did, in self-test.
    """
    step = max(1, frame.size // 64)
    seen = {
        frame.rgb(x, y)
        for y in range(0, frame.size, step)
        for x in range(0, frame.size, step)
    }
    return Check("not_blank", len(seen) >= min_unique,
                 f"{len(seen)} distinct sampled colours (need >= {min_unique})")


def no_nan_artifacts(frame: Frame, max_black_ratio: float = 0.98) -> Check:
    """NaN in a shader usually renders as a black or fully saturated field."""
    step = max(1, frame.size // 64)
    pts = [(x, y) for y in range(0, frame.size, step) for x in range(0, frame.size, step)]
    black = sum(1 for x, y in pts if sum(frame.rgb(x, y)) < 8)
    ratio = black / len(pts)
    return Check("no_nan_artifacts", ratio <= max_black_ratio,
                 f"{ratio:.0%} of samples are near-black")


# --------------------------------------------------------------------------
# Colour and position
# --------------------------------------------------------------------------

def pixel_near(frame: Frame, x: float, y: float, rgb: tuple[int, int, int],
               tol: int = 40) -> Check:
    """Colour at a normalised coordinate (0..1), y from the top."""
    px, py = int(x * (frame.size - 1)), int(y * (frame.size - 1))
    got = frame.rgb(px, py)
    dist = max(abs(a - b) for a, b in zip(got, rgb))
    return Check(f"pixel_near({x:.2f},{y:.2f})", dist <= tol,
                 f"got rgb{got}, want rgb{rgb} +/-{tol} (off by {dist})")


def dominant_channel(frame: Frame, channel: str, margin: int = 12) -> Check:
    """Averaged over the frame, one channel should lead."""
    idx = {"r": 0, "g": 1, "b": 2}[channel]
    step = max(1, frame.size // 48)
    pts = [(x, y) for y in range(0, frame.size, step) for x in range(0, frame.size, step)]
    means = [sum(frame.rgb(x, y)[c] for x, y in pts) / len(pts) for c in range(3)]
    others = [m for c, m in enumerate(means) if c != idx]
    ok = all(means[idx] > o + margin for o in others)
    return Check(f"dominant_channel({channel})", ok,
                 f"means r={means[0]:.0f} g={means[1]:.0f} b={means[2]:.0f}")


def dominant_channels(frame: Frame, channels: list[str], margin: int = 12) -> Check:
    """Require a colour pair (for example green+blue = cyan) over the rest.

    Requiring one channel to dominate is incorrect for secondary colours: pure
    cyan intentionally has equal green and blue components.
    """
    indices = {"r": 0, "g": 1, "b": 2}
    wanted = {indices[c] for c in channels}
    step = max(1, frame.size // 48)
    pts = [(x, y) for y in range(0, frame.size, step) for x in range(0, frame.size, step)]
    means = [sum(frame.rgb(x, y)[c] for x, y in pts) / len(pts) for c in range(3)]
    selected = [means[i] for i in wanted]
    others = [means[i] for i in range(3) if i not in wanted]
    ok = bool(selected and others) and min(selected) > max(others) + margin
    label = "".join(channels)
    return Check(f"dominant_channels({label})", ok,
                 f"means r={means[0]:.0f} g={means[1]:.0f} b={means[2]:.0f}")


# --------------------------------------------------------------------------
# Structure — the assertions a lookalike shader cannot fake
# --------------------------------------------------------------------------

def gradient_along(frame: Frame, axis: str = "x", direction: str = "increasing",
                   min_delta: float = 25.0) -> Check:
    """Mean brightness should trend across the frame."""
    n, step = frame.size, max(1, frame.size // 32)
    bands = []
    for i in range(0, n, step):
        if axis == "x":
            vals = [frame.luma(i, y) for y in range(0, n, step)]
        else:
            vals = [frame.luma(x, i) for x in range(0, n, step)]
        bands.append(sum(vals) / len(vals))
    delta = bands[-1] - bands[0]
    ok = delta >= min_delta if direction == "increasing" else delta <= -min_delta
    return Check(f"gradient_{axis}_{direction}", ok,
                 f"first band {bands[0]:.0f}, last band {bands[-1]:.0f}, delta {delta:+.0f}")


def symmetric(frame: Frame, kind: str = "horizontal", tol: float = 14.0) -> Check:
    """Mirror or 4-fold symmetry, compared as mean absolute luma difference."""
    n, step = frame.size, max(1, frame.size // 48)
    diffs = []
    for y in range(0, n, step):
        for x in range(0, n, step):
            a = frame.luma(x, y)
            if kind == "horizontal":
                b = frame.luma(n - 1 - x, y)
            elif kind == "vertical":
                b = frame.luma(x, n - 1 - y)
            else:  # radial / 4-fold
                b = (frame.luma(n - 1 - x, y) + frame.luma(x, n - 1 - y)) / 2
            diffs.append(abs(a - b))
    mad = sum(diffs) / len(diffs)
    return Check(f"symmetric({kind})", mad <= tol, f"mean abs diff {mad:.1f} (tol {tol})")


def asymmetric(frame: Frame, kind: str = "horizontal", min_delta: float = 20.0) -> Check:
    """Require that a requested mirror symmetry is absent."""
    n, step = frame.size, max(1, frame.size // 48)
    diffs = []
    for y in range(0, n, step):
        for x in range(0, n, step):
            a = frame.luma(x, y)
            if kind == "horizontal":
                b = frame.luma(n - 1 - x, y)
            else:
                b = frame.luma(x, n - 1 - y)
            diffs.append(abs(a - b))
    mad = sum(diffs) / len(diffs)
    return Check(f"asymmetric({kind})", mad >= min_delta,
                 f"mean abs diff {mad:.1f} (need >= {min_delta})")


def radial_falloff(frame: Frame, min_delta: float = 20.0) -> Check:
    """Centre should differ from the corners — catches 'drew a flat disc'."""
    n = frame.size
    c = frame.luma(n // 2, n // 2)
    m = n // 8
    edge = [frame.luma(m, m), frame.luma(n - 1 - m, m),
            frame.luma(m, n - 1 - m), frame.luma(n - 1 - m, n - 1 - m)]
    mean_edge = sum(edge) / 4
    delta = c - mean_edge
    return Check("radial_falloff", delta >= min_delta,
                 f"centre {c:.0f}, mean corner {mean_edge:.0f}, delta {delta:+.0f}")


# --------------------------------------------------------------------------
# Time — proves the shader is animated rather than merely accepting a uniform
# --------------------------------------------------------------------------

def animates(result: RenderResult, min_delta: float = 4.0) -> Check:
    """Frames at different times must actually differ.

    Compares every pair of frames and keeps the largest difference, rather than
    only first-vs-last. A correct animation can be near its starting phase at
    the final sample; scoring that as "static" would be our bug, not the
    shader's.
    """
    if len(result.frames) < 2:
        return Check("animates", False, "need >= 2 frames")

    best, pair = 0.0, ("", "")
    for i in range(len(result.frames)):
        for j in range(i + 1, len(result.frames)):
            a, b = result.frames[i], result.frames[j]
            step = max(1, a.size // 48)
            pts = [(x, y) for y in range(0, a.size, step) for x in range(0, a.size, step)]
            mad = sum(abs(a.luma(x, y) - b.luma(x, y)) for x, y in pts) / len(pts)
            if mad > best:
                best, pair = mad, (f"{a.time:g}", f"{b.time:g}")
    return Check("animates", best >= min_delta,
                 f"largest diff {best:.1f} between t={pair[0]} and t={pair[1]} "
                 f"(need >= {min_delta})")


def stable_over_time(result: RenderResult, max_delta: float = 3.0) -> Check:
    """The inverse — for shaders that must NOT depend on time."""
    if len(result.frames) < 2:
        return Check("stable_over_time", True, "single frame")
    worst, pair = 0.0, ("", "")
    for i in range(len(result.frames)):
        for j in range(i + 1, len(result.frames)):
            a, b = result.frames[i], result.frames[j]
            step = max(1, a.size // 48)
            pts = [(x, y) for y in range(0, a.size, step)
                   for x in range(0, a.size, step)]
            mad = sum(abs(a.luma(x, y) - b.luma(x, y)) for x, y in pts) / len(pts)
            if mad > worst:
                worst, pair = mad, (f"{a.time:g}", f"{b.time:g}")
    return Check("stable_over_time", worst <= max_delta,
                 f"largest diff {worst:.1f} between t={pair[0]} and t={pair[1]}")


# --------------------------------------------------------------------------
# Spatial reasoning — the assertions that separate "knows GLSL syntax" from
# "can reason about space". These are the interesting ones.
# --------------------------------------------------------------------------

def tiles(frame: Frame, count: int, axis: str = "x", tol: float = 18.0,
          period_cells: int = 1) -> Check:
    """The image repeats `count` times along an axis.

    Requires modulo/fract reasoning in UV space. A model that understands
    `fract(uv * n)` passes; one pattern-matching on shader idioms does not.
    """
    n = frame.size
    # A checkerboard is ANTI-periodic at one cell: shifting by a single cell
    # inverts it. Its true spatial period is two cells. Pass period_cells=2.
    period = (n / count) * period_cells
    step = max(1, n // 64)
    diffs = []
    for y in range(0, n, step):
        for x in range(0, n, step):
            if axis == "x":
                x2 = int((x + period) % n)
                a, b = frame.luma(x, y), frame.luma(x2, y)
            else:
                y2 = int((y + period) % n)
                a, b = frame.luma(x, y), frame.luma(x, y2)
            diffs.append(abs(a - b))
    mad = sum(diffs) / len(diffs)
    return Check(f"tiles({count},{axis})", mad <= tol,
                 f"mean abs diff at period {period:.0f}px is {mad:.1f} (tol {tol})")


def rotational_symmetry(frame: Frame, fold: int, tol: float = 12.0,
                        exact: bool = False,
                        min_half_step_diff: float = 5.0) -> Check:
    """N-fold rotational symmetry about the centre.

    Compares the ANGULAR residual, not raw luma. A radial gradient is identical
    under any rotation, so raw comparison lets a 5-fold pattern pass a 6-fold
    check — it did, in self-test. Subtracting the mean brightness at each radius
    isolates the angular structure, which is the thing actually being asserted.
    """
    import math
    n = frame.size
    c = (n - 1) / 2.0
    step = max(1, n // 64)
    limit = (c * 0.85) ** 2

    pts = []
    for y in range(0, n, step):
        for x in range(0, n, step):
            dx, dy = x - c, y - c
            d2 = dx * dx + dy * dy
            if d2 <= limit:
                pts.append((x, y, math.sqrt(d2)))
    if not pts:
        return Check(f"rotational_symmetry({fold})", False, "no samples in range")

    # Mean luma per radius bin -> the purely radial component.
    nbins = 24
    maxr = max(p[2] for p in pts) or 1.0
    sums = [0.0] * nbins
    counts = [0] * nbins
    for x, y, r in pts:
        b = min(int(r / maxr * (nbins - 1)), nbins - 1)
        sums[b] += frame.luma(x, y)
        counts[b] += 1
    radial = [sums[i] / counts[i] if counts[i] else 0.0 for i in range(nbins)]

    def residual(px, py):
        dx, dy = px - c, py - c
        r = math.sqrt(dx * dx + dy * dy)
        b = min(int(r / maxr * (nbins - 1)), nbins - 1)
        return frame.luma(px, py) - radial[b]

    def rotation_mad(ang: float) -> float:
        ca, sa = math.cos(ang), math.sin(ang)
        diffs = []
        for x, y, _ in pts:
            dx, dy = x - c, y - c
            rx = round(c + dx * ca - dy * sa)
            ry = round(c + dx * sa + dy * ca)
            if 0 <= rx < n and 0 <= ry < n:
                diffs.append(abs(residual(x, y) - residual(rx, ry)))
        return sum(diffs) / len(diffs) if diffs else float("inf")

    ang = 2.0 * math.pi / fold
    mad = rotation_mad(ang)
    half_mad = rotation_mad(ang / 2.0) if exact else None
    ok = mad <= tol and (not exact or half_mad >= min_half_step_diff)
    detail = (f"angular residual diff: {360 / fold:g}deg={mad:.1f} (tol {tol})")
    if exact:
        detail += (f", {180 / fold:g}deg={half_mad:.1f} "
                   f"(need >= {min_half_step_diff})")
    return Check(f"rotational_symmetry({fold})", ok, detail)


def _circle_at(frame: Frame, center_x: float, center_y: float, radius: float,
               tol: float, min_contrast: float, samples: int, name: str) -> Check:
    import math
    n = frame.size
    # Task coordinates follow GLSL/fragCoord convention (origin at bottom-left),
    # while captured image rows use an origin at the top-left.
    cx, cy = center_x * (n - 1), (1.0 - center_y) * (n - 1)
    centre = frame.luma(round(cx), round(cy))
    corners = [frame.luma(0, 0), frame.luma(n - 1, 0),
               frame.luma(0, n - 1), frame.luma(n - 1, n - 1)]
    background = sum(corners) / len(corners)
    contrast = abs(centre - background)
    if contrast < min_contrast:
        return Check(name, False,
                     f"centre/background contrast {contrast:.1f} (need >= {min_contrast})")

    threshold = (centre + background) / 2.0
    centre_is_bright = centre > background
    radii = []
    max_px = int(n * 0.49)
    for i in range(samples):
        a = 2.0 * math.pi * i / samples
        transition = None
        for px in range(1, max_px + 1):
            x = round(cx + math.cos(a) * px)
            y = round(cy + math.sin(a) * px)
            if not (0 <= x < n and 0 <= y < n):
                break
            lum = frame.luma(x, y)
            outside = lum < threshold if centre_is_bright else lum > threshold
            if outside:
                transition = px / n
                break
        if transition is not None:
            radii.append(transition)

    if len(radii) < samples:
        return Check(name, False, f"found boundaries on {len(radii)}/{samples} rays")
    errors = [abs(r - radius) for r in radii]
    ok = max(errors) <= tol
    return Check(name, ok,
                 f"radii {min(radii):.3f}-{max(radii):.3f}, want {radius:.3f} +/-{tol:.3f}")


def circle_radius(frame: Frame, radius: float, tol: float = 0.04,
                  min_contrast: float = 30.0, samples: int = 32) -> Check:
    """Check that a centred bright/dark region has a circular boundary.

    Symmetry plus a bright centre cannot distinguish a circle from a square.
    Estimate the first foreground/background transition along multiple rays and
    require every direction to meet the requested radius.
    """
    return _circle_at(frame, 0.5, 0.5, radius, tol, min_contrast, samples,
                      "circle_radius")


def circle_at(frame: Frame, center_x: float, center_y: float, radius: float,
              tol: float = 0.04, min_contrast: float = 30.0,
              samples: int = 32) -> Check:
    """Check a circular boundary at a specified normalized coordinate."""
    name = f"circle_at({center_x:.2f},{center_y:.2f})"
    return _circle_at(frame, center_x, center_y, radius, tol, min_contrast, samples, name)


def ring_radii(frame: Frame, inner: float, outer: float, tol: float = 0.04,
               min_contrast: float = 30.0, samples: int = 32) -> Check:
    """Estimate the inner and outer boundaries of a centred bright ring."""
    import math
    n = frame.size
    c = (n - 1) / 2.0
    mid_r = (inner + outer) / 2.0
    ring_samples = []
    background_samples = [frame.luma(round(c), round(c))]
    for i in range(samples):
        a = 2.0 * math.pi * i / samples
        ring_samples.append(frame.luma(round(c + math.cos(a) * mid_r * n),
                                       round(c + math.sin(a) * mid_r * n)))
        probe = min(0.48, outer + 0.08)
        background_samples.append(frame.luma(round(c + math.cos(a) * probe * n),
                                             round(c + math.sin(a) * probe * n)))
    ring_mean = sum(ring_samples) / len(ring_samples)
    background = sum(background_samples) / len(background_samples)
    if ring_mean < background + min_contrast:
        return Check("ring_radii", False,
                     f"ring/background contrast {ring_mean - background:.1f} "
                     f"(need >= {min_contrast})")
    threshold = (ring_mean + background) / 2.0
    found_inner, found_outer = [], []
    for i in range(samples):
        a = 2.0 * math.pi * i / samples
        states = []
        for px in range(int(n * 0.49)):
            x = round(c + math.cos(a) * px)
            y = round(c + math.sin(a) * px)
            states.append(frame.luma(x, y) >= threshold)
        enter = next((j for j, state in enumerate(states) if state), None)
        leave = (next((j for j in range((enter or 0) + 1, len(states))
                       if not states[j]), None) if enter is not None else None)
        if enter is not None and leave is not None:
            found_inner.append(enter / n)
            found_outer.append(leave / n)
    if len(found_inner) < samples:
        return Check("ring_radii", False,
                     f"found two boundaries on {len(found_inner)}/{samples} rays")
    error = max(max(abs(r - inner) for r in found_inner),
                max(abs(r - outer) for r in found_outer))
    return Check("ring_radii", error <= tol,
                 f"inner {min(found_inner):.3f}-{max(found_inner):.3f}, "
                 f"outer {min(found_outer):.3f}-{max(found_outer):.3f}; "
                 f"want {inner:.3f}/{outer:.3f} +/-{tol:.3f}")


def box_bounds(frame: Frame, half_width: float, half_height: float,
               center_x: float = 0.5, center_y: float = 0.5,
               tol: float = 0.04, min_contrast: float = 30.0) -> Check:
    """Check the extents and filled corners of an axis-aligned rectangle."""
    n = frame.size
    cx, cy = round(center_x * (n - 1)), round(center_y * (n - 1))
    foreground = frame.luma(cx, cy)
    background = sum(frame.luma(x, y) for x, y in
                     ((0, 0), (n - 1, 0), (0, n - 1), (n - 1, n - 1))) / 4
    if abs(foreground - background) < min_contrast:
        return Check("box_bounds", False, "insufficient foreground/background contrast")
    bright = foreground > background
    threshold = (foreground + background) / 2

    def outside(x: int, y: int) -> bool:
        lum = frame.luma(x, y)
        return lum < threshold if bright else lum > threshold

    extents = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        hit = None
        for px in range(1, int(n * 0.49)):
            x, y = cx + dx * px, cy + dy * px
            if not (0 <= x < n and 0 <= y < n) or outside(x, y):
                hit = px / n
                break
        extents.append(hit)
    if any(value is None for value in extents):
        return Check("box_bounds", False, f"missing boundary: {extents}")
    expected = (half_width, half_width, half_height, half_height)
    extent_ok = all(abs(got - want) <= tol for got, want in zip(extents, expected))
    corner_ok = True
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = round((center_x + sx * half_width * 0.85) * (n - 1))
            y = round((center_y + sy * half_height * 0.85) * (n - 1))
            corner_ok &= not outside(x, y)
    return Check("box_bounds", extent_ok and corner_ok,
                 f"extents {[round(v, 3) for v in extents]}, "
                 f"want {half_width:.3f}/{half_height:.3f}; filled corners={corner_ok}")


def sharp_edges(frame: Frame, min_ratio: float = 0.010,
                min_gradient: float = 70.0) -> Check:
    """A meaningful fraction of pixels sit on a hard boundary.

    Distinguishes a real signed-distance shape from a soft blur that happens to
    have a bright middle.
    """
    n, step = frame.size, max(1, frame.size // 96)
    edge = total = 0
    for y in range(step, n - step, step):
        for x in range(step, n - step, step):
            gx = abs(frame.luma(x + step, y) - frame.luma(x - step, y))
            gy = abs(frame.luma(x, y + step) - frame.luma(x, y - step))
            total += 1
            if max(gx, gy) > min_gradient:
                edge += 1
    ratio = edge / max(total, 1)
    return Check("sharp_edges", ratio >= min_ratio,
                 f"{ratio:.1%} of samples on a hard boundary (need >= {min_ratio:.1%})")


def region_brighter(frame: Frame, x: float, y: float, than_x: float, than_y: float,
                    r: float = 0.06, margin: float = 25.0) -> Check:
    """Region A is brighter than region B. Tests placement, not just colour."""
    n = frame.size
    rad = max(1, int(r * n))

    def mean_at(nx, ny):
        cx, cy = int(nx * (n - 1)), int(ny * (n - 1))
        vals = [frame.luma(min(max(cx + dx, 0), n - 1), min(max(cy + dy, 0), n - 1))
                for dy in range(-rad, rad + 1, 2) for dx in range(-rad, rad + 1, 2)]
        return sum(vals) / len(vals)

    a, b = mean_at(x, y), mean_at(than_x, than_y)
    return Check(f"region_brighter({x:.2f},{y:.2f})", a > b + margin,
                 f"A={a:.0f} vs B={b:.0f} (need A > B + {margin:.0f})")


def distinct_bands(frame: Frame, count: int, axis: str = "x", tol: int = 1) -> Check:
    """Counts flat bands along an axis — tests quantisation (step/floor)."""
    n, step = frame.size, max(1, frame.size // 128)
    mid = n // 2
    vals = [frame.luma(i, mid) if axis == "x" else frame.luma(mid, i)
            for i in range(0, n, step)]
    transitions = sum(1 for i in range(1, len(vals)) if abs(vals[i] - vals[i - 1]) > 18)
    got = transitions + 1
    return Check(f"distinct_bands({count},{axis})", abs(got - count) <= tol,
                 f"found ~{got} bands, want {count} +/-{tol}")


def centroid_moves(result: RenderResult, axis: str = "x", direction: str = "increasing",
                   min_delta: float = 0.15, max_orthogonal_delta: float = 0.08) -> Check:
    """Check directional motion of the rendered brightness centroid."""
    if len(result.frames) < 2:
        return Check("centroid_moves", False, "need >= 2 frames")

    def centroid(frame: Frame) -> tuple[float, float]:
        n, step = frame.size, max(1, frame.size // 64)
        samples = [(x, y, frame.luma(x, y))
                   for y in range(0, n, step) for x in range(0, n, step)]
        baseline = min(value for _, _, value in samples)
        total = sx = sy = 0.0
        for x, y, value in samples:
            weight = max(0.0, value - baseline)
            total += weight
            sx += weight * x / (n - 1)
            sy += weight * y / (n - 1)
        return (sx / total, sy / total) if total else (0.5, 0.5)

    first, last = centroid(result.frames[0]), centroid(result.frames[-1])
    idx = 0 if axis == "x" else 1
    orth = 1 - idx
    delta = last[idx] - first[idx]
    directed = delta >= min_delta if direction == "increasing" else delta <= -min_delta
    stable_orthogonal = abs(last[orth] - first[orth]) <= max_orthogonal_delta
    return Check(f"centroid_moves({axis},{direction})", directed and stable_orthogonal,
                 f"centroid {first[0]:.2f},{first[1]:.2f} -> "
                 f"{last[0]:.2f},{last[1]:.2f}; delta={delta:+.2f}")


# --------------------------------------------------------------------------
# Dispatch — task.json names properties by string
# --------------------------------------------------------------------------

FRAME_CHECKS = {
    "not_blank": not_blank,
    "no_nan_artifacts": no_nan_artifacts,
    "pixel_near": pixel_near,
    "dominant_channel": dominant_channel,
    "dominant_channels": dominant_channels,
    "gradient_along": gradient_along,
    "symmetric": symmetric,
    "asymmetric": asymmetric,
    "radial_falloff": radial_falloff,
    "tiles": tiles,
    "rotational_symmetry": rotational_symmetry,
    "circle_radius": circle_radius,
    "circle_at": circle_at,
    "ring_radii": ring_radii,
    "box_bounds": box_bounds,
    "sharp_edges": sharp_edges,
    "region_brighter": region_brighter,
    "distinct_bands": distinct_bands,
}

RESULT_CHECKS = {
    "animates": animates,
    "stable_over_time": stable_over_time,
    "centroid_moves": centroid_moves,
}


def evaluate(result: RenderResult, properties: list[dict]) -> list[Check]:
    """Run every named property. `properties` comes straight from task.json."""
    checks: list[Check] = []
    for spec in properties:
        name = spec.get("check")
        kwargs = {k: v for k, v in spec.items() if k != "check"}
        if name in RESULT_CHECKS:
            checks.append(RESULT_CHECKS[name](result, **kwargs))
        elif name in FRAME_CHECKS:
            if isinstance(kwargs.get("rgb"), list):
                kwargs["rgb"] = tuple(kwargs["rgb"])
            checks.append(FRAME_CHECKS[name](result.first, **kwargs))
        else:
            checks.append(Check(name or "?", False, "unknown check"))
    return checks
