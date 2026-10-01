# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "numpy", "astral"]
# ///

"""
Read the file in data/, make one picture, save it to out/.

    uv run plot.py

Three parts, and you will replace all three: rows() reads the file the way *your*
file needs reading, the loop in main() picks the numbers out of it, and the plot at
the bottom is the transformation you chose. Print before you plot.
"""

import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.image import imread
from matplotlib.patches import Circle, Rectangle
from matplotlib.transforms import Affine2D
import numpy as np
from fetch import FILE

PICTURE = "plot.png"                           # what goes into out/, and into the README

HERE = Path(__file__).parent
DATA = HERE / "data" / FILE
OUT = HERE / "out"
SPRITE = HERE / "sprites" / "cloud.png"
FONT_DIR = HERE / "fonts"
TIMEZONE = "HKT"

def rows(path):
    """Read hourly cloud coverage from the generated CSV."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def register_fonts():
    """Register the bundled Google Fonts family before drawing any text."""
    for font_name in ("Rajdhani-Regular.ttf", "Rajdhani-Bold.ttf"):
        font_manager.fontManager.addfont(FONT_DIR / font_name)
    plt.rcParams["font.family"] = "Rajdhani"

def format_visibility(meters):
    if meters >= 1000:
        return f"{meters / 1000:.2f}".rstrip("0").rstrip(".") + " km"
    return f"{meters:.0f} m"

def lerp_color(start, end, amount):
    return tuple(
        start_channel + (end_channel - start_channel) * amount
        for start_channel, end_channel in zip(start, end)
    )

def moon_image(phase):
    coordinates = np.linspace(-1, 1, 100)
    x, y = np.meshgrid(coordinates, coordinates)
    disk = x**2 + y**2 <= 1
    z = np.sqrt(np.maximum(0, 1 - x**2 - y**2))
    angle = 2 * math.pi * phase
    illuminated = x * math.sin(angle) + z * math.cos(angle) > 0
    image = np.zeros((100, 100, 4))
    image[..., :3] = (0.85, 0.85, 0.85)
    image[..., 3] = disk & illuminated
    return image

def main():
    register_fonts()
    table = rows(DATA)
    hkt = timezone(timedelta(hours=8))
    sunrise = datetime.fromisoformat(table[0]["sunrise"]).replace(tzinfo=hkt)
    sunset = datetime.fromisoformat(table[0]["sunset"]).replace(tzinfo=hkt)
    first = max(table, key=lambda row: float(row["stargaze_score"]))
    cloud_coverage = float(first["cloud_coverage"])
    coverage_fraction = max(0, min(cloud_coverage, 100)) / 100
    hkt_time = datetime.fromisoformat(first["time"]).replace(tzinfo=hkt)
    readable_time = hkt_time.strftime("%I:%M %p").lstrip("0")
    visibility = format_visibility(float(first["visibility"]))
    stargaze_score = float(first["stargaze_score"])
    moon_phase = float(first["moon_phase"])
    moon_illumination = float(first["moon_illumination"])
    moon_altitude = float(first["moon_altitude"])
    moon_azimuth = float(first["moon_azimuth"])
    sun_altitude = float(first["sun_altitude"])
    sun_azimuth = float(first["sun_azimuth"])
    daylight_progress = (
        (hkt_time - sunrise).total_seconds()
        / (sunset - sunrise).total_seconds()
    )
    daylight_brightness = (
        math.sin(math.pi * daylight_progress)
        if 0 <= daylight_progress <= 1
        else 0
    )
    background = lerp_color((0.01, 0.02, 0.10), (0.35, 0.70, 0.95),
                            daylight_brightness)

    fig, ax = plt.subplots(figsize=(10, 8), facecolor=background)
    ax.set_facecolor(background)
    star_variation = random.Random(84)
    star_count = round(120 * max(0, min(stargaze_score, 100)) / 100)
    stars_x = [star_variation.uniform(0, 8) for _ in range(star_count)]
    stars_y = [star_variation.uniform(0, 6) for _ in range(star_count)]
    star_sizes = [star_variation.uniform(3, 14) for _ in range(star_count)]
    star_alphas = [star_variation.uniform(0.4, 1) for _ in range(star_count)]
    ax.scatter(stars_x, stars_y, s=star_sizes, c="#fff4c2",
               alpha=star_alphas, linewidths=0)
    sun_x = sun_azimuth / 360 * 8
    sun_y = max(0, min(6, sun_altitude / 90 * 6))
    moon_x, moon_y = 7, 5
    if sun_altitude > 0:
        ax.add_patch(Circle((sun_x, sun_y), 0.45, color="#ffd34e"))
    ax.imshow(moon_image(moon_phase),
              extent=(moon_x - 0.45, moon_x + 0.45,
                      moon_y - 0.45, moon_y + 0.45))
    ax.text(moon_x, moon_y - 0.7,
            "Visible" if moon_altitude > 0
            else "Moon below horizon\nmoonlight not included in score",
            ha="center", va="top", fontsize=11, color="#ffffff")
    cloud = imread(SPRITE)
    variation = random.Random(42)
    positions = [(x, y) for x in range(8) for y in range(6)]
    variation.shuffle(positions)
    cloud_count = round(len(positions) * coverage_fraction)
    for x, y in positions[:cloud_count]:
            jitter_x = variation.uniform(-0.15, 0.15)
            jitter_y = variation.uniform(-0.15, 0.15)
            left, bottom = x + jitter_x, y + jitter_y
            center_x, center_y = left + 0.5, bottom + 0.5
            rotation = variation.uniform(-12, 12)
            transform = (Affine2D()
                         .rotate_deg_around(center_x, center_y, rotation)
                         + ax.transData)
            ax.imshow(cloud, extent=(left, left + 1, bottom, bottom + 1),
                      transform=transform)
    ax.add_patch(Rectangle((-0.05, 3.72), 3.35, 2.48,
                           facecolor="black", alpha=0.55, edgecolor="none"))
    info_rows = (
        (f"Time ({TIMEZONE})", readable_time),
        ("Cloud coverage", f"{cloud_coverage:.0f}%"),
        ("Visibility", visibility),
        ("Moon illumination", f"{moon_illumination:.0f}%"),
        ("Moon altitude", f"{moon_altitude:.1f}°"),
        ("Moon phase", first["moon_name"]),
    )
    for row, (label, value) in enumerate(info_rows):
        y = 5.95 - row * 0.25
        ax.text(0.05, y, f"{label}:", ha="left", va="top",
                fontsize=11, color="#ffffff")
        ax.text(2.15, y, value, ha="left", va="top",
                fontsize=11, color="#bfbfbf")
    ax.text(0.05, 4.15, "Not considered:",
            ha="left", va="top", fontsize=11, color="#ffffff")
    ax.text(0.05, 3.9, "Light pollution, target altitude",
            ha="left", va="top", fontsize=11, color="#bfbfbf")
    score_color = "#43d17a" if stargaze_score >= 50 else "#ff5c5c"
    ax.add_patch(Rectangle((-0.05, 0.18), 2.2, 0.55,
                           facecolor="black", alpha=0.65, edgecolor="none"))
    ax.text(0.05, 0.35, "Chance of good stargazing:",
            ha="left", va="bottom", fontsize=11, fontweight="bold",
            color="#ffffff")
    ax.text(1.85, 0.35, f"{stargaze_score:.0f}%",
            ha="left", va="bottom", fontsize=11, fontweight="bold",
            color=score_color)
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 6)
    ax.axis("off")
    fig.tight_layout()

    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / PICTURE, dpi=150)
    print(f"saved out/{PICTURE}")
    plt.show()

if __name__ == "__main__":
    main()