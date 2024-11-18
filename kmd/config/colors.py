from types import SimpleNamespace

from colour import Color


def hsl_to_hex(hsl_string: str) -> str:
    """
    Convert an HSL string to an RGB hex string.
    "hsl(134, 43%, 60%)" -> "#6dbd6d"
    """
    hsl_values = hsl_string.replace("hsl(", "").replace(")", "").replace("%", "").split(",")
    hue, saturation, lightness = (float(value.strip()) for value in hsl_values)

    saturation /= 100
    lightness /= 100

    color = Color(hsl=(hue / 360, saturation, lightness))
    return color.hex_l


# Dark terminal colors.
terminal_dark = SimpleNamespace(
    foreground="#fff",
    background="#000",
    # Based on:
    # https://rootloops.sh?sugar=8&colors=7&sogginess=5&flavor=2&fruit=9&milk=1
    # Some tools only like hex colors so convert them at once.
    # black
    black_dark=hsl_to_hex("hsl(0, 0%, 10%)"),
    black_light=hsl_to_hex("hsl(0, 0%, 73%)"),
    black_lighter=hsl_to_hex("hsl(0, 0%, 90%)"),
    # red
    red_dark=hsl_to_hex("hsl(7, 73%, 72%)"),
    red_light=hsl_to_hex("hsl(7, 87%, 85%)"),
    red_lighter=hsl_to_hex("hsl(7, 95%, 94%)"),
    # green
    green_dark=hsl_to_hex("hsl(134, 43%, 60%)"),
    green_light=hsl_to_hex("hsl(134, 53%, 73%)"),
    green_lighter=hsl_to_hex("hsl(134, 70%, 90%)"),
    # yellow
    yellow_dark=hsl_to_hex("hsl(44, 54%, 55%)"),
    yellow_light=hsl_to_hex("hsl(44, 74%, 76%)"),
    yellow_lighter=hsl_to_hex("hsl(44, 80%, 90%)"),
    # blue
    blue_dark=hsl_to_hex("hsl(225, 71%, 76%)"),
    blue_light=hsl_to_hex("hsl(225, 86%, 88%)"),
    blue_lighter=hsl_to_hex("hsl(225, 90%, 94%)"),
    # magenta
    magenta_dark=hsl_to_hex("hsl(305, 54%, 71%)"),
    magenta_light=hsl_to_hex("hsl(305, 68%, 85%)"),
    magenta_lighter=hsl_to_hex("hsl(305, 96%, 95%)"),
    # cyan
    cyan_dark=hsl_to_hex("hsl(188, 58%, 57%)"),
    cyan_light=hsl_to_hex("hsl(188, 52%, 76%)"),
    cyan_lighter=hsl_to_hex("hsl(188, 52%, 92%)"),
    # white
    white_dark=hsl_to_hex("hsl(240, 6%, 87%)"),
    white_light=hsl_to_hex("hsl(240, 6%, 94%)"),
    white_lighter=hsl_to_hex("hsl(240, 6%, 98%)"),
    # Additional colors.
    border=hsl_to_hex("hsl(231, 17%, 16%)"),
    cursor=hsl_to_hex("hsl(305, 84%, 68%)"),
    selection="hsla(305, 32%, 82%, 0.50)",
    input=hsl_to_hex("hsl(305, 92%, 95%)"),
    input_form=hsl_to_hex("hsl(188, 52%, 76%)"),
)

# Only support dark terminal colors for now.
terminal = terminal_dark

# Web light colors.
web_light = SimpleNamespace(
    primary="#488189",
    primary_light="#79bbc5",
    secondary="#6b7280",
    bg="#f3f4f6",
    text="#111827",
    hover="#d1d5db",
    hover_bg="#eff0f1",
    hint="#9ca3af",
)

# Only support light web colors for now.
web = web_light

# Logical colors
logical = SimpleNamespace(
    concept_dark=terminal.green_dark,
    concept_light=terminal.green_light,
    concept_lighter=terminal.green_lighter,
    doc_dark=terminal.blue_dark,
    doc_light=terminal.blue_light,
    doc_lighter=terminal.blue_lighter,
    resource_dark=terminal.cyan_dark,
    resource_light=terminal.cyan_light,
    resource_lighter=terminal.cyan_lighter,
    link_dark=terminal.yellow_dark,
    link_light=terminal.yellow_light,
    link_lighter=terminal.yellow_lighter,
    other=terminal.white_dark,
    other_light=terminal.white_light,
    other_lighter=terminal.white_lighter,
)


def generate_css_variables():
    """
    Generate CSS variables for the terminal and web colors.
    """

    css_variables = ":root {\n"

    # var(--red_dark), etc.
    for name, value in terminal.__dict__.items():
        css_var_name = name.replace("_", "-")
        css_variables += f"  --{css_var_name}: {value};\n"

    # var(--color-primary), var(--color-primary-light), etc.
    for name, value in {**web.__dict__, **logical.__dict__}.items():
        css_var_name = "color-" + name.replace("_", "-")
        css_variables += f"  --{css_var_name}: {value};\n"

    css_variables += "}"

    return css_variables


if __name__ == "__main__":
    print(generate_css_variables())
