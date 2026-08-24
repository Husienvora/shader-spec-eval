"""Is this eval any good?

An eval that produces numbers is not the same as an eval that measures something.
Three questions decide it, and they are separable:

  1. DISCRIMINATION — do models get meaningfully different scores, or does
     everything cluster? A ceiling of 100% ranks nothing.

  2. RELIABILITY — run the same model twice. If it moves more between its own
     runs than models differ from each other, the eval is a noise generator.
     This is the ratio that matters and it is the one people skip.

  3. VALIDITY — does it track an independent measure of the same ability
     (LiveBench `spatial`) more closely than a different ability
     (`code_generation`)? If it tracks coding better, it is a coding eval
     wearing a graphics costume.

All statistics are stdlib. No scipy dependency for a handful of models.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .bench import Cell

_REP = re.compile(r"\s+#\d+$")


def base_name(model: str) -> str:
    """'gemini-3.6-flash #2' -> 'gemini-3.6-flash'"""
    return _REP.sub("", model).strip()


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def spearman(a: list[float], b: list[float]) -> float | None:
    """Rank correlation. None if there is not enough signal to compute one."""
    n = len(a)
    if n < 3:
        return None

    def ranks(xs):
        order = sorted(range(n), key=lambda i: xs[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    ma, mb = mean(ra), mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    if da == 0 or db == 0:          # everything tied — no ranking possible
        return None
    return num / (da * db)


@dataclass
class Verdict:
    reliable: bool
    headline: str
    reasons: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def analyse(cells: list[Cell], tasks: list[str],
            external: dict[str, dict] | None = None) -> Verdict:
    """external: {model_label -> {metric -> value}} from LiveBench etc."""
    real = [c for c in cells
            if not c.model.startswith("reference") and c.scorable]
    if not real:
        return Verdict(False, "No model runs to analyse.")

    # ---- group repeats -------------------------------------------------
    runs: dict[str, dict[str, list[float]]] = {}
    for c in real:
        runs.setdefault(base_name(c.model), {}).setdefault(c.task, []).append(c.score)

    per_model_run_scores: dict[str, list[float]] = {}
    for m, by_task in runs.items():
        n_reps = max(len(v) for v in by_task.values())
        for r in range(n_reps):
            vals = [v[r] for v in by_task.values() if len(v) > r]
            if vals:
                per_model_run_scores.setdefault(m, []).append(mean(vals))

    model_means = {m: mean(v) for m, v in per_model_run_scores.items()}
    within = [stdev(v) for v in per_model_run_scores.values() if len(v) > 1]
    within_sd = mean(within) if within else None
    between_sd = stdev(list(model_means.values()))

    stats = {
        "models": len(model_means),
        "model_means": {m: round(v, 4) for m, v in model_means.items()},
        "between_sd": round(between_sd, 4),
        "within_sd": round(within_sd, 4) if within_sd is not None else None,
        "repeats_available": within_sd is not None,
        "score_range": [round(min(model_means.values()), 4),
                        round(max(model_means.values()), 4)],
    }

    reasons: list[str] = []
    fixes: list[str] = []
    ok = True

    # ---- 1. discrimination ---------------------------------------------
    lo, hi = stats["score_range"]
    at_ceiling = [m for m, v in model_means.items() if v >= 0.999]
    if len(model_means) < 2:
        ok = False
        reasons.append("DISCRIMINATION UNTESTED: a one-model run cannot show whether "
                       "the ladder separates models.")
        fixes.append("Add another model only when comparison capacity is available; "
                     "the current run is still useful for local test-retest variance.")
    elif len(at_ceiling) >= max(2, len(model_means) // 2):
        ok = False
        reasons.append(
            f"CEILING: {len(at_ceiling)}/{len(model_means)} models score 100%. "
            "The ladder cannot rank them.")
        fixes.append("Add harder tiers — the fix is the task set, not the maths. "
                     "Raymarching, nested polar domains, correct 3D lighting.")
    elif hi - lo < 0.15:
        ok = False
        reasons.append(f"NARROW SPREAD: all models within {(hi-lo)*100:.0f} points.")
        fixes.append("Add tiers that separate the top, or drop tiers everything passes.")
    else:
        reasons.append(f"Discriminates: scores span {lo*100:.0f}%–{hi*100:.0f}%.")

    # ---- 2. reliability -------------------------------------------------
    if within_sd is None:
        ok = False
        reasons.append("UNKNOWN RELIABILITY: no repeated runs, so run-to-run noise "
                       "has never been measured.")
        fixes.append("Run with --repeats 3 or more. Without it no score is "
                     "trustworthy at the precision being reported.")
    elif len(model_means) < 2:
        reasons.append(f"Test-retest variability measured: within-model SD "
                       f"{within_sd:.3f} across repeated full-ladder runs. "
                       "Signal/noise needs at least two models.")
    else:
        snr = between_sd / within_sd if within_sd > 0 else float("inf")
        stats["signal_to_noise"] = round(snr, 2)
        if snr < 1.0:
            ok = False
            reasons.append(
                f"NOISE DOMINATES: within-model SD {within_sd:.3f} exceeds "
                f"between-model SD {between_sd:.3f} (ratio {snr:.2f}). A model "
                "differs from itself more than from other models.")
            fixes.append("Average more repeats per cell, and add tasks. Both reduce "
                         "the noise floor; neither requires changing the maths.")
        elif snr < 2.0:
            reasons.append(f"Marginal reliability: signal/noise {snr:.2f}. "
                           "Rankings of adjacent models are not trustworthy.")
            fixes.append("Report only large gaps, or increase repeats until "
                         "signal/noise exceeds 2.")
        else:
            reasons.append(f"Reliable: signal/noise {snr:.2f} — models differ from "
                           "each other far more than from themselves.")

    # ---- 3. validity ----------------------------------------------------
    if external:
        shared = [m for m in model_means if m in external]
        if len(shared) >= 3:
            vis = [model_means[m] for m in shared]
            for metric in ("spatial", "code_generation", "code_completion"):
                vals = [external[m].get(metric) for m in shared]
                if any(v is None for v in vals):
                    continue
                rho = spearman(vis, [float(v) for v in vals])
                stats[f"rho_{metric}"] = round(rho, 3) if rho is not None else None

            rs, rc = stats.get("rho_spatial"), stats.get("rho_code_generation")
            if rs is None and rc is None:
                reasons.append("VALIDITY UNTESTED: external scores are all tied, so "
                               "no rank correlation can be computed.")
                fixes.append("Include models whose published scores actually differ.")
            elif rs is not None and rc is not None:
                if rs > rc + 0.15:
                    reasons.append(
                        f"Convergent validity: tracks spatial (rho={rs:+.2f}) more "
                        f"than coding (rho={rc:+.2f}). It measures what it claims.")
                elif rc > rs + 0.15:
                    ok = False
                    reasons.append(
                        f"WRONG CONSTRUCT: tracks coding (rho={rc:+.2f}) more than "
                        f"spatial (rho={rs:+.2f}). This is a coding eval in a "
                        "graphics costume.")
                    fixes.append("Reduce the GLSL-syntax burden so shader-API "
                                 "familiarity stops dominating the score.")
                else:
                    reasons.append(f"Inconclusive validity: spatial rho={rs:+.2f} vs "
                                   f"coding rho={rc:+.2f} — too close to separate.")
                    fixes.append("More models. Rank correlation on 3–4 points cannot "
                                 "distinguish these.")
        else:
            reasons.append(f"VALIDITY UNTESTED: only {len(shared)} model(s) have "
                           "published scores; 3 is the minimum for a correlation.")
            fixes.append("Benchmark models that appear on LiveBench, or add entries "
                         "to the local scores file.")
    else:
        reasons.append("VALIDITY UNTESTED: no external scores supplied.")

    # ---- 4. per-task usefulness ----------------------------------------
    dead = []
    if len(model_means) >= 2:
        for t in tasks:
            vals = [mean(runs[m].get(t, [])) for m in runs if runs[m].get(t)]
            if len(vals) >= 2 and stdev(vals) < 0.02:
                dead.append(t)
    if dead:
        stats["non_discriminating_tasks"] = dead
        reasons.append(f"{len(dead)}/{len(tasks)} tasks give every model the same "
                       f"score: {', '.join(t.replace('shader-','') for t in dead)}.")
        fixes.append("Those tasks add runtime and no information. Replace them with "
                     "harder variants.")

    headline = ("The eval discriminates and is reliable enough to rank models."
                if ok else
                "Not yet a trustworthy eval — see the reasons below.")
    return Verdict(ok, headline, reasons, fixes, stats)
