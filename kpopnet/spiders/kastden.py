import os
import re
import io
import json
import hashlib
from pathlib import Path
from urllib.parse import unquote
from typing import cast
from contextlib import suppress

import scrapy
from scrapy.http import Response
from PIL import Image

from ..items import (
    Idol,
    Group,
    Profiles,
    Overrides,
    IdolValidator,
    GroupValidator,
)


class KastdenSpider(scrapy.Spider):
    name = "kastden"
    allowed_domains = ["selca.kastden.org"]
    start_urls = ["https://selca.kastden.org/noona/search/?pt=kpop"]

    all_idols: list[Idol] = []
    all_groups: list[Group] = []
    all_overrides: Overrides

    OUT_JSON_FNAME = "kpopnet.json"
    OUT_MINJSON_FNAME = "kpopnet.min.json"
    OUT_THUMB_DNAME = "thumb"

    THUMB_BASE_URL = "https://up.kpop.re/net"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_root_fpath = Path(__file__).parent / ".." / ".."

        self.out_json_fpath = project_root_fpath / self.OUT_JSON_FNAME
        self.out_minjson_fpath = project_root_fpath / self.OUT_MINJSON_FNAME
        self.out_thumb_dpath = project_root_fpath / self.OUT_THUMB_DNAME

        overrides_fpath = project_root_fpath / "overrides.json"
        self.all_overrides = json.load(open(overrides_fpath))

        self.cleanup()

    def cleanup(self):
        with suppress(FileNotFoundError):
            os.remove(self.out_json_fpath)
        with suppress(FileNotFoundError):
            os.remove(self.out_minjson_fpath)

    @staticmethod
    def unquote(url: str) -> str:
        url = unquote(url)
        # for convenient ctrl+click from terminal
        return url.replace(" ", "%20")

    def parse(self, response):
        for href in response.css(".cell_line a::attr(href)").getall():
            if href.startswith("/noona/idol/"):
                yield response.follow(href, callback=self.parse_idol)

    def parse_date(self, prop, value, full=True):
        if full:
            m = re.search(r"(\d{4})\s*-\s*(\d{2})\s*-\s*(\d{2})", value)
        else:
            m = re.search(r"(\d{4})(?:\s*-\s*(\d{2})(?:\s*-\s*(\d{2}))?)?", value)
        assert m, (prop, value)
        year, month, day = m.groups()
        month = month or "00"
        day = day or "00"
        return f"{year}-{month}-{day}"

    def download_thumb(self, response: Response, item: Idol | Group):
        thumb_url = response.css(".thumb img::attr(src)").get()
        if not thumb_url:
            return  # optional
        assert thumb_url.endswith(".jpg"), thumb_url
        # Callbacks are better than await here because we can download
        # everything asynchonously
        yield response.follow(
            thumb_url, callback=self.write_thumb, cb_kwargs=dict(item=item)
        )

    def write_thumb(self, response: Response, item: Idol | Group):
        im = Image.open(io.BytesIO(response.body))
        assert im.format == "JPEG", item
        hash = hashlib.sha1(response.body).hexdigest()
        fname = hash[:2] + "/" + hash[2:] + ".jpg"
        fpath = self.out_thumb_dpath / fname
        os.makedirs(fpath.parent, exist_ok=True)
        fpath.write_bytes(response.body)
        item["thumb_url"] = self.THUMB_BASE_URL + "/" + fname

    def get_item_kpopnet_url(self, item: Idol | Group) -> str:
        return f"https://net.kpop.re/?id={item['id']}"

    def parse_idol(self, response):
        """
        Pop type: K-pop
        Stage name (romanized): Boram
        Stage name (original): 보람
        Real name (romanized): Jeon Boram
        Real name (original): 전보람
        Birth date: 1986-03-22 (age 37) ▲ ▼
        Chinese zodiac sign: 🐅 Tiger
        Western zodiac sign: ♈ Aries
        Hometown: Seoul
        Height: 152.8cm (5'0") ▲ ▼
        Weight: 40.0kg (88lb) ▲ ▼
        Blood type: B
        Debut date: 2008-04-15 (15 years and 6 months ago) ▲ ▼
        Country of origin: Korea, Republic of
        """
        idol = cast(Idol, {})
        table_idol = response.css("h1 ~ div table")[0]
        for tr in table_idol.css("tr"):
            prop = tr.css("td:nth-child(1)::text").get()
            if not prop:
                continue
            prop = prop.strip()
            value = tr.css("td:nth-child(2) ::text").getall()
            value = "".join(value).strip()
            if not value:
                continue

            # TODO: other fields: formerly known as, hometown, country
            # TODO: additional fields? name_kanji, real_name_hanja
            if prop == "Pop type":
                assert value == "K-pop", (prop, value)
            elif re.search(r"stage\s+name.*romanized", prop, re.I):
                idol["name"] = value
            elif re.search(r"stage\s+name.*original", prop, re.I):
                value = re.sub(r"\s*\(.*\)$", "", value)  # remove kanji name
                idol["name_original"] = value
            elif re.search(r"real\s+name.*romanized", prop, re.I):
                idol["real_name"] = value
            elif re.search(r"real\s+name.*original", prop, re.I):
                value = re.sub(r"\s*\(.*\)$", "", value)  # remove hanja name
                idol["real_name_original"] = value
            elif re.search(r"birth\s+date", prop, re.I):
                idol["birth_date"] = self.parse_date(prop, value)
            elif re.search(r"debut\s+date", prop, re.I):
                idol["debut_date"] = self.parse_date(prop, value, full=False)
            elif re.search(r"height", prop, re.I):
                m = re.search(r"(\d+(?:\.\d+)?)cm", value)
                assert m, (prop, value)
                idol["height"] = float(m.group(1))
            elif re.search(r"weight", prop, re.I):
                m = re.search(r"(\d+(?:\.\d+)?)kg", value)
                assert m, (prop, value)
                idol["weight"] = float(m.group(1))

        idol["_groups"] = []  # tmp key, will update later
        tables_groups = response.css("h2 ~ table tbody")
        if tables_groups:
            # TODO: subunit table
            # XXX: subunits table without groups table?
            for tr in tables_groups[0].css("tr"):
                tds = tr.css("td")
                group_name = tds[1].css("a::text").get()
                group_url = tds[1].css("a::attr(href)").get()
                group_disbanded = tds[4].get() is not None
                group_current = not group_disbanded
                if len(tds) > 5:
                    group_current = tds[5].css("::text").get() == "Yes"
                group_roles = None
                if len(tds) > 6:
                    roles_text = tds[6].css("::text").get()
                    # TODO: split by comma?
                    group_roles = roles_text.lower() if roles_text else None
                # FIXME: might need to normalize group_name and reference will be broken!
                idol["_groups"].append(
                    {"name": group_name, "current": group_current, "roles": group_roles}
                )
                # TODO(Kagami): does crawl deduplication always work?
                yield response.follow(group_url, callback=self.parse_group)

        yield from self.download_thumb(response, idol)

        idol["urls"] = [response.url]
        # TODO: Check for <h2>References</h2>?
        # list_urls = response.css("h2 ~ ul")
        # if list_urls:
        #     for url in list_urls.css("a::attr(href)").getall():
        #         idol["urls"].append(self.unquote(url))

        IdolValidator.normalize(cast(dict, idol), self.all_overrides["idols"])
        idol["urls"].insert(0, self.get_item_kpopnet_url(idol))
        self.all_idols.append(idol)

    def parse_group(self, response):
        """
        Display name (romanized): T-ara
        Display name (original): 티아라
        Company: MBK Entertainment
        Debut date: 2009-07-29 (14 years and 3 months ago)
        """
        group = cast(Group, {})
        table_group = response.css("h1 ~ div table")[0]
        for tr in table_group.css("tr"):
            prop = tr.css("td:nth-child(1)::text").get()
            if not prop:
                continue
            prop = prop.strip()
            value = tr.css("td:nth-child(2) ::text").getall()
            value = "".join(value).strip()
            if not value:
                continue

            if re.search(r"display\s+name.*romanized", prop, re.I):
                group["name"] = value
            elif re.search(r"display\s+name.*original", prop, re.I):
                group["name_original"] = value
            elif re.search(r"company", prop, re.I):
                group["agency_name"] = value
            elif re.search(r"debut\s+date", prop, re.I):
                group["debut_date"] = self.parse_date(prop, value, full=False)
            elif re.search(r"disbandment\s+date", prop, re.I):
                group["disband_date"] = self.parse_date(prop, value, full=False)

        yield from self.download_thumb(response, group)

        group["urls"] = [response.url]
        # list_urls = response.css("h2 ~ ul")
        # if list_urls:
        #     for url in list_urls.css("a::attr(href)").getall():
        #         group["urls"].append(self.unquote(url))

        GroupValidator.normalize(cast(dict, group), self.all_overrides["groups"])
        group["urls"].insert(0, self.get_item_kpopnet_url(group))
        self.all_groups.append(group)

    def closed(self, reason):
        if reason != "finished":
            self.log("Exited with error, no dump")
            return

        self.log("Processing data")
        idol_key = lambda i: (i["birth_date"], i["real_name"])
        group_key = lambda g: (g["debut_date"] or "0", g["name"])
        idols = sorted(self.all_idols, key=idol_key, reverse=True)
        groups = sorted(self.all_groups, key=group_key, reverse=True)

        # Modify idol/group data *in place*
        group_by_id = dict((g["id"], g) for g in groups)
        group_by_name = dict((g["name"], g) for g in groups)
        idol_groups_key = lambda gid: group_key(group_by_id[gid])

        for group in groups:
            group["members"] = []
        for idol in idols:
            idol["groups"] = []
            for idol_group in idol.pop("_groups"):
                group = group_by_name[idol_group["name"]]
                idol["groups"].append(group["id"])
                group["members"].append(
                    {
                        "id": idol["id"],
                        "current": idol_group["current"],
                        "roles": idol_group["roles"],
                    }
                )
            idol["groups"].sort(key=idol_groups_key, reverse=True)

        # Validate after modifications
        IdolValidator.validate_all(self.all_idols)
        GroupValidator.validate_all(self.all_groups)

        profiles: Profiles = {"idols": idols, "groups": groups}
        self.log("Dumping data")
        with open(self.out_json_fpath, "w") as f:
            json.dump(profiles, f, ensure_ascii=False, sort_keys=True, indent=2)
        with open(self.out_minjson_fpath, "w") as f:
            json.dump(
                profiles, f, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
