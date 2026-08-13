#!/usr/bin/env python3
"""Regression test for the `analyze` CLI command.

Bug: cli.py read `chi_square_indicator` from under each channel's `lsb_ratio`
dict, but steg_core.analyze_image() puts it directly on the channel dict
(only `zeros`/`ones` are nested under `lsb_ratio`). Every `analyze` run
crashed with KeyError: 'chi_square_indicator'.

This exercises the real CLI path (not just analyze_image(), which was never
broken) via Typer's CliRunner, on both a clean carrier and a stego-carrying
image. Run directly:  python test_analyze_cli.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from PIL import Image
from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def _noise_png(path: Path) -> None:
    """A deterministic RGB noise image, a realistic analyze target."""
    rng = np.random.default_rng(1234)
    arr = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    Image.fromarray(arr, "RGB").save(path)


def test_analyze_runs_clean_on_noise_carrier():
    with tempfile.TemporaryDirectory() as td:
        img = Path(td) / "carrier.png"
        _noise_png(img)
        result = runner.invoke(app, ["analyze", str(img)])
        assert result.exit_code == 0, (
            f"analyze exited {result.exit_code}; "
            f"exception={result.exception!r}")
        assert result.exception is None, result.exception
        # The channel-analysis table must actually render its anomaly verdict.
        assert "Verdict" in result.stdout, result.stdout


def test_analyze_runs_clean_on_stego_image():
    """An image with LSB data hidden should still analyze without crashing
    (and is the case the detector actually exists for)."""
    with tempfile.TemporaryDirectory() as td:
        carrier = Path(td) / "carrier.png"
        hidden = Path(td) / "hidden.png"
        _noise_png(carrier)
        enc = runner.invoke(app, [
            "encode-cmd", "-i", str(carrier), "-t", "regression secret",
            "-o", str(hidden)])
        assert enc.exit_code == 0, (
            f"encode failed {enc.exit_code}: {enc.exception!r}")
        result = runner.invoke(app, ["analyze", str(hidden)])
        assert result.exit_code == 0, (
            f"analyze exited {result.exit_code}; "
            f"exception={result.exception!r}")
        assert result.exception is None, result.exception


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL {name}: {e}")
    if failures:
        print(f"\n{failures} test(s) failed")
        sys.exit(1)
    print("\nall tests passed")
