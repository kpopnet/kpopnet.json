import base64
import hashlib
from typing import TypedDict


class Override(TypedDict):
    match: dict
    update: dict


class Overrides(TypedDict):
    idols: list[Override]
    groups: list[Override]


class Item(dict):
    REQUIRED_FIELDS = []
    OPTIONAL_FIELDS = []

    def normalize(self, overrides: list[Override]):
        for override in overrides:
            matched = all(self[k] == v for k, v in override["match"].items())
            if matched:
                self.update(override["update"])
                break
        for field in self.REQUIRED_FIELDS:
            assert self.get(field), (field, self)
        for field in self.OPTIONAL_FIELDS:
            if field not in self:
                self[field] = None


class Idol(Item):
    REQUIRED_FIELDS = [
        "name",
        "name_original",
        "real_name",
        "real_name_original",
        "birth_date",
        "urls",
    ]
    OPTIONAL_FIELDS = ["debut_date", "height", "weight"]

    def gen_id(self):
        s = self["real_name_original"] + self["birth_date"]
        hash = hashlib.blake2b(s.encode(), digest_size=8).digest()
        return base64.b64encode(hash, b"-_").decode().rstrip("=")

    def normalize(self, overrides: list[Override]):
        super().normalize(overrides)
        self["id"] = self.gen_id()


class Group(Item):
    REQUIRED_FIELDS = ["name", "name_original", "agency_name", "urls"]
    OPTIONAL_FIELDS = ["debut_date", "disband_date"]
