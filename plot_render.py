"""Render a prepared observation as a stargazing picture."""

import math
import random
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.image import imread
from matplotlib.patches import Circle, Rectangle
from matplotlib.transforms import Affine2D
from matplotlib.widgets import Button, Slider
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
    if star_count == 0:
        return
    stars_x = [variation.uniform(0, 8) for _ in range(star_count)]
    stars_y = [variation.uniform(0, 6) for _ in range(star_count)]
    star_sizes = [variation.uniform(3, 14) for _ in range(star_count)]
    star_alphas = [variation.uniform(0.4, 1) for _ in range(star_count)]
    ax.scatter(stars_x, stars_y, s=star_sizes, c="#fff4c2",
               alpha=star_alphas, linewidths=0)


def draw_sky(ax, color):
    variation = random.Random()
    base = np.array(color)
    bottom = np.clip(base * variation.uniform(0.82, 0.94), 0, 1)
    top = np.clip(base * variation.uniform(1.04, 1.18), 0, 1)
    gradient = np.linspace(bottom, top, 256)[:, np.newaxis, :]
    ax.imshow(gradient, extent=(0, 8, 0, 6), aspect="auto",
              interpolation="bicubic", zorder=0)


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
                  transform=transform,
                  alpha=variation.uniform(0.55, 1.0))


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


def render_image(observation, sprite_path, width, height):
    background = lerp_color(
        (0.01, 0.02, 0.10),
        (0.35, 0.70, 0.95),
        observation.daylight_brightness,
    )
    fig, ax = plt.subplots(
        figsize=(width / 100, height / 100),
        dpi=100,
        facecolor=background,
    )
    fig.subplots_adjust(0, 0, 1, 1)
    draw_sky(ax, background)

    draw_stars(ax, observation.stargaze_score)
    sun_x = observation.sun_azimuth / 360 * 8
    sun_y = max(0, min(6, observation.sun_altitude / 90 * 6))
    moon_x = observation.moon_azimuth / 360 * 8
    moon_y = max(0, min(6, observation.moon_altitude / 90 * 6))
    if observation.sun_altitude > 0:
        ax.add_patch(Circle((sun_x, sun_y), 0.45, color="#ffd34e"))
    if observation.moon_altitude > 0:
        ax.imshow(moon_image(observation.moon_phase),
                  extent=(moon_x - 0.45, moon_x + 0.45,
                          moon_y - 0.45, moon_y + 0.45))
    draw_clouds(ax, observation.coverage_fraction, sprite_path)
    draw_information_panel(ax, observation)
    draw_score_panel(ax, observation.stargaze_score)

    ax.set_xlim(0, 8)
    ax.set_ylim(0, 6)
    ax.axis("off")
    fig.canvas.draw()
    image = np.asarray(fig.canvas.buffer_rgba()).copy()
    plt.close(fig)
    return image


def preview_size(window):
    screen_height = None
    if window is not None and hasattr(window, "winfo_screenheight"):
        screen_height = window.winfo_screenheight()
    elif window is not None and hasattr(window, "screen"):
        screen = window.screen()
        if screen is not None:
            screen_height = screen.availableGeometry().height()
    elif window is not None and hasattr(window, "GetDisplaySize"):
        screen_height = window.GetDisplaySize()[1]

    height = min(640, round(screen_height * 0.75)) if screen_height else 640
    return round(height * 1.25), height


def render(observations, sprite_path, font_dir, output_path, initial_index=0):
    register_fonts(font_dir)
    window = None
    width, height = 800, 640
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    window = getattr(fig.canvas.manager, "window", None)
    if window is not None:
        width, height = preview_size(window)
        fig.set_size_inches(width / 100, height / 100)
        if hasattr(window, "resizable"):
            window.resizable(False, False)
        elif hasattr(window, "setFixedSize"):
            window.setFixedSize(width, height)
        if hasattr(window, "geometry"):
            window.geometry(f"{width}x{height}")

    ax.axis("off")
    loading_text = ax.text(
        0.5, 0.5, "Preparing sky images...", ha="center", va="center",
        fontsize=14,
    )
    plt.show(block=False)
    fig.canvas.draw()
    fig.canvas.flush_events()

    images = []
    for index, observation in enumerate(observations, start=1):
        images.append(render_image(observation, sprite_path, width, height))
        loading_text.set_text(
            f"Preparing sky images... {index}/{len(observations)}"
        )
        fig.canvas.draw_idle()
        fig.canvas.flush_events()

    initial_index = max(0, min(initial_index, len(images) - 1))
    fig.subplots_adjust(bottom=0.15)
    ax.clear()
    image_artist = ax.imshow(images[initial_index], interpolation="nearest")
    ax.axis("off")
    slider_ax = fig.add_axes((0.2, 0.04, 0.6, 0.04))
    save_ax = fig.add_axes((0.83, 0.035, 0.1, 0.05))
    slider = Slider(
        slider_ax,
        "Time",
        0,
        len(images) - 1,
        valinit=initial_index,
        valstep=1,
        valfmt="%d",
    )
    save_button = Button(save_ax, "Save")

    fig.canvas.draw()
    image_artist.set_animated(True)
    background = fig.canvas.copy_from_bbox(ax.bbox)

    def redraw_image(_event=None):
        fig.canvas.restore_region(background)
        ax.draw_artist(image_artist)
        fig.canvas.blit(ax.bbox)

    def update(index):
        index = round(index)
        image_artist.set_data(images[index])
        slider.valtext.set_text(observations[index].readable_time)
        fig.canvas.draw_idle()

    def save(_event):
        output_path.parent.mkdir(exist_ok=True)
        selected = observations[round(slider.val)]
        image = render_image(selected, sprite_path, 1500, 1200)
        plt.imsave(output_path, image)
        print(f"saved {output_path}")

    fig.canvas.mpl_connect("draw_event", redraw_image)
    slider.on_changed(update)
    save_button.on_clicked(save)
    slider.valtext.set_text(observations[initial_index].readable_time)
    redraw_image()
    plt.show()
    plt.close(fig)
