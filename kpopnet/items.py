import base64
import hashlib
from typing import TypedDict, Optional, Sequence, Mapping, NotRequired


# NOTE(Kagami): Should match with types in kpopnet/items.py!
class Idol(TypedDict):
    # required
    id: str
    name: str
    name_original: str
    real_name: str
    real_name_original: str
    birth_date: str
    urls: list[str]
    # optional
    debut_date: Optional[str]
    height: Optional[float]
    weight: Optional[float]
    thumb_url: Optional[str]
    # references
    groups: list[str]
    # tmp key
    _groups: NotRequired[list[dict]]


class GroupMember(TypedDict):
    id: str
    current: bool
    roles: Optional[str]


class Group(TypedDict):
    # required
    id: str
    name: str
    name_original: str
    agency_name: str
    urls: list[str]
    # optional
    debut_date: Optional[str]
    disband_date: Optional[str]
    thumb_url: Optional[str]
    # references
    members: list[GroupMember]


class Profiles(TypedDict):
    groups: list[Group]
    idols: list[Idol]


class Override(TypedDict):
    match: dict
    update: dict


class Overrides(TypedDict):
    idols: list[Override]
    groups: list[Override]


# Runtime validation/data fixes
class Validator:
    REQUIRED_FIELDS = []
    OPTIONAL_FIELDS = []
    OTHER_FIELDS = []
    UNIQUE_FIELDS = []

    @classmethod
    def normalize(cls, item: dict, overrides: list[Override]):
        for override in overrides:
            matched = all(item[k] == v for k, v in override["match"].items())
            if matched:
                item.update(override["update"])
                break
        for field in cls.REQUIRED_FIELDS:
            assert item.get(field), (field, item)
        for field in cls.OPTIONAL_FIELDS:
            if field not in item:
                item[field] = None
        item["id"] = cls.gen_id(item)

    @staticmethod
    def hash(s: str) -> str:
        hash = hashlib.blake2b(s.encode(), digest_size=15).digest()
        return base64.b64encode(hash, b"-_").decode()

    @classmethod
    def gen_id(cls, item: dict) -> str:
        raise NotImplementedError

    # TODO: validate types, regular expression
    @classmethod
    def validate(cls, item: Mapping):
        allowed_fields = set(
            cls.REQUIRED_FIELDS + cls.OPTIONAL_FIELDS + cls.OTHER_FIELDS + ["id"]
        )
        current_fields = set(item.keys())
        assert allowed_fields == current_fields, (allowed_fields, current_fields)

    @classmethod
    def validate_unique_fields(cls, items: Sequence[Mapping], fields: list[str]):
        seen = dict((field, dict()) for field in fields)
        for item in items:
            for field in fields:
                value = item[field]
                assert value not in seen[field], (item, seen[field][value])
                seen[field][value] = item

    @classmethod
    def validate_all(cls, items: Sequence[Mapping]):
        for item in items:
            cls.validate(item)
        # TODO: validate id cross-reference?
        cls.validate_unique_fields(items, cls.UNIQUE_FIELDS + ["id"])


class IdolValidator(Validator):
    REQUIRED_FIELDS = [
        "name",
        "name_original",
        "real_name",
        "real_name_original",
        "birth_date",
        "urls",
    ]
    OPTIONAL_FIELDS = ["debut_date", "height", "weight", "thumb_url"]
    OTHER_FIELDS = ["groups"]

    @classmethod
    def gen_id(cls, item: Idol) -> str:
        return cls.hash(item["real_name_original"] + item["birth_date"])


class GroupValidator(Validator):
    REQUIRED_FIELDS = ["name", "name_original", "agency_name", "urls"]
    OPTIONAL_FIELDS = ["debut_date", "disband_date", "thumb_url"]
    OTHER_FIELDS = ["members"]
    UNIQUE_FIELDS = ["name", "name_original"]

    @classmethod
    def gen_id(cls, item: Group) -> str:
        return cls.hash(item["name_original"])
