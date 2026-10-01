# Process

<!-- Same as assignment 1, same honesty. Which tools you used and for what; one
thing you kept and why it was good; one thing you rejected and why it was wrong.
"I did not use any" is fine if it is true.

If a model wrote most of plot.py, which is likely and allowed, the interesting part
is what you had to correct: did it invent a column name, use pandas where a list
would do, silently drop the rows it could not parse? -->

## Tools

Matplotlib draws the generated picture, and the Rajdhani font files from Google Fonts
are bundled in `fonts/` so the output is consistent across machines.

The plotting code is separated into `plot.py` for orchestration, `plot_data.py` for
loading and preparing the observation, and `plot_render.py` for drawing the scene
and panels.

## Kept

Rajdhani was kept because its compact, geometric letterforms fit the space-themed
image while remaining readable at the small annotation sizes.

## Rejected
