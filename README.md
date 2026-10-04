# Chance of good stargazing

<!-- To do: Add picture preview here -->

<img width="800" height="373" alt="ezgif-7b616799b2abca39" src="https://github.com/user-attachments/assets/ea7feb67-6657-49c2-b1e4-a2c6b042fcf0" />

## The phenomenon

<!-- What goes up and down, and why you looked at it. -->

The scene changes over a 24-hour forecast: the sun and moon move according to their altitude and azimuth, the sky brightness transitions between day and night, cloud coverage and cloud positions change, and the stars gradually appear, fade, and drift across the sky. A day/night landscape overlay also fades between its daytime and nighttime versions. I looked at these changes to create an artistic visualization of how suitable the sky is for stargazing over time, rather than a conventional numerical chart.

## The source

<!-- A link to the page or endpoint the file came from, and one line on what is in
the file: how many rows, what a row means, what the units are. -->

The weather data comes from the Open-Meteo forecast API: https://api.open-meteo.com/v1/forecast?latitude=22.3193&longitude=114.1694&hourly=cloud_cover,visibility&daily=sunrise,sunset&forecast_days=1&timezone=Asia%2FHong_Kong

The generated CSV contains 24 hourly rows for Hong Kong: cloud cover (%) and visibility (metres) are hard data from the API; the stargazing score, moon phase, illumination, and sun/moon positions are interpreted from data and astronomical formulas.

I have separated the scripts by responsibilities. One is responsible for data handling, and one is responsible for its visuals. You still only need to run two scripts: One to fetch data and one to use it.

## What the picture shows

<!-- Two or three sentences. Including what it hides: every transformation throws
something away, and naming what yours threw away is the easiest way to sound like
you know what you did. -->

The plot script runs an interactive Pygame sky scene showing the current sun or moon, animated stars and clouds, a day/night landscape, sky brightness, and a panel containing the time, cloud coverage, visibility, moon information, and stargazing score. The slider allows the viewer to move through the hourly forecast, while the scene elements interpolate smoothly between nearby observations.<br><br>
There is also a save button that saves an image on the /out/ folder.<br><br>
All the values from the data do contribute either directly or indirectly (for interpretation) to the visualization (since the endpoint is flexible, you can choose to only query data that you really need), but the final visualization does ignore several things: it does not show the exact geographic horizon, real cloud formations, light pollution, or target altitude. The clouds and stars are stylized decorative sprites, and the stargazing score is calculated based on visibility, cloud cover, moonlight, and daylight, not a scientific probability.

## How to run it

```
uv run fetch.py
uv run plot.py
```
