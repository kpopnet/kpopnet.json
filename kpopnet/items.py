import base64
import hashlib
from typing import TypedDict


class Overrides(TypedDict):
    idols: list[dict]
    groups: list[dict]


class Item(dict):
    REQUIRED_FIELDS = []
    OPTIONAL_FIELDS = []
    OTHER_FIELDS = []

    def normalize(self, overrides: list[dict]):
        for override in overrides:
            matched = all(self[field] == override[field] for field in override["match"])
            if matched:
                for field, value in override.items():
                    if field != "match":
                        self[field] = value
                break
        for field in self.REQUIRED_FIELDS:
            assert self.get(field), (field, self)
        for field in self.OPTIONAL_FIELDS:
            if field not in self:
                self[field] = None
        allowed_fields = set(
            self.REQUIRED_FIELDS + self.OPTIONAL_FIELDS + self.OTHER_FIELDS
        )
        current_fields = set(self.keys())
        assert allowed_fields == current_fields, (allowed_fields, current_fields)


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
    OTHER_FIELDS = ["_groups"]

    def gen_id(self):
        s = self["real_name_original"] + self["birth_date"]
        hash = hashlib.md5(s.encode()).digest()
        return base64.b64encode(hash).decode().rstrip("=")

    def normalize(self, overrides: list[dict]):
        super().normalize(overrides)
        self["id"] = self.gen_id()


class Group(Item):
    REQUIRED_FIELDS = ["name", "name_original", "agency_name", "urls"]
    OPTIONAL_FIELDS = ["debut_date", "disband_date"]
