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
from ..utils import find_by_field


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

    def parse_name_alias(self, value: str) -> str:
        value = re.sub(r"\s*\(\s*", ",", value)
        value = re.sub(r"\s*\)\s*", ",", value)
        value = re.sub(r",+$", "", value)
        value = re.sub(r"\s*,+\s*", ", ", value)
        return value

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
            elif re.search(r"formerly\s+known\s+as", prop, re.I):
                idol["name_alias"] = self.parse_name_alias(value)
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
        for table_groups in response.css("h2 ~ table tbody"):  # groups + subunits
            for tr in table_groups.css("tr"):
                tds = tr.css("td")
                # group_name = tds[1].css("a::text").get()
                group_url = response.urljoin(tds[1].css("a::attr(href)").get())
                if len(tds) >= 5:
                    group_disbanded = tds[4].get() is not None
                    group_current = not group_disbanded
                else:
                    # will fix with info from main group later
                    group_current = True
                if len(tds) >= 6:
                    group_current = tds[5].css("::text").get() == "Yes"
                group_roles = None
                if len(tds) >= 7:
                    roles_text = tds[6].css("::text").get()
                    group_roles = roles_text.lower() if roles_text else None
                idol["_groups"].append(
                    {"url": group_url, "current": group_current, "roles": group_roles}
                )
                # TODO(Kagami): does crawl deduplication always work?
                yield response.follow(group_url, callback=self.parse_group)

        yield from self.download_thumb(response, idol)

        idol["urls"] = [response.url]
        list_urls = response.css("h2 ~ ul")
        if list_urls:
            urls = list_urls[0].css("a::attr(href)").getall()
            namu_urls = [self.unquote(url) for url in urls if "namu.wiki" in url]
            if len(namu_urls) > 1:
                # might be multiple references to namu, we need the one pointing to idol
                namu_urls = [
                    url
                    for url in namu_urls
                    if idol["name_original"] in url or idol["name"] in url
                ]
                assert len(namu_urls) == 1, urls
            if namu_urls:
                idol["urls"].append(namu_urls[0])

        IdolValidator.normalize(cast(dict, idol), self.all_overrides["idols"])
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

        table_parent_group = response.xpath(
            "//h2[contains(text(), 'Main group')]/following-sibling::table[1]/tbody"
        )
        if table_parent_group:
            # should be only one parent group
            trs = table_parent_group[0].css("tr")
            assert len(trs) == 1, trs
            tr_group = trs[0]

            parent_url = tr_group.css("td:nth-child(2) a::attr(href)").get()
            parent_url = response.urljoin(parent_url)
            group["parent_id"] = parent_url  # will fix with ID later

            # subunits miss agency_name, copy from main group
            assert "agency_name" not in group, group
            group["agency_name"] = tr_group.css("td:nth-child(3) ::text").get().strip()

        yield from self.download_thumb(response, group)

        group["urls"] = [response.url]
        list_urls = response.css("h2 ~ ul")
        if list_urls:
            urls = list_urls[0].css("a::attr(href)").getall()
            namu_urls = [self.unquote(url) for url in urls if "namu.wiki" in url]
            assert len(namu_urls) <= 1, urls
            if namu_urls:
                group["urls"].append(namu_urls[0])

        GroupValidator.normalize(cast(dict, group), self.all_overrides["groups"])
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
        # XXX: second url is kastden
        group_by_url = dict((g["urls"][1], g) for g in groups)
        idol_groups_key = lambda gid: group_key(group_by_id[gid])

        for group in groups:
            group["members"] = []
        for idol in idols:
            idol["groups"] = []
            for idol_group in idol.pop("_groups"):
                group = group_by_url[idol_group["url"]]
                idol["groups"].append(group["id"])
                group["members"].append(
                    {
                        "idol_id": idol["id"],
                        "current": idol_group["current"],
                        "roles": idol_group["roles"],
                    }
                )
            idol["groups"].sort(key=idol_groups_key, reverse=True)
        # fix subunits
        for group in groups:
            if group["parent_id"]:
                parent_group = group_by_url[group["parent_id"]]
                group["parent_id"] = parent_group["id"]
                for member in group["members"]:
                    # O(n^2) but should be fine
                    parent_member = find_by_field(
                        parent_group["members"], "idol_id", member["idol_id"]
                    )
                    assert parent_member, (group, member)
                    member["current"] = parent_member["current"]

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
