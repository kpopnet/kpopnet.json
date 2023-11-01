import base64
import hashlib
from typing import TypedDict


class Override(TypedDict):
    match: dict
    update: dict


class Overrides(TypedDict):
    idols: list[Override]
    groups: list[Override]


# TODO(Kagami): use dataclass instead for proper field typing?
class Item(dict):
    REQUIRED_FIELDS = []
    OPTIONAL_FIELDS = []
    OTHER_FIELDS = []

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
        self["id"] = self.gen_id()

    # TODO: validate types, regular expression
    def validate(self):
        allowed_fields = set(
            self.REQUIRED_FIELDS + self.OPTIONAL_FIELDS + self.OTHER_FIELDS + ["id"]
        )
        current_fields = set(self.keys())
        assert allowed_fields == current_fields, (allowed_fields, current_fields)

    @staticmethod
    def hash(s: str) -> str:
        hash = hashlib.blake2b(s.encode(), digest_size=9).digest()
        return base64.b64encode(hash, b"-_").decode()

    def gen_id(self) -> str:
        raise NotImplementedError


# NOTE(Kagami): Should match with types in kpopnet.d.ts!
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
    OTHER_FIELDS = ["groups"]

    def gen_id(self):
        return self.hash(self["real_name_original"] + self["birth_date"])


class GroupMember(TypedDict):
    id: str
    current: bool
    roles: str | None


class Group(Item):
    REQUIRED_FIELDS = ["name", "name_original", "agency_name", "urls"]
    OPTIONAL_FIELDS = ["debut_date", "disband_date"]
    OTHER_FIELDS = ["members"]

    def gen_id(self):
        return self.hash(self["name_original"])


class Profiles(TypedDict):
    groups: list[Group]
    idols: list[Idol]
