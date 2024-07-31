# Based on:
# https://rootloops.sh?sugar=8&colors=7&sogginess=5&flavor=2&fruit=9&milk=1

# black
black_dark = "hsl(0, 0%, 10%)"
black_light = "hsl(0, 0%, 73%)"
black_lighter = "hsl(0, 0%, 90%)"

# red
red_dark = "hsl(7, 73%, 72%)"
red_light = "hsl(7, 87%, 85%)"
red_lighter = "hsl(7, 95%, 94%)"

# green
green_dark = "hsl(134, 43%, 60%)"
green_light = "hsl(134, 53%, 73%)"
green_lighter = "hsl(134, 70%, 90%)"

# yellow
yellow_dark = "hsl(44, 54%, 55%)"
yellow_light = "hsl(44, 74%, 76%)"
yellow_lighter = "hsl(44, 80%, 90%)"

# blue
blue_dark = "hsl(225, 71%, 76%)"
blue_light = "hsl(225, 86%, 88%)"
blue_lighter = "hsl(225, 90%, 94%)"

# magenta
magenta_dark = "hsl(305, 54%, 71%)"
magenta_light = "hsl(305, 68%, 85%)"
magenta_lighter = "hsl(305, 96%, 95%)"

# cyan
cyan_dark = "hsl(188, 58%, 57%)"
cyan_light = "hsl(188, 52%, 76%)"
cyan_lighter = "hsl(188, 52%, 92%)"

# white
white_dark = "hsl(240, 6%, 87%)"
white_light = "hsl(240, 6%, 94%)"
white_lighter = "hsl(240, 6%, 98%)"

# Additional colors. These are compatible with terminal preferences too.

foreground = "#fff"
background = "#000"

border = "hsl(231, 17%, 16%)"

cursor = "hsl(305, 84%, 68%)"
selection = "hsla(305, 32%, 82%, 0.50)"

input = "#fee6fc"


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
