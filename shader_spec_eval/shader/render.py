"""Headless deterministic shader rendering.

Uses Chromium's software rasteriser (SwiftShader) rather than the GPU. That is
slower and entirely deliberate: an eval other people run on other hardware has
to produce the same bytes on every machine, and driver-dependent output would
make published numbers meaningless.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

HARNESS = Path(__file__).with_name("harness.html")

# Force software rendering so output is machine-independent.
CHROMIUM_ARGS = [
    "--use-gl=swiftshader",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--disable-gpu-sandbox",
    "--deterministic-mode",
    "--disable-lcd-text",
    "--force-color-profile=srgb",
    "--disable-partial-raster",
    "--disable-skia-runtime-opts",
    "--disable-dev-shm-usage",
]


@dataclass
class Frame:
    ok: bool
    size: int = 0
    time: float = 0.0
    pixels: bytes = b""
    stage: str = ""
    log: str = ""

    def rgb(self, x: int, y: int) -> tuple[int, int, int]:
        """Pixel at (x, y) with y measured from the TOP, like an image viewer.

        WebGL's readPixels returns bottom-up, so we flip here once and let every
        assertion above this line think in normal image coordinates.
        """
        fy = self.size - 1 - y
        i = (fy * self.size + x) * 4
        return self.pixels[i], self.pixels[i + 1], self.pixels[i + 2]

    def luma(self, x: int, y: int) -> float:
        r, g, b = self.rgb(x, y)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b


@dataclass
class RenderResult:
    frames: list[Frame] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.frames) and all(f.ok for f in self.frames)

    @property
    def first(self) -> Frame:
        return self.frames[0]


def render(source: str, times: list[float] | None = None, size: int = 256) -> RenderResult:
    """Render `source` at each requested time. Returns one Frame per time."""
    times = times if times is not None else [0.0]

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return RenderResult(error=(
            "playwright not installed.\n"
            "  pip install playwright\n"
            "  python -m playwright install chromium"
        ))

    frames: list[Frame] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=CHROMIUM_ARGS)
            page = browser.new_page(viewport={"width": 320, "height": 320})
            page.goto(HARNESS.as_uri())
            page.wait_for_function("typeof window.renderShader === 'function'", timeout=15000)

            for t in times:
                res = page.evaluate(
                    "([src, opts]) => window.renderShader(src, opts)",
                    [source, {"size": size, "time": t}],
                )
                if not res or not res.get("ok"):
                    frames.append(Frame(
                        ok=False,
                        stage=(res or {}).get("stage", "unknown"),
                        log=(res or {}).get("log", "render returned nothing"),
                        time=t,
                    ))
                    break
                frames.append(Frame(
                    ok=True,
                    size=res["size"],
                    time=res["time"],
                    pixels=bytes(res["pixels"]),
                ))

            browser.close()
    except Exception as exc:                                  # noqa: BLE001
        return RenderResult(frames=frames, error=f"{type(exc).__name__}: {exc}")

    return RenderResult(frames=frames)


def save_png(frame: Frame, path: Path) -> bool:
    """Write a frame to disk for the video. Optional — needs Pillow."""
    try:
        from PIL import Image
    except ImportError:
        return False
    img = Image.frombytes("RGBA", (frame.size, frame.size), frame.pixels)
    img.transpose(Image.FLIP_TOP_BOTTOM).save(path)
    return True
