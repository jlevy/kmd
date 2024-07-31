# Based on:
# https://rootloops.sh?sugar=8&colors=7&sogginess=5&flavor=2&fruit=9&milk=1

# black
black_dark = "#1a1a1a"
black_light = "#bbbbbb"
black_lighter = "#e6e6e6"

# red
red_dark = "#ec9384"
red_light = "#fac1b7"
red_lighter = "#fbe8e5"

# green
green_dark = "#6cc581"
green_light = "#97dea7"
green_lighter = "#d5f4dc"


# yellow
yellow_dark = "#cbab4f"
yellow_light = "#efd795"
yellow_lighter = "#f4e9c9"

# blue
blue_dark = "#96abed"
blue_light = "#c1cdf0"
blue_lighter = "#dfe4f3"

# magenta
magenta_dark = "#dd8ed6"
magenta_light = "#e6cbe4"
magenta_lighter = "#fbe8f9"

# cyan
cyan_dark = "#54c0d1"
cyan_light = "#a2d9e2"
cyan_lighter = "#dff2f5"

# white
white_dark = "#dddde1"
white_light = "#eeeef0"
white_lighter = "#ffffff"


# Logical colors

concept_dark = green_dark
concept_light = green_light
concept_lighter = green_lighter

note_dark = blue_dark
note_light = blue_light
note_lighter = blue_lighter

resource_dark = cyan_dark
resource_light = cyan_light
resource_lighter = cyan_lighter

link_dark = yellow_dark
link_light = yellow_light
link_lighter = yellow_lighter


def generate_css_variables():
    css_variables = ":root {\n"
    for name, value in globals().items():
        if not name.startswith("__"):
            css_var_name = name.replace("_", "-")
            css_variables += f"  --{css_var_name}: {value};\n"
    css_variables += "}"

    return css_variables


if __name__ == "__main__":
    print(generate_css_variables())
