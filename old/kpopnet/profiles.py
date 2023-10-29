import json
from .spiders import profile_spiders, run_spider
from .io import (
    get_all_band_names,
    get_idol_names,
    get_band_path_by_name,
    get_idol_path_by_name,
    load_json,
)


def update(spider_name, **kwargs):
    """
    Collect/update profiles info using given spider and write them to
    data directory. Safe to use multiple times, previously collected
    data will be preserved.
    """
    spider = profile_spiders[spider_name]
    return run_spider(spider, **kwargs)


def export(opath):
    bands = []
    idols = []
    for bname in get_all_band_names():
        bpath = get_band_path_by_name(bname)
        band = load_json(bpath)
        try:
            # TODO(Kagami): Don't write this?
            del band['urls']
        except KeyError:
            pass
        bands.append(band)
        for iname in get_idol_names(bname):
            ipath = get_idol_path_by_name(bname, iname)
            idols.append(load_json(ipath))
    result = dict(bands=bands, idols=idols)
    json.dump(result, open(opath, 'w'), ensure_ascii=False, separators=(',', ':'))
    return 0
