from types import SimpleNamespace
from typing import Dict

from colour import Color


def hsl_to_hex(hsl_string: str) -> str:
    """
    Convert an HSL/HSLA string to an RGB hex string or RGBA value.
    "hsl(134, 43%, 60%)" -> "#6dbd6d"
    "hsla(220, 14%, 96%, 0.86)" -> "rgba(244, 245, 247, 0.86)"
    """
    is_hsla = hsl_string.startswith("hsla")
    hsl_values = (
        hsl_string.replace("hsla(", "")
        .replace("hsl(", "")
        .replace(")", "")
        .replace("%", "")
        .split(",")
    )

    if is_hsla:
        hue, saturation, lightness, alpha = (float(value.strip()) for value in hsl_values)
    else:
        hue, saturation, lightness = (float(value.strip()) for value in hsl_values)
        alpha = 1.0

    saturation /= 100
    lightness /= 100

    color = Color(hsl=(hue / 360, saturation, lightness))

    if alpha < 1:
        rgb = color.rgb
        return f"rgba({int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)}, {alpha})"
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
    input=hsl_to_hex("hsl(305, 92%, 95%)"),
    input_form=hsl_to_hex("hsl(188, 52%, 76%)"),
)

# Only support dark terminal colors for now.
terminal = terminal_dark

# Web light colors.
web_light = SimpleNamespace(
    primary=hsl_to_hex("hsl(188, 31%, 41%)"),
    primary_light=hsl_to_hex("hsl(188, 40%, 62%)"),
    secondary=hsl_to_hex("hsl(188, 12%, 38%)"),
    bg=hsl_to_hex("hsl(188, 14%, 96%)"),
    bg_translucent=hsl_to_hex("hsla(188, 12%, 84%, 0.95)"),
    bg_alt=hsl_to_hex("hsl(44, 28%, 90%)"),
    text=hsl_to_hex("hsl(188, 39%, 11%)"),
    hover=hsl_to_hex("hsl(188, 12%, 84%)"),
    hover_bg=hsl_to_hex("hsl(188, 7%, 94%)"),
    hint=hsl_to_hex("hsl(188, 11%, 65%)"),
    tooltip_bg=hsl_to_hex("hsla(44, 6%, 40%, 0.95)"),
    bright=hsl_to_hex("hsl(134, 43%, 60%)"),
    selection="hsla(225, 61%, 82%, 0.80)",
    scrollbar=hsl_to_hex("hsl(188, 12%, 55%)"),
    scrollbar_hover=hsl_to_hex("hsl(188, 12%, 38%)"),
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


def consolidate_color_vars(overrides: Dict[str, str] = {}) -> Dict[str, str]:
    """
    Consolidate all color variables into a single dictionary with appropriate prefixes.
    Terminal variables have no prefix, while web and logical variables have "color-" prefix.
    """
    return {
        # Terminal variables (no prefix)
        **terminal.__dict__,
        # Web and logical variables with "color-" prefix
        **{f"color-{k}": v for k, v in web.__dict__.items()},
        **{f"color-{k}": v for k, v in logical.__dict__.items()},
        # Overrides take precedence (assume they already have correct prefixes)
        **overrides,
    }


def normalize_var_names(variables: Dict[str, str]) -> Dict[str, str]:
    """
    Normalize variable names from Python style to CSS style.
    Example: color_bg -> color-bg
    """
    return {k.replace("_", "-"): v for k, v in variables.items()}


def generate_css_vars(overrides: Dict[str, str] = {}) -> str:
    """
    Generate CSS variables for the terminal and web colors.
    """
    normalized_vars = normalize_var_names(consolidate_color_vars(overrides))

    # Generate the CSS.
    css_variables = ":root {\n"
    for name, value in normalized_vars.items():
        css_variables += f"  --{name}: {value};\n"
    css_variables += "}"

    return css_variables


if __name__ == "__main__":
    print(generate_css_vars())
