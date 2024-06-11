import os
from dataclasses import asdict, dataclass
from typing import List, Optional
from kmd.file_storage.workspaces import current_workspace
from kmd.file_storage.yaml_util import read_yaml_file, to_yaml_string, write_yaml_file
from kmd.model.items_model import Format, Item, ItemType
from kmd.model.locators import StorePath
from kmd.util.type_utils import as_dataclass, not_none
from kmd.web_gen.template_render import render_web_template


@dataclass
class TabInfo:
    label: str
    id: Optional[str] = None
    content_html: Optional[str] = None
    store_path: Optional[str] = None


@dataclass
class TabbedWebpage:
    title: str
    tabs: List[TabInfo]


def _fill_in_ids(tabs: List[TabInfo]):
    for i, tab in enumerate(tabs):
        if not tab.id:
            tab.id = f"tab_{i}"


def configure_webpage(title: str, items: List[Item]) -> Item:
    """
    Get an item with the config for a tabbed web page.
    """
    for item in items:
        if not item.store_path:
            raise ValueError(f"Item has no store_path: {item}")

    tabs = [
        TabInfo(label=item.abbrev_title(max_len=20), store_path=item.store_path) for item in items
    ]
    _fill_in_ids(tabs)
    config = TabbedWebpage(title=title, tabs=tabs)

    config_item = Item(
        title=f"Config for {title}",
        type=ItemType.config,
        format=Format.yaml,
        body=to_yaml_string(asdict(config)),
    )

    return config_item


def _load_tab_content(config: TabbedWebpage):
    """
    Load the content for each tab.
    """
    for tab in config.tabs:
        html = current_workspace().load(StorePath(not_none(tab.store_path))).body_as_html()
        tab.content_html = html


def generate_webpage(config_item: Item) -> str:
    """
    Generate a web page using the supplied config.
    """
    config = config_item.read_as_config()
    tabbed_webpage = as_dataclass(config, TabbedWebpage)  # Checks the format.

    _load_tab_content(tabbed_webpage)
    return render_web_template("tabbed_webpage.template.html", asdict(tabbed_webpage))


## Tests


def test_render():
    config = TabbedWebpage(
        title="An Elegant Web Page",
        tabs=[
            TabInfo(
                label="Home <escaped HTML chars>",
                content_html="Welcome to the home page! confirming <b>this is HTML</b>",
            ),
            TabInfo(label="Profile", content_html="This is the profile page."),
            TabInfo(label="Contact", content_html="This is the contact page."),
        ],
    )

    os.makedirs("tmp", exist_ok=True)
    write_yaml_file(asdict(config), "tmp/webpage_config.yaml")
    print("\nWrote config to tmp/webpage_config.yaml")

    # Check config reads correctly.
    new_config = as_dataclass(read_yaml_file("tmp/webpage_config.yaml"), TabbedWebpage)
    assert new_config == config

    html = render_web_template(
        "tabbed_webpage.template.html",
        asdict(config),
    )
    with open("tmp/webpage.html", "w") as f:
        f.write(html)
    print("Rendered tabbed webpage to tmp/webpage.html")

    lines = open("tmp/webpage.html", "r").readlines()
    assert any("Home &lt;escaped HTML chars&gt;" in line for line in lines)
    assert any("<b>this is HTML</b>" in line for line in lines)
