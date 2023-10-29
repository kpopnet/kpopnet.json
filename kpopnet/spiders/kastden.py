import re
import json
import base64
import hashlib
from pprint import pprint
import scrapy


class Idol(dict):
    REQUIRED_FIELDS = [
        "name",
        "name_original",
        "real_name",
        "real_name_original",
        "birth_date",
    ]
    OPTIONAL_FIELDS = ["debut_date", "height", "weight"]

    def gen_id(self):
        s = self["real_name_original"] + self["birth_date"]
        hash = hashlib.md5(s.encode()).digest()
        return base64.b64encode(hash).decode().rstrip("=")

    def normalize(self):
        for field in self.REQUIRED_FIELDS:
            assert self.get(field), (field, self)
        for field in self.OPTIONAL_FIELDS:
            if field not in self:
                self[field] = None
        self["id"] = self.gen_id()


class Group(dict):
    pass


class KastdenSpider(scrapy.Spider):
    name = "kastden"
    allowed_domains = ["selca.kastden.org"]
    start_urls = ["https://selca.kastden.org/noona/search/?pt=kpop&h_op=lt&h=153"]

    all_idols: list[Idol] = []
    all_groups: list[Group] = []

    def parse(self, response):
        for href in response.css(".cell_line a::attr(href)").getall():
            if href.startswith("/noona/idol/"):
                yield response.follow(href, callback=self.parse_idol)

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
        idol = Idol()
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

            # TODO: other fields
            if prop == "Pop type":
                assert value == "K-pop", (prop, value)
            elif re.search(r"stage\s+name.*romanized", prop, re.I):
                idol["name"] = value
            elif re.search(r"stage\s+name.*original", prop, re.I):
                idol["name_original"] = value
            elif re.search(r"real\s+name.*romanized", prop, re.I):
                idol["real_name"] = value
            elif re.search(r"real\s+name.*original", prop, re.I):
                idol["real_name_original"] = value
            elif re.search(r"birth\s+date", prop, re.I):
                m = re.search(r"(\d{4})\s*-\s*(\d{2})\s*-\s*(\d{2})", value)
                assert m, (prop, value)
                idol["birth_date"] = "-".join(m.groups())
            elif re.search(r"debut\s+date", prop, re.I):
                m = re.search(r"(\d{4})\s*-\s*(\d{2})\s*-\s*(\d{2})", value)
                assert m, (prop, value)
                idol["debut_date"] = "-".join(m.groups())
            elif re.search(r"height", prop, re.I):
                m = re.search(r"(\d+(?:\.\d+)?)cm", value)
                assert m, (prop, value)
                idol["height"] = float(m.group(1))
            elif re.search(r"weight", prop, re.I):
                m = re.search(r"(\d+(?:\.\d+)?)kg", value)
                assert m, (prop, value)
                idol["weight"] = float(m.group(1))

        idol["groups"] = []
        table2 = response.css("h2 ~ table tbody")
        if table2:
            # TODO: subunit table
            # XXX: subunits table without groups table?
            for tr in table2[0].css("tr"):
                # TODO: roles
                tds = tr.css("td")
                td_img, td_name, td_company, td_debut, td_disband, td_current = tds[:6]
                group_name = td_name.css("a::text").get()
                idol["groups"].append(group_name)
                group_url = td_name.css("a::attr(href)").get()
                # XXX: does deduplication always work?
                yield response.follow(group_url, callback=self.parse_group)

        idol.normalize()
        self.all_idols.append(idol)

    def parse_group(self, response):
        print("PARSING", response.url)

    def closed(self, reason):
        self.log("Dumping data")
        idols = sorted(self.all_idols, key=lambda i: i["birth_date"], reverse=True)
        groups = sorted(self.all_groups, key=lambda g: g["debut_date"], reverse=True)
        result = {"idols": idols, "groups": groups}
        with open("kpopnet.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)
