import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture()
def spider():
    from .kastden import KastdenSpider

    return KastdenSpider()


def test_parse_date(spider):
    s = spider
    assert s.parse_date("date", "2003-01-09") == "2003-01-09"

    with pytest.raises(AssertionError):
        s.parse_date("date", "2023")
    with pytest.raises(AssertionError):
        s.parse_date("date", "2023-01")

    assert s.parse_date("date", "2003", full=False) == "2003-00-00"
    assert s.parse_date("date", "2003-01", full=False) == "2003-01-00"


def test_parse_name_alias(spider):
    s = spider
    assert s.parse_name_alias("Lizzy (리지)") == "Lizzy, 리지"
    assert s.parse_name_alias("박혜경 (朴惠慶)") == "박혜경, 朴惠慶"
    assert s.parse_name_alias("Tae E (태이), Jian (지안)") == "Tae E, 태이, Jian, 지안"
    assert s.parse_name_alias("Lim Chanmi (임찬미 (林澯美))") == "Lim Chanmi, 임찬미, 林澯美"
    assert (
        s.parse_name_alias("Hyeseong (혜성), Yang Hyeseon (양혜선 (梁寭善))")
        == "Hyeseong, 혜성, Yang Hyeseon, 양혜선, 梁寭善"
    )

    assert s.parse_name_alias("Tae E (태이)  ,   Jian (지안)") == "Tae E, 태이, Jian, 지안"
    assert (
        s.parse_name_alias("Tae E ( 태이  )  ,  Jian  ( 지안 ) ") == "Tae E, 태이, Jian, 지안"
    )
