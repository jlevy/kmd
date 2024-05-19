from dataclasses import asdict, dataclass
import os
from typing import List, Optional
from strif import atomic_output_file
from kmd.file_storage.yaml_util import read_yaml_file, write_yaml
from kmd.util.type_utils import as_dataclass
from kmd.web_gen.template_writer import render_template


@dataclass
class TabInfo:
    label: str
    id: Optional[str] = None
    content: Optional[str] = None
    store_path: Optional[str] = None


@dataclass
class TabbedWebPage:
    title: str
    tabs: List[TabInfo]


def template_config(title: str, tabs: List[TabInfo]):
    for i, tab in enumerate(tabs):
        if not tab.id:
            tab.id = f"tab_{i}"
    return {
        "title": title,
        "tabs": tabs,
    }


def render(web_page_info: TabbedWebPage, output_path: str):
    render_template(
        "tabbed_web_page.template.html",
        output_path,
        template_config(web_page_info.title, web_page_info.tabs),
    )


def write_config(config: TabbedWebPage, output_path: str):
    with atomic_output_file(output_path) as f:
        with open(f, "w") as f:
            write_yaml(asdict(config), f)


## Tests


def test_render():
    config = TabbedWebPage(
        title="An Elegant Web Page",
        tabs=[
            TabInfo(
                label="Home", content="Welcome to the home page! confirming <HTML escaping works>"
            ),
            TabInfo(label="Profile", content="This is the profile page."),
            TabInfo(label="Contact", content="This is the contact page."),
        ],
    )

    os.makedirs("tmp", exist_ok=True)
    write_config(config, "tmp/web_page_config.yaml")
    print("Wrote config to tmp/web_page_config.yaml")

    # Check config reads correctly.
    new_config = as_dataclass(read_yaml_file("tmp/web_page_config.yaml"), TabbedWebPage)

    render(new_config, "tmp/web_page.html")
    print("Rendered tabbed web_page to tmp/web_page.html")

    lines = open("tmp/web_page.html", "r").readlines()
    assert any("&lt;HTML escaping works&gt;" in line for line in lines)
