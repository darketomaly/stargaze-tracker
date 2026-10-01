# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "numpy", "astral"]
# ///

"""Prepare the data and render one stargazing picture."""

from pathlib import Path

from fetch import FILE
from plot_data import load_observation
from plot_render import render


HERE = Path(__file__).parent
DATA = HERE / "data" / FILE
OUT = HERE / "out"
PICTURE = "plot.png"
SPRITE = HERE / "sprites" / "cloud.png"
FONT_DIR = HERE / "fonts"


def main():
    observation = load_observation(DATA)
    render(observation, SPRITE, FONT_DIR, OUT / PICTURE)
    print(f"saved out/{PICTURE}")


if __name__ == "__main__":
    main()
