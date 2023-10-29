import scrapy


class KastdenSpider(scrapy.Spider):
    name = "kastden"
    allowed_domains = ["selca.kastden.org"]
    start_urls = ["https://selca.kastden.org/noona/search/?pt=kpop&h_op=lt&h=153"]

    def parse(self, response):
        for href in response.css(".cell_line a::attr(href)").getall():
            if href.startswith("/noona/idol/"):
                url = response.urljoin(href)
                print(f"found idol {url}")
                yield response.follow(url, callback=self.parse_idol)
                break

    def parse_idol(self, response):
        idol = {}
        table = response.css("table")[0]
        for tr in table.css("tr"):
            name = tr.css("td:nth-child(1)::text").get()
            value = tr.css("td:nth-child(2)::text").get()
            if not name or not value:
                continue
            name = name.strip()
            value = value.strip()

            print(f"{name}: {value}")
