# Shooting star probability index

<!-- To do: Add picture preview here -->

## The phenomenon

<!-- What goes up and down, and why you looked at it. -->

Meteor shower active dates, moon phase/illumination percentage and local cloud cover percentage.  

## The source

<!-- A link to the page or endpoint the file came from, and one line on what is in
the file: how many rows, what a row means, what the units are. -->

Data via Open-meteo weather API.

## What the picture shows

<!-- Two or three sentences. Including what it hides: every transformation throws
something away, and naming what yours threw away is the easiest way to sound like
you know what you did. -->

Chance of good stargazing and a preview of the sky. This percentage is an index
based on visibility, cloud cover and moonlight; it is not a measured probability.
For example, if it's cloudy, it will show clouds.

The generated picture uses the [Rajdhani](https://fonts.google.com/specimen/Rajdhani)
font from Google Fonts for its text.

## Run it

```
uv run fetch.py
uv run plot.py
```