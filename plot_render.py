"""Render a prepared observation as a stargazing picture."""

import math
import random
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.image import imread
from matplotlib.patches import Circle, Rectangle
from matplotlib.transforms import Affine2D
import numpy as np

from plot_data import Observation, TIMEZONE, lerp_color


def register_fonts(font_dir):
    """Register the bundled Google Fonts family before drawing any text."""
    for font_name in ("Rajdhani-Regular.ttf", "Rajdhani-Bold.ttf"):
        font_manager.fontManager.addfont(font_dir / font_name)
    plt.rcParams["font.family"] = "Rajdhani"


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


def draw_stars(ax, score):
    variation = random.Random()
    star_count = round(120 * max(0, min(score, 100)) / 100)
    stars_x = [variation.uniform(0, 8) for _ in range(star_count)]
    stars_y = [variation.uniform(0, 6) for _ in range(star_count)]
    star_sizes = [variation.uniform(3, 14) for _ in range(star_count)]
    star_alphas = [variation.uniform(0.4, 1) for _ in range(star_count)]
    ax.scatter(stars_x, stars_y, s=star_sizes, c="#fff4c2",
               alpha=star_alphas, linewidths=0)


def draw_clouds(ax, coverage_fraction, sprite_path):
    cloud = imread(sprite_path)
    variation = random.Random()
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


def draw_information_panel(ax, observation):
    ax.add_patch(Rectangle((-0.05, 3.72), 3.35, 2.48,
                           facecolor="black", alpha=0.55, edgecolor="none"))
    info_rows = (
        (f"Time ({TIMEZONE})", observation.readable_time),
        ("Cloud coverage", f"{observation.cloud_coverage:.0f}%"),
        ("Visibility", observation.visibility),
        ("Moon illumination", f"{observation.moon_illumination:.0f}%"),
        ("Moon altitude", f"{observation.moon_altitude:.1f}°"),
        ("Moon phase", observation.moon_name),
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


def draw_score_panel(ax, score):
    score_color = "#43d17a" if score >= 50 else "#ff5c5c"
    ax.add_patch(Rectangle((-0.05, 0.18), 2.2, 0.55,
                           facecolor="black", alpha=0.65, edgecolor="none"))
    ax.text(0.05, 0.35, "Chance of good stargazing:",
            ha="left", va="bottom", fontsize=11, fontweight="bold",
            color="#ffffff")
    ax.text(1.85, 0.35, f"{score:.0f}%",
            ha="left", va="bottom", fontsize=11, fontweight="bold",
            color=score_color)


def render(observation, sprite_path, font_dir, output_path):
    register_fonts(font_dir)
    background = lerp_color(
        (0.01, 0.02, 0.10),
        (0.35, 0.70, 0.95),
        observation.daylight_brightness,
    )
    fig, ax = plt.subplots(figsize=(10, 8), facecolor=background)
    ax.set_facecolor(background)

    draw_stars(ax, observation.stargaze_score)
    sun_x = observation.sun_azimuth / 360 * 8
    sun_y = max(0, min(6, observation.sun_altitude / 90 * 6))
    moon_x, moon_y = 7, 5
    if observation.sun_altitude > 0:
        ax.add_patch(Circle((sun_x, sun_y), 0.45, color="#ffd34e"))
    ax.imshow(moon_image(observation.moon_phase),
              extent=(moon_x - 0.45, moon_x + 0.45,
                      moon_y - 0.45, moon_y + 0.45))
    ax.text(moon_x, moon_y - 0.7,
            "Visible" if observation.moon_altitude > 0
            else "Moon below horizon\nmoonlight not included in score",
            ha="center", va="top", fontsize=11, color="#ffffff")
    draw_clouds(ax, observation.coverage_fraction, sprite_path)
    draw_information_panel(ax, observation)
    draw_score_panel(ax, observation.stargaze_score)

    ax.set_xlim(0, 8)
    ax.set_ylim(0, 6)
    ax.axis("off")
    fig.tight_layout()
    output_path.parent.mkdir(exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.show()
    plt.close(fig)
