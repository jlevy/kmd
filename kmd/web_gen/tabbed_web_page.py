import os
from dataclasses import asdict, dataclass
from typing import List, Optional
from kmd.file_storage.yaml_util import read_yaml_file, to_yaml_string, write_yaml_file
from kmd.model.items_model import Format, Item, ItemType
from kmd.util.type_utils import as_dataclass, not_none
from kmd.web_gen.template_render import render_web_template


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


def _fill_in_ids(tabs: List[TabInfo]):
    for i, tab in enumerate(tabs):
        if not tab.id:
            tab.id = f"tab_{i}"


def configure_web_page(title: str, items: List[Item]) -> Item:
    """
    Get an item with the config for a tabbed web page.
    """
    for item in items:
        if not item.store_path:
            raise ValueError(f"Item has no store_path: {item}")

    tabs = [TabInfo(label=item.get_title(max_len=20), store_path=item.store_path) for item in items]
    _fill_in_ids(tabs)
    config = TabbedWebPage(title=title, tabs=tabs)

    config_item = Item(
        title=f"Config for {title}",
        type=ItemType.config,
        format=Format.yaml,
        body=to_yaml_string(asdict(config)),
    )

    return config_item


def generate_web_page(config_item: Item) -> str:
    """
    Generate a web page using the supplied config.
    """
    if config_item.type != ItemType.config:
        raise ValueError(f"Expected a config item, got: {config_item}")
    config = read_yaml_file(not_none(config_item.store_path))
    config = asdict(as_dataclass(config, TabbedWebPage))  # Check the format.
    return render_web_template(
        "tabbed_web_page.template.html",
        config,
    )


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
    write_yaml_file(asdict(config), "tmp/web_page_config.yaml")
    print("Wrote config to tmp/web_page_config.yaml")

    # Check config reads correctly.
    new_config = as_dataclass(read_yaml_file("tmp/web_page_config.yaml"), TabbedWebPage)
    assert new_config == config

    html = render_web_template(
        "tabbed_web_page.template.html",
        asdict(config),
    )
    with open("tmp/web_page.html", "w") as f:
        f.write(html)

    print("Rendered tabbed web_page to tmp/web_page.html")

    lines = open("tmp/web_page.html", "r").readlines()
    assert any("&lt;HTML escaping works&gt;" in line for line in lines)
