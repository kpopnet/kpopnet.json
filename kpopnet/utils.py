from urllib.parse import unquote
from typing import Sequence, Mapping, Optional


def unquote_no_space(url: str) -> str:
    url = unquote(url)
    # for convenient ctrl+click from terminal
    return url.replace(" ", "%20")


def find_by_field(
    items: Sequence[Mapping], field: str, value: str
) -> Optional[Mapping]:
    for item in items:
        if item[field] == value:
            return item
    return None
