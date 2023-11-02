#!/usr/bin/env pipenv run python

import sys
import argparse

from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def main():
    parser = argparse.ArgumentParser(
        prog="kpopnet",
        description="kpopnet web spiders and utils",
    )
    parser.add_argument("kastden", nargs="?")

    args = parser.parse_args()

    if args.kastden:

        def process_spider_error(failure, response, spider):
            nonlocal had_error
            had_error = True

        def process_spider_closed(spider, reason):
            nonlocal had_error
            if reason != "finished":
                had_error = True

        had_error = False

        process = CrawlerProcess(get_project_settings())
        crawler = process.create_crawler("kastden")
        crawler.signals.connect(process_spider_error, signals.spider_error)
        crawler.signals.connect(process_spider_closed, signals.spider_closed)
        process.crawl(crawler)
        process.start()

        # XXX(Kagami): hackish way to catch exception in closed()
        if crawler.stats and crawler.stats.get_value("log_count/ERROR", 0) != 0:
            had_error = True

        if had_error:
            print()
            print("@" * 50)
            print("ERROR OCCURED, PLEASE CHECK LOGS")
            print("@" * 50)
            sys.exit(1)

    else:
        parser.print_usage(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
