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


def circle_radius(frame: Frame, radius: float, tol: float = 0.04,
                  min_contrast: float = 30.0, samples: int = 32) -> Check:
    """Check that a centred bright/dark region has a circular boundary.

    Symmetry plus a bright centre cannot distinguish a circle from a square.
    Estimate the first foreground/background transition along multiple rays and
    require every direction to meet the requested radius.
    """
    import math
    n = frame.size
    c = (n - 1) / 2.0
    centre = frame.luma(round(c), round(c))
    corners = [frame.luma(0, 0), frame.luma(n - 1, 0),
               frame.luma(0, n - 1), frame.luma(n - 1, n - 1)]
    background = sum(corners) / len(corners)
    contrast = abs(centre - background)
    if contrast < min_contrast:
        return Check("circle_radius", False,
                     f"centre/background contrast {contrast:.1f} (need >= {min_contrast})")

    threshold = (centre + background) / 2.0
    centre_is_bright = centre > background
    radii = []
    max_px = int(n * 0.49)
    for i in range(samples):
        a = 2.0 * math.pi * i / samples
        transition = None
        for px in range(1, max_px + 1):
            x = min(n - 1, max(0, round(c + math.cos(a) * px)))
            y = min(n - 1, max(0, round(c + math.sin(a) * px)))
            lum = frame.luma(x, y)
            outside = lum < threshold if centre_is_bright else lum > threshold
            if outside:
                transition = px / n
                break
        if transition is not None:
            radii.append(transition)

    if len(radii) < samples:
        return Check("circle_radius", False,
                     f"found boundaries on {len(radii)}/{samples} rays")
    errors = [abs(r - radius) for r in radii]
    ok = max(errors) <= tol
    return Check("circle_radius", ok,
                 f"radii {min(radii):.3f}-{max(radii):.3f}, want {radius:.3f} +/-{tol:.3f}")


def sharp_edges(frame: Frame, min_ratio: float = 0.010) -> Check:
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
            if max(gx, gy) > 70:
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
    "radial_falloff": radial_falloff,
    "tiles": tiles,
    "rotational_symmetry": rotational_symmetry,
    "circle_radius": circle_radius,
    "sharp_edges": sharp_edges,
    "region_brighter": region_brighter,
    "distinct_bands": distinct_bands,
}

RESULT_CHECKS = {
    "animates": animates,
    "stable_over_time": stable_over_time,
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
