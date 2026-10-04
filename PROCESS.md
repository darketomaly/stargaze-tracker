# Process

<!-- Same as assignment 1, same honesty. Which tools you used and for what; one
thing you kept and why it was good; one thing you rejected and why it was wrong.
"I did not use any" is fine if it is true.

If a model wrote most of plot.py, which is likely and allowed, the interesting part
is what you had to correct: did it invent a column name, use pandas where a list
would do, silently drop the rows it could not parse? -->

## Tools

Rider chat with Copilot for coding and Gemini for some sprite generation.

## Kept

Funny enough I first studied Environmental Engineering (dropped half way), but I am terrible at understanding complex biological and astronomical phenomenoms. I kept the interpretations that were generated from known data. For example, you don't need an API to tell you the moon phase, this can be calculated locally.

## Rejected

At first, since the idea was to visualize data, Matplotlib was used. But this was awful. It ran very slow for artistic interpretations and it felt like trying to use a real life car with a gamepad. Sounds good but doesn't work. I ended up using pygame instead.

Sometimes things are thrown from a prompt that removes previous features, introduces bugs or does not consider proper code architecture. I often reject AI code and be more explicit regarding it. For example, the entire code was being written in plot.py without proper methods or separate files.
