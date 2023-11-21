import base64
import hashlib
from typing import TypedDict, Optional, Sequence, Mapping, NotRequired


# NOTE(Kagami): Should match with types in kpopnet.d.ts!
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
    name_alias: Optional[str]
    debut_date: Optional[str]
    height: Optional[float]
    weight: Optional[float]
    thumb_url: Optional[str]
    # references
    groups: list[str]
    # tmp key
    _groups: NotRequired[list[dict]]


class GroupMember(TypedDict):
    idol_id: str
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
    name_alias: Optional[str]
    debut_date: Optional[str]
    disband_date: Optional[str]
    thumb_url: Optional[str]
    # references
    members: list[GroupMember]
    parent_id: Optional[str]


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
    def override_urls(cls, item: dict, update: dict):
        url_keys = []
        for key in update:
            if key.startswith("urls"):
                url_keys.append(key)
        if not url_keys:
            return

        for key in url_keys:
            val = update.pop(key)
            idx = int(key[5:-1])  # urls[x] -> x
            # FIXME(Kagami): kpopnet url is inserted later
            item["urls"][idx - 1] = val
        return update

    @classmethod
    def normalize(cls, item: dict, overrides: list[Override]):
        for override in overrides:
            matched = all(item[k] == v for k, v in override["match"].items())
            if matched:
                override_update = override["update"].copy()
                cls.override_urls(item, override_update)
                item.update(override_update)
                break
        for field in cls.REQUIRED_FIELDS:
            assert item.get(field), (field, item)
        for field in cls.OPTIONAL_FIELDS:
            if field not in item:
                item[field] = None
        item["id"] = cls.gen_id(item)
        item["urls"].insert(0, cls.get_kpopnet_url(item))
        # TODO: overrides by id here?

    @staticmethod
    def hash(s: str) -> str:
        hash = hashlib.blake2b(s.encode(), digest_size=15).digest()
        return base64.b64encode(hash, b"-_").decode()

    @classmethod
    def gen_id(cls, item: dict) -> str:
        raise NotImplementedError

    @classmethod
    def get_kpopnet_url(cls, item: dict) -> str:
        return f"https://net.kpop.re/?id={item['id']}"

    # TODO: validate types, regular expression
    @classmethod
    def validate(cls, item: Mapping):
        allowed_fields = set(
            cls.REQUIRED_FIELDS + cls.OPTIONAL_FIELDS + cls.OTHER_FIELDS + ["id"]
        )
        current_fields = set(item.keys())
        assert allowed_fields == current_fields, (allowed_fields, current_fields)
        cls.validate_urls(item)

    @classmethod
    def validate_urls(cls, item: Mapping):
        assert 2 <= len(item["urls"]) <= 3, item
        assert item["urls"][0].startswith("https://net.kpop.re/?id="), item
        if "members" in item:
            assert item["urls"][1].startswith(
                "https://selca.kastden.org/noona/group/"
            ), item
        else:
            assert item["urls"][1].startswith(
                "https://selca.kastden.org/noona/idol/"
            ), item
        if len(item["urls"]) > 2:
            assert item["urls"][2].startswith("https://namu.wiki/w/"), item

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
    OPTIONAL_FIELDS = ["name_alias", "debut_date", "height", "weight", "thumb_url"]
    OTHER_FIELDS = ["groups"]

    @classmethod
    def gen_id(cls, item: Idol) -> str:
        return cls.hash(item["real_name_original"] + item["birth_date"])


class GroupValidator(Validator):
    REQUIRED_FIELDS = ["name", "name_original", "agency_name", "urls"]
    OPTIONAL_FIELDS = [
        "name_alias",
        "debut_date",
        "disband_date",
        "thumb_url",
        "parent_id",
    ]
    OTHER_FIELDS = ["members"]
    UNIQUE_FIELDS = ["name", "name_original"]

    @classmethod
    def gen_id(cls, item: Group) -> str:
        return cls.hash(item["name_original"])
