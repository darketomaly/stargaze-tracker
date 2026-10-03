"""Render a prepared observation as a stargazing picture with Pygame."""

import math
import os
import random
from io import BytesIO
from pathlib import Path

os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitor")

import pygame

from plot_data import TIMEZONE, lerp_color


CLOUD_DRIFT_PERIOD = 60 * 60
CLOUD_DRIFT_SPEED = 1 / CLOUD_DRIFT_PERIOD
STAR_DRIFT_PERIOD = 3 * 24 * 60 * 60
STAR_DRIFT_SPEED = 1 / STAR_DRIFT_PERIOD
STAR_CURVE = 0.035
CLOUD_CURVE = 0.07
UI_LEFT_PADDING = 0.15
SCENE_ANIMATION_DURATION = 0.45
STAR_SEED = 317


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
    illuminated = set()
    for py in range(size):
        for px in range(size):
            x = (px - size / 2) / radius
            y = (py - size / 2) / radius
            if x * x + y * y <= 1:
                z = math.sqrt(max(0, 1 - x * x - y * y))
                if x * math.sin(angle) + z * math.cos(angle) > 0:
                    illuminated.add((px, py))

    outline = set()
    for px, py in illuminated:
        for offset_x in (-1, 0, 1):
            for offset_y in (-1, 0, 1):
                neighbor = (px + offset_x, py + offset_y)
                if neighbor not in illuminated and (
                    0 <= neighbor[0] < size and 0 <= neighbor[1] < size
                ):
                    outline.add(neighbor)
    for px, py in outline:
        surface.set_at((px, py), (0, 0, 0, 220))
    for px, py in illuminated:
        surface.set_at((px, py), (217, 217, 217, 255))
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


def _interpolate_angle(start, end, fraction):
    difference = (end - start + 180) % 360 - 180
    return (start + difference * fraction) % 360


def _interpolate_wrapped(start, end, fraction, period):
    difference = (end - start + period / 2) % period - period / 2
    return start + difference * fraction


def _dome_offset(x, strength):
    """Return the inverted-U elevation for a wrapped screen position."""
    wrapped_x = x % 1
    return strength * 4 * wrapped_x * (1 - wrapped_x)


def _interpolate_observation(start, end, fraction):
    """Interpolate the visual values that change when the selected time changes."""
    fraction = max(0, min(1, fraction))
    time = start.time + (end.time - start.time) * fraction
    return start.__class__(
        time=time,
        readable_time=time.strftime("%I:%M %p").lstrip("0"),
        cloud_coverage=start.cloud_coverage + (end.cloud_coverage - start.cloud_coverage) * fraction,
        coverage_fraction=start.coverage_fraction + (end.coverage_fraction - start.coverage_fraction) * fraction,
        visibility=end.visibility if fraction >= .5 else start.visibility,
        visibility_meters=start.visibility_meters + (end.visibility_meters - start.visibility_meters) * fraction,
        stargaze_score=start.stargaze_score + (end.stargaze_score - start.stargaze_score) * fraction,
        moon_phase=_interpolate_wrapped(start.moon_phase, end.moon_phase, fraction, 1),
        moon_illumination=start.moon_illumination + (end.moon_illumination - start.moon_illumination) * fraction,
        moon_altitude=start.moon_altitude + (end.moon_altitude - start.moon_altitude) * fraction,
        moon_azimuth=_interpolate_angle(start.moon_azimuth, end.moon_azimuth, fraction),
        moon_name=end.moon_name if fraction >= .5 else start.moon_name,
        sun_altitude=start.sun_altitude + (end.sun_altitude - start.sun_altitude) * fraction,
        sun_azimuth=_interpolate_angle(start.sun_azimuth, end.sun_azimuth, fraction),
        daylight_brightness=start.daylight_brightness + (end.daylight_brightness - start.daylight_brightness) * fraction,
    )


def _load_image(path):
    data = Path(path).read_bytes()
    # The save icon is named .png for historical reasons, but its bytes are WebP.
    hint = "image.webp" if data[:4] == b"RIFF" and b"WEBP" in data[:16] else str(path)
    return pygame.image.load(BytesIO(data), hint).convert_alpha()


def _atmosphere_layout(observation):
    """Create stable star slots and slowly drifting cloud/star slots."""
    # Stars are decorative background points, not a new random field for each
    # observation. Keeping their identities fixed prevents visible shuffling
    # while their visibility changes with the stargazing score.
    star_rng = random.Random(STAR_SEED)
    stars = []
    for index in range(120):
        brightness = star_rng.uniform(100, 255)
        x = star_rng.random() + observation.time.timestamp() * STAR_DRIFT_SPEED
        y = star_rng.random()
        stars.append((
            x,
            y,
            max(1, round(star_rng.uniform(1, 2.5))),
            brightness
            if index < round(120 * max(0, min(observation.stargaze_score, 100)) / 100)
            else 0,
        ))

    cloud_rng = random.Random(observation.time.date().toordinal())
    positions = [(x, y) for x in range(8) for y in range(6)]
    cloud_rng.shuffle(positions)
    clouds = []
    for index, (x, y) in enumerate(positions):
        x = (x + cloud_rng.uniform(-.15, .15)) / 8
        x += observation.time.timestamp() * CLOUD_DRIFT_SPEED / 8
        y = (y + 1 + cloud_rng.uniform(-.15, .15)) / 6
        clouds.append((
            x,
            y,
            cloud_rng.uniform(.55, 1) * 255
            if index < round(len(positions) * observation.coverage_fraction)
            else 0,
            cloud_rng.uniform(-12, 12),
        ))
    return stars, clouds


def _draw_scene(
    observation,
    sprite_path,
    fonts,
    size,
    atmosphere_layout=None,
    ui_size=None,
):
    width, height = size
    ui_width = width if ui_size is None else ui_size[0]
    ui_scale = ui_width / 8
    background = lerp_color((.01, .02, .10), (.35, .70, .95),
                             observation.daylight_brightness)
    scene = pygame.Surface(size)
    _draw_gradient(scene, background, observation.time.date().toordinal())
    scale = min(width / 8, height / 6)
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

    if atmosphere_layout is not None:
        scene.blit(
            _draw_atmosphere(observation, sprite_path, size, atmosphere_layout),
            (0, 0),
        )
    _draw_scene_details(scene, observation, fonts, ui_scale, ui_width)
    return scene


def _draw_atmosphere(observation, sprite_path, size, layout=None):
    width, height = size
    atmosphere = pygame.Surface(size, pygame.SRCALPHA)
    if layout is None:
        layout = _atmosphere_layout(observation)
    stars, clouds = layout
    for x, y, radius, alpha in stars:
        if alpha:
            x %= 1
            y -= _dome_offset(x, STAR_CURVE)
            star = pygame.Surface((radius * 2 + 1, radius * 2 + 1), pygame.SRCALPHA)
            pygame.draw.circle(star, (255, 244, 194, round(alpha)), (radius, radius), radius)
            atmosphere.blit(star, (round(x * width) - radius, round(y * height) - radius))

    scale = min(width / 8, height / 6)
    cloud = _load_image(sprite_path)
    for x, y, alpha, angle in clouds:
        if not alpha:
            continue
        x %= 1
        y += _dome_offset(x, CLOUD_CURVE)
        y = 1 - y
        cloud_size = round(scale)
        sprite = pygame.transform.smoothscale(cloud, (cloud_size, cloud_size))
        sprite.set_alpha(round(alpha))
        sprite = pygame.transform.rotate(sprite, angle)
        atmosphere.blit(sprite, (
            round(x * width - sprite.get_width() / 2),
            round(y * height - sprite.get_height() / 2),
        ))
    return atmosphere


def _interpolate_layout(start, end, fraction):
    stars = [
        (
            start_star[0] + (end_star[0] - start_star[0]) * fraction,
            start_star[1] + (end_star[1] - start_star[1]) * fraction,
            start_star[2] if fraction < .5 else end_star[2],
            start_star[3] + (end_star[3] - start_star[3]) * fraction,
        )
        for start_star, end_star in zip(start[0], end[0])
    ]
    clouds = [
        (
            start_cloud[0] + (end_cloud[0] - start_cloud[0]) * fraction,
            start_cloud[1] + (end_cloud[1] - start_cloud[1]) * fraction,
            start_cloud[2] + (end_cloud[2] - start_cloud[2]) * fraction,
            start_cloud[3] + (end_cloud[3] - start_cloud[3]) * fraction,
        )
        for start_cloud, end_cloud in zip(start[1], end[1])
    ]
    return stars, clouds


def _draw_scene_details(scene, observation, fonts, scale, width):
    regular = _font(fonts, width / 72)
    bold = _font(fonts, width / 72, True)
    left_padding = round(UI_LEFT_PADDING * scale)
    panel = pygame.Surface((round(3.35 * scale), round(2.48 * scale)), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 140))
    scene.blit(panel, (left_padding - round(.05 * scale), round(.28 * scale)))
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
        scene.blit(regular.render(label + ":", True, "white"), (left_padding + round(.05 * scale), y))
        scene.blit(regular.render(value, True, "#bfbfbf"), (left_padding + round(2.15 * scale), y))
    scene.blit(regular.render("Not considered:", True, "white"), (left_padding + round(.05 * scale), round(1.98 * scale)))
    scene.blit(regular.render("Light pollution, target altitude", True, "#bfbfbf"), (left_padding + round(.05 * scale), round(2.23 * scale)))

    score = observation.stargaze_score
    score_panel = pygame.Surface((round(2.2 * scale), round(.68 * scale)), pygame.SRCALPHA)
    score_panel.fill((0, 0, 0, 165))
    scene.blit(score_panel, (left_padding - round(.05 * scale), round(5.24 * scale)))
    scene.blit(bold.render("Chance of good stargazing:", True, "white"), (left_padding + round(.05 * scale), round(5.35 * scale)))
    score_color = "#43d17a" if score >= 50 else "#ff5c5c"
    scene.blit(bold.render(f"{score:.0f}%", True, score_color), (left_padding + round(1.85 * scale), round(5.35 * scale)))
    if score < 50:
        scene.blit(regular.render(score_explanation(observation), True, "#bfbfbf"), (left_padding + round(.05 * scale), round(5.58 * scale)))
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
    animation_from = None
    animation_layout_from = None
    animation_layout_to = None
    animation_started = 0
    save_icon_path = Path(sprite_path).with_name("icon_save.png")
    try:
        icon = _load_image(save_icon_path)
    except pygame.error:
        icon = None
    dragging_slider = False
    slider_fraction = index / max(1, len(observations) - 1)

    def set_index(new_index):
        nonlocal index, animation_from, animation_layout_from
        nonlocal animation_layout_to, animation_started, slider_fraction
        new_index = max(0, min(new_index, len(observations) - 1))
        slider_fraction = new_index / max(1, len(observations) - 1)
        if new_index == index:
            return
        now = pygame.time.get_ticks()
        if animation_from is not None:
            fraction = min(
                1,
                (now - animation_started) / (SCENE_ANIMATION_DURATION * 1000),
            )
            current = _interpolate_observation(
                animation_from, observations[index], fraction
            )
            current_layout = _interpolate_layout(
                animation_layout_from,
                animation_layout_to,
                fraction,
            )
        else:
            current = observations[index]
            current_layout = _atmosphere_layout(current)
        animation_from = current
        animation_layout_from = current_layout
        animation_layout_to = _atmosphere_layout(observations[new_index])
        animation_started = now
        index = new_index

    def update_slider(position):
        nonlocal slider_fraction
        width, height = window.get_size()
        scene_height = min(height - 90, round(width * 3 / 4))
        scene_width = round(scene_height * 4 / 3)
        left = (width - scene_width) // 2
        if scene_width:
            fraction = max(0, min(1, (position[0] - left) / scene_width))
            set_index(round(fraction * (len(observations) - 1)))
            slider_fraction = fraction
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
                    image = _draw_scene(
                        observations[index],
                        sprite_path,
                        fonts,
                        (1600, 1200),
                        _atmosphere_layout(observations[index]),
                        (1600, 1200),
                    )
                    pygame.image.save(image, str(output_path))
                    print(f"saved {output_path}")
            elif event.type == pygame.MOUSEMOTION and dragging_slider:
                update_slider(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                dragging_slider = False
        width, height = window.get_size()
        slider_height = min(height - 90, round(width * 3 / 4))
        slider_width = round(slider_height * 4 / 3)
        slider_left = (width - slider_width) // 2
        scene_size = (width, height)
        ui_size = (slider_width, slider_height)
        if dragging_slider:
            update_slider(pygame.mouse.get_pos())
        now = pygame.time.get_ticks()
        if animation_from is not None:
            progress = min(
                1,
                (now - animation_started) / (SCENE_ANIMATION_DURATION * 1000),
            )
            displayed_observation = _interpolate_observation(
                animation_from, observations[index], progress
            )
            displayed_layout = _interpolate_layout(
                animation_layout_from,
                animation_layout_to,
                progress,
            )
            if progress >= 1:
                animation_from = None
                animation_layout_from = None
                animation_layout_to = None
        else:
            displayed_observation = observations[index]
            displayed_layout = _atmosphere_layout(displayed_observation)
        scene = _draw_scene(
            displayed_observation,
            sprite_path,
            fonts,
            scene_size,
            ui_size=ui_size,
        )
        atmosphere = _draw_atmosphere(
            displayed_observation,
            sprite_path,
            scene_size,
            displayed_layout,
        )
        window.fill("#111111")
        displayed_scene = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
        displayed_scene.blit(scene, (0, 0))
        displayed_scene.blit(atmosphere, (0, 0))
        window.blit(displayed_scene, (0, 0))
        pygame.draw.line(
            window,
            "#777777",
            (slider_left, height - 50),
            (slider_left + slider_width, height - 50),
            4,
        )
        knob = slider_left + round(slider_width * slider_fraction)
        pygame.draw.circle(window, "#A6192E", (knob, height - 50), 9)
        if icon:
            button = pygame.transform.smoothscale(icon, (42, 42))
            window.blit(button, (width - 82, height - 70))
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()
