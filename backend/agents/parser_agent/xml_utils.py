from pathlib import Path
from xml.etree import ElementTree
from xml.etree.ElementTree import Element


def parse_xml_file(path: Path) -> Element:
    parser = ElementTree.XMLParser()
    tree = ElementTree.parse(path, parser=parser)
    return tree.getroot()


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def iter_by_local_name(root: Element, name: str) -> list[Element]:
    return [element for element in root.iter() if local_name(element.tag) == name]


def first_attr(element: Element, *names: str) -> str | None:
    for name in names:
        value = element.attrib.get(name)
        if value not in {None, ""}:
            return value
    return None


def bool_attr(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}
