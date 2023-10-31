import pytest


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_parse_date():
    from .kastden import KastdenSpider

    s = KastdenSpider()

    assert s.parse_date("date", "2003-01-09") == "2003-01-09"

    with pytest.raises(AssertionError):
        s.parse_date("date", "2023")
    with pytest.raises(AssertionError):
        s.parse_date("date", "2023-01")

    assert s.parse_date("date", "2003", full=False) == "2003-00-00"
    assert s.parse_date("date", "2003-01", full=False) == "2003-01-00"
