import re
import json
from pprint import pprint
import scrapy


class KastdenSpider(scrapy.Spider):
    name = "kastden"
    allowed_domains = ["selca.kastden.org"]
    start_urls = ["https://selca.kastden.org/noona/search/?pt=kpop&h_op=lt&h=153"]

    all_idols = []

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
        idol = {}
        table = response.css("table")[0]
        for tr in table.css("tr"):
            prop = tr.css("td:nth-child(1)::text").get()
            if not prop:
                continue
            prop = prop.strip()
            value = tr.css("td:nth-child(2) ::text").getall()
            value = "".join(value).strip()
            if not value:
                continue

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

        self.normalize_idol(idol)
        self.all_idols.append(idol)

    REQUIRED_FIELDS = [
        "name",
        "name_original",
        "real_name",
        "real_name_original",
        "birth_date",
    ]
    OPTIONAL_FIELDS = ["debut_date", "height", "weight"]

    def normalize_idol(self, idol: dict):
        for field in self.REQUIRED_FIELDS:
            assert field in idol, (field, idol)
        for field in self.OPTIONAL_FIELDS:
            if field not in idol:
                idol[field] = None

    def closed(self, reason):
        result = {"idols": self.all_idols}
        with open("kpopnet.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)
