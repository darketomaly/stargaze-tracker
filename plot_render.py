"""Render a prepared observation as a stargazing picture with Pygame."""

import math
import os
import random
from dataclasses import replace
from io import BytesIO
from pathlib import Path

os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitor")

import pygame

from plot_data import TIMEZONE, lerp_color


CLOUD_DRIFT_PERIOD = 60 * 60
CLOUD_DRIFT_SPEED = 1 / CLOUD_DRIFT_PERIOD
OBSERVATION_ANIMATION_SPEED = 12


def register_fonts(font_dir):
    """Return the bundled Rajdhani font paths (Pygame loads fonts explicitly)."""
    return {
        "regular": str(Path(font_dir) / "Rajdhani-Regular.ttf"),
        "bold": str(Path(font_dir) / "Rajdhani-Bold.ttf"),
    }


def _font(fonts, size, bold=False):
    path = fonts["bold" if bold else "regular"]
    try:
        return pygame.font.Font(path, max(1, round(size)))
    except (FileNotFoundError, pygame.error):
        return pygame.font.SysFont("sans", max(1, round(size)), bold=bold)


def _color(rgb):
    return tuple(max(0, min(255, round(channel * 255))) for channel in rgb)


def moon_image(phase, size):
    """Create a transparent moon surface, including its phase shadow."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    radius = size / 2 - 1
    angle = 2 * math.pi * phase
    for py in range(size):
        for px in range(size):
            x = (px - size / 2) / radius
            y = (py - size / 2) / radius
            if x * x + y * y <= 1:
                z = math.sqrt(max(0, 1 - x * x - y * y))
                if x * math.sin(angle) + z * math.cos(angle) > 0:
                    surface.set_at((px, py), (217, 217, 217, 255))
    pygame.draw.circle(surface, (0, 0, 0, 220), (size // 2, size // 2), round(radius), 2)
    return surface


def _draw_gradient(surface, color, seed):
    width, height = surface.get_size()
    base = tuple(color)
    variation = random.Random(seed)
    bottom = _color(tuple(max(0, min(1, value * variation.uniform(.82, .94))) for value in base))
    top = _color(tuple(max(0, min(1, value * variation.uniform(1.04, 1.18))) for value in base))
    for y in range(height):
        fraction = y / max(1, height - 1)
        current = tuple(round(bottom[i] + (top[i] - bottom[i]) * fraction) for i in range(3))
        pygame.draw.line(surface, current, (0, height - y - 1), (width, height - y - 1))


def _draw_stars(surface, score, rng):
    width, height = surface.get_size()
    for _ in range(round(120 * max(0, min(score, 100)) / 100)):
        x, y = rng.randrange(width), rng.randrange(height)
        radius = max(1, round(rng.uniform(1, 2.5)))
        color = (255, 244, 194, round(rng.uniform(100, 255)))
        star = pygame.Surface((radius * 2 + 1, radius * 2 + 1), pygame.SRCALPHA)
        pygame.draw.circle(star, color, (radius, radius), radius)
        surface.blit(star, (x - radius, y - radius))


def _load_image(path):
    data = Path(path).read_bytes()
    # The save icon is named .png for historical reasons, but its bytes are WebP.
    hint = "image.webp" if data[:4] == b"RIFF" and b"WEBP" in data[:16] else str(path)
    return pygame.image.load(BytesIO(data), hint).convert_alpha()


def _animate_observation(current, target, amount):
    def animate_angle(current_angle, target_angle):
        difference = (target_angle - current_angle + 180) % 360 - 180
        return current_angle + difference * amount

    time = current.time + (target.time - current.time) * amount
    return replace(
        target,
        time=time,
        readable_time=time.strftime("%I:%M %p").lstrip("0"),
        cloud_coverage=current.cloud_coverage
        + (target.cloud_coverage - current.cloud_coverage) * amount,
        coverage_fraction=current.coverage_fraction
        + (target.coverage_fraction - current.coverage_fraction) * amount,
        visibility_meters=current.visibility_meters
        + (target.visibility_meters - current.visibility_meters) * amount,
        stargaze_score=current.stargaze_score
        + (target.stargaze_score - current.stargaze_score) * amount,
        moon_phase=current.moon_phase
        + (target.moon_phase - current.moon_phase) * amount,
        moon_illumination=current.moon_illumination
        + (target.moon_illumination - current.moon_illumination) * amount,
        moon_altitude=current.moon_altitude
        + (target.moon_altitude - current.moon_altitude) * amount,
        moon_azimuth=animate_angle(current.moon_azimuth, target.moon_azimuth),
        sun_altitude=current.sun_altitude
        + (target.sun_altitude - current.sun_altitude) * amount,
        sun_azimuth=animate_angle(current.sun_azimuth, target.sun_azimuth),
        daylight_brightness=current.daylight_brightness
        + (target.daylight_brightness - current.daylight_brightness) * amount,
    )


def _draw_scene(observation, sprite_path, fonts, size):
    width, height = size
    background = lerp_color((.01, .02, .10), (.35, .70, .95),
                             observation.daylight_brightness)
    scene = pygame.Surface(size)
    _draw_gradient(scene, background, observation.time.date().toordinal())
    scale = width / 8
    sun_x = round(observation.sun_azimuth / 360 * width)
    sun_y = round(height - max(0, min(6, observation.sun_altitude / 90 * 6)) * scale)
    moon_x = round(observation.moon_azimuth / 360 * width)
    moon_y = round(height - max(0, min(6, observation.moon_altitude / 90 * 6)) * scale)
    if observation.sun_altitude > 0:
        pygame.draw.circle(scene, "#ffd34e", (sun_x, sun_y), round(scale * .45))
        pygame.draw.circle(scene, "#000000", (sun_x, sun_y), round(scale * .45), 2)
    if observation.moon_altitude > 0:
        moon = moon_image(observation.moon_phase, round(scale * .9))
        scene.blit(moon, (moon_x - moon.get_width() // 2, moon_y - moon.get_height() // 2))

    scene.blit(_draw_atmosphere(observation, sprite_path, size), (0, 0))
    _draw_scene_details(scene, observation, fonts, scale, width)
    return scene


def _draw_atmosphere(observation, sprite_path, size):
    width, height = size
    timestamp = observation.time.timestamp()
    atmosphere = pygame.Surface(size, pygame.SRCALPHA)
    _draw_stars(
        atmosphere,
        observation.stargaze_score,
        random.Random(observation.time.date().toordinal()),
    )
    scale = width / 8
    cloud = _load_image(sprite_path)
    cloud_rng = random.Random(observation.time.date().toordinal())
    horizontal_offset = timestamp * CLOUD_DRIFT_SPEED
    positions = [(x, y) for x in range(8) for y in range(6)]
    cloud_rng.shuffle(positions)
    for x, y in positions[:round(len(positions) * observation.coverage_fraction)]:
        cloud_size = round(scale)
        sprite = pygame.transform.smoothscale(cloud, (cloud_size, cloud_size))
        sprite.set_alpha(round(cloud_rng.uniform(.55, 1) * 255))
        sprite = pygame.transform.rotate(sprite, cloud_rng.uniform(-12, 12))
        left = round(
            ((x + cloud_rng.uniform(-.15, .15) + horizontal_offset) % 8) * scale
        )
        top = round(height - (y + 1 + cloud_rng.uniform(-.15, .15)) * scale)
        atmosphere.blit(sprite, (left, top))
    return atmosphere


def _draw_scene_details(scene, observation, fonts, scale, width):
    regular = _font(fonts, width / 72)
    bold = _font(fonts, width / 72, True)
    panel = pygame.Surface((round(3.35 * scale), round(2.48 * scale)), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 140))
    scene.blit(panel, (-round(.05 * scale), round(.28 * scale)))
    rows = (
        (f"Time ({TIMEZONE})", f"{observation.time.day} {observation.time:%b} @ {observation.readable_time}"),
        ("Cloud coverage", f"{observation.cloud_coverage:.0f}%"),
        ("Visibility", observation.visibility),
        ("Moon illumination", f"{observation.moon_illumination:.0f}%"),
        ("Moon altitude", f"{observation.moon_altitude:.1f}°"),
        ("Moon phase", observation.moon_name),
    )
    for row, (label, value) in enumerate(rows):
        y = round((.43 + row * .25) * scale)
        scene.blit(regular.render(label + ":", True, "white"), (round(.05 * scale), y))
        scene.blit(regular.render(value, True, "#bfbfbf"), (round(2.15 * scale), y))
    scene.blit(regular.render("Not considered:", True, "white"), (round(.05 * scale), round(1.98 * scale)))
    scene.blit(regular.render("Light pollution, target altitude", True, "#bfbfbf"), (round(.05 * scale), round(2.23 * scale)))

    score = observation.stargaze_score
    score_panel = pygame.Surface((round(2.2 * scale), round(.68 * scale)), pygame.SRCALPHA)
    score_panel.fill((0, 0, 0, 165))
    scene.blit(score_panel, (-round(.05 * scale), round(5.24 * scale)))
    scene.blit(bold.render("Chance of good stargazing:", True, "white"), (round(.05 * scale), round(5.35 * scale)))
    score_color = "#43d17a" if score >= 50 else "#ff5c5c"
    scene.blit(bold.render(f"{score:.0f}%", True, score_color), (round(1.85 * scale), round(5.35 * scale)))
    if score < 50:
        scene.blit(regular.render(score_explanation(observation), True, "#bfbfbf"), (round(.05 * scale), round(5.58 * scale)))
    return scene


def score_explanation(observation):
    if observation.sun_altitude >= 0:
        return "Daylight"
    if observation.cloud_coverage >= 70:
        return "Heavy cloud cover"
    if observation.visibility_meters < 5000:
        return "Poor visibility"
    if observation.moon_illumination >= 70 and observation.moon_altitude > 0:
        return "Bright moonlight"
    return "Limited conditions"


def render(observations, sprite_path, font_dir, output_path, initial_index=0):
    """Show the interactive viewer and save the selected scene on request."""
    pygame.init()
    pygame.font.init()
    fonts = register_fonts(font_dir)
    desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]
    window = pygame.display.set_mode(
        (min(1280, desktop_width), min(960, desktop_height)),
        pygame.RESIZABLE,
    )
    pygame.display.set_caption("Stargazing sky")
    clock = pygame.time.Clock()
    index = max(0, min(initial_index, len(observations) - 1))
    displayed_observation = observations[index]
    save_icon_path = Path(sprite_path).with_name("icon_save.png")
    try:
        icon = _load_image(save_icon_path)
    except pygame.error:
        icon = None
    dragging_slider = False

    def set_index(new_index):
        nonlocal index
        new_index = max(0, min(new_index, len(observations) - 1))
        index = new_index

    def update_slider(position):
        width, height = window.get_size()
        scene_height = min(height - 90, round(width * 3 / 4))
        scene_width = round(scene_height * 4 / 3)
        left = (width - scene_width) // 2
        if scene_width:
            fraction = max(0, min(1, (position[0] - left) / scene_width))
            set_index(round(fraction * (len(observations) - 1)))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
                set_index(index - 1)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                set_index(index + 1)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                width, height = window.get_size()
                scene_height = min(height - 90, round(width * 3 / 4))
                scene_width = round(scene_height * 4 / 3)
                left = (width - scene_width) // 2
                if height - 75 <= event.pos[1] <= height - 25 and scene_width:
                    dragging_slider = True
                    update_slider(event.pos)
                elif width - 110 <= event.pos[0] <= width - 25 and height - 75 <= event.pos[1] <= height - 15:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    image = _draw_scene(observations[index], sprite_path, fonts, (1600, 1200))
                    pygame.image.save(image, str(output_path))
                    print(f"saved {output_path}")
            elif event.type == pygame.MOUSEMOTION and dragging_slider:
                update_slider(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                dragging_slider = False
        width, height = window.get_size()
        scene_height = min(height - 90, round(width * 3 / 4))
        scene_width = round(scene_height * 4 / 3)
        scene_size = (scene_width, scene_height)
        elapsed = clock.tick(60) / 1000
        animation_amount = 1 - math.exp(
            -OBSERVATION_ANIMATION_SPEED * elapsed
        )
        displayed_observation = _animate_observation(
            displayed_observation,
            observations[index],
            animation_amount,
        )
        scene = _draw_scene(displayed_observation, sprite_path, fonts, scene_size)
        window.fill("#111111")
        left = (width - scene_width) // 2
        window.blit(scene, (left, 0))
        pygame.draw.line(window, "#777777", (left, height - 50), (left + scene_width, height - 50), 4)
        knob = left + round(scene_width * index / max(1, len(observations) - 1))
        pygame.draw.circle(window, "#43d17a", (knob, height - 50), 9)
        font = _font(fonts, 18)
        window.blit(
            font.render(displayed_observation.readable_time, True, "white"),
            (left, height - 85),
        )
        if icon:
            button = pygame.transform.smoothscale(icon, (42, 42))
            window.blit(button, (width - 82, height - 70))
        pygame.display.flip()
    pygame.quit()
