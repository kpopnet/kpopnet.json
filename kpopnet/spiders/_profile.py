from uuid import uuid4

import scrapy

from ..io import get_band_by_url, save_band, save_idol


class ProfileSpider(scrapy.Spider):
    """
    Just a collection of useful wrappers. We may pass settings object in
    the future to support e.g. custom locations of profile data.
    """

    update_all = False
    bnames = []

    def uuid(self):
        return str(uuid4())

    def get_band_by_url(self, band):
        return get_band_by_url(band)

    def save_band(self, band):
        return save_band(band)

    def save_idol(self, band, idol):
        return save_idol(band, idol)
