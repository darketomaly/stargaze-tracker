# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "numpy", "astral"]
# ///

"""Prepare the data and render one stargazing picture."""

from pathlib import Path

from fetch import FILE
from plot_data import load_observation, rows
from plot_render import render


HERE = Path(__file__).parent
DATA = HERE / "data" / FILE
OUT = HERE / "out"
PICTURE = "plot.png"
SPRITE = HERE / "sprites" / "cloud.png"
FONT_DIR = HERE / "fonts"


def main():
    observations = [
        load_observation(DATA, row_index)
        for row_index in range(len(rows(DATA)))
    ]
    render(observations, SPRITE, FONT_DIR, OUT / PICTURE, initial_index=11)


if __name__ == "__main__":
    main()
