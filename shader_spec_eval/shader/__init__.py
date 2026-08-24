"""Objective quality evaluation for shader code.

Renders a fragment shader headlessly and asserts properties derived from the
task specification, rather than diffing against one reference implementation.
"""
from .assertions import Check, evaluate
from .render import Frame, RenderResult, render, save_png

__all__ = ["Check", "Frame", "RenderResult", "evaluate", "render", "save_png"]
