"""Tests for cosmo (Python / PyICU port).

These assert observable, locale-stable behaviour. Exact display strings can vary
between ICU versions, so where a wording is volatile we assert structure
(substrings, membership, length) rather than a brittle literal.
"""

import datetime

import pytest

from cosmo import Bundle, Cosmo, CosmoError

# A fixed instant: 2020-02-02T00:13:20Z (POSIX seconds).
TS = 1580602400.0


# --------------------------------------------------------------------------- #
# construction & subtags
# --------------------------------------------------------------------------- #


def test_canonicalises_locale():
    assert Cosmo("en-au").locale == "en_AU"
    assert Cosmo("en_AU").subtags == {"language": "en", "script": "", "region": "AU"}


def test_region_currency_inference():
    assert Cosmo("en_AU").modifiers["currency"] == "AUD"
    assert Cosmo("en_US").modifiers["currency"] == "USD"
    assert Cosmo("en").modifiers["currency"] is None  # no region -> no inference


def test_modifier_timezone_alias():
    c = Cosmo("en_AU", {"timezone": "Australia/Sydney"})
    assert c.modifiers["timeZone"] == "Australia/Sydney"


def test_from_subtags():
    assert Cosmo.from_subtags({"language": "en", "region": "AU"}).locale == "en_AU"


def test_from_accept_language_picks_highest_q():
    assert Cosmo.from_accept_language("fr-CH, en;q=0.9, de;q=0.7").locale == "fr_CH"
    assert Cosmo.from_accept_language("en;q=0.2, de;q=0.8").subtags["language"] == "de"


# --------------------------------------------------------------------------- #
# key -> value lookups
# --------------------------------------------------------------------------- #


def test_language():
    assert Cosmo("en").language("en") == "English"
    assert Cosmo("fa").language("en") == "انگلیسی"
    assert Cosmo("en").language("") == ""


def test_country_and_script():
    assert Cosmo("en").country("AU") == "Australia"
    assert Cosmo("en").country("") == ""
    assert Cosmo("en").script("Latn") == "Latin"
    assert "Simplified" in Cosmo("en").script("Hans")


def test_calendar_and_direction():
    assert Cosmo("en").calendar("buddhist") == "Buddhist Calendar"
    assert Cosmo("en").direction() == "ltr"
    assert Cosmo("fa").direction() == "rtl"
    assert Cosmo("en").direction("ar") == "rtl"


def test_flag():
    assert Cosmo("en_AU").flag() == "🇦🇺"
    assert Cosmo("en").flag("US") == "🇺🇸"
    assert Cosmo("en").flag("X") == ""


def test_currency_name_and_symbol():
    c = Cosmo("en_US")
    assert c.currency("AUD") == "Australian Dollar"
    assert c.currency("AUD", symbol=True) == "A$"
    assert c.currency("ZZZ") == "ZZZ"  # echoes unknown back
    with pytest.raises(CosmoError):
        c.currency("ZZZ", strict=True)


# --------------------------------------------------------------------------- #
# numbers
# --------------------------------------------------------------------------- #


def test_number_percentage():
    assert Cosmo("en").number(1234567.89) == "1,234,567.89"
    assert Cosmo("en").percentage(0.2) == "20%"
    # halfExpand (round half away from zero) — matches the JS port's Intl default.
    assert Cosmo("en").percentage(0.12345, 2) == "12.35%"


def test_money():
    assert Cosmo("en_AU").money(1234.5) == "$1,234.50"
    assert Cosmo("en_US").money(1234.5, "EUR") == "€1,234.50"
    assert Cosmo("en_US").money(1234.9, "USD", precision=0) == "$1,235"
    assert Cosmo("en").money(100) == ""  # no currency available
    with pytest.raises(CosmoError):
        Cosmo("en").money(100, strict=True)


def test_symbol():
    c = Cosmo("en")
    assert c.symbol("decimal") == "."
    assert c.symbol("grouping_separator") == ","
    assert c.symbol("percent") == "%"
    assert Cosmo("de").symbol("decimal") == ","
    with pytest.raises(CosmoError):
        c.symbol("bogus")


def test_unit():
    assert Cosmo("en").unit("digital", "gigabyte", 2.19) == "2.19 gigabytes"
    assert "GB" in Cosmo("en").unit("digital", "gigabyte", 2.19, "short")
    with pytest.raises(CosmoError):
        Cosmo("en").unit("x", "not-a-unit", 1)


def test_scientific_compact():
    assert Cosmo("en").scientific(12345) == "1.2345E4"
    assert Cosmo("en").compact(1200) == "1.2K"
    assert Cosmo("en").compact(1200000, "long") == "1.2 million"


def test_ordinal_spellout():
    c = Cosmo("en")
    assert c.ordinal(1) == "1st"
    assert c.ordinal(2) == "2nd"
    assert c.spellout(42) == "forty-two"


def test_duration():
    c = Cosmo("en")
    assert c.duration(1221440) == "339:17:20"
    assert "hours" in c.duration(1221440, with_words=True)


# --------------------------------------------------------------------------- #
# dates & times
# --------------------------------------------------------------------------- #


def test_moment_date_time():
    c = Cosmo("en_US", {"timeZone": "UTC"})
    assert c.date(TS, "long") == "February 2, 2020"
    assert c.time(TS, "short") == "12:13 AM"
    assert c.moment(TS, "none", "none") == ""


def test_moment_accepts_datetime_and_date():
    c = Cosmo("en_US", {"timeZone": "UTC"})
    dt = datetime.datetime(2020, 2, 2, 0, 13, 20, tzinfo=datetime.timezone.utc)
    assert c.date(dt, "long") == "February 2, 2020"
    assert c.date(datetime.date(2020, 2, 2), "long") == "February 2, 2020"


def test_format_moment_pattern():
    assert Cosmo("en_US", {"timeZone": "UTC"}).format_moment(TS, "yyyy-MM-dd") == "2020-02-02"


def test_persian_calendar_is_implicit():
    # fa_IR resolves to the Persian calendar without an explicit modifier.
    assert "۱۳۹۸" in Cosmo("fa_IR", {"timeZone": "UTC"}).date(TS, "long")


def test_date_range():
    out = Cosmo("en_US", {"timeZone": "UTC"}).date_range(
        datetime.date(2020, 2, 2), datetime.date(2020, 2, 5)
    )
    assert "2" in out and "5" in out and "Feb" in out


# --------------------------------------------------------------------------- #
# collation & segmentation
# --------------------------------------------------------------------------- #


def test_compare_sort():
    c = Cosmo("en")
    assert c.compare("a", "b") < 0
    assert c.compare("b", "a") > 0
    assert c.sort(["banana", "apple", "cherry"]) == ["apple", "banana", "cherry"]
    assert c.sort([{"n": "b"}, {"n": "a"}], key=lambda x: x["n"]) == [{"n": "a"}, {"n": "b"}]


def test_contains():
    c = Cosmo("en")
    assert c.contains("Résumé", "resume") is True  # base: ignore case & accents
    assert c.contains("hello world", "WORLD") is True
    assert c.contains("hello", "xyz") is False
    assert c.contains("anything", "") is True
    assert c.contains("Résumé", "resume", "variant") is False


def test_segmentation():
    c = Cosmo("en")
    assert c.split_words("Hello, world! ICU rocks.") == ["Hello", "world", "ICU", "rocks"]
    assert c.split_sentences("Hi there. How are you?") == ["Hi there.", "How are you?"]


def test_ellipsize():
    c = Cosmo("en")
    assert c.ellipsize("short", 20) == "short"
    out = c.ellipsize("The quick brown fox jumps", 15)
    assert out.endswith("…") and len(out) <= 15


# --------------------------------------------------------------------------- #
# messages, plurals, quoting, lists
# --------------------------------------------------------------------------- #


def test_message_positional_and_named():
    c = Cosmo("en")
    assert c.message("{0} has {1, plural, one {# item} other {# items}}", ["Bob", 3]) == "Bob has 3 items"
    assert c.message("{0, plural, one {# item} other {# items}}", [1]) == "1 item"
    assert c.message("{name} likes {n, plural, one {# cat} other {# cats}}", {"name": "Sue", "n": 2}) == "Sue likes 2 cats"


def test_plural_category():
    c = Cosmo("en")
    assert c.plural_category(1) == "one"
    assert c.plural_category(2) == "other"
    assert c.plural_category(1, ordinal=True) == "one"
    assert c.plural_category(2, ordinal=True) == "two"
    assert c.plural_category(3, ordinal=True) == "few"


def test_quote():
    assert Cosmo("en").quote("hi") == "“hi”"
    assert Cosmo("fa").quote("x") == "«x»"


def test_join():
    c = Cosmo("en")
    assert c.join(["A", "B", "C"]) == "A, B, and C"  # en CLDR uses the Oxford comma
    assert c.join(["A", "B", "C"], "disjunction") == "A, B, or C"
    with pytest.raises(CosmoError):
        c.join(["A"], "bogus")


# --------------------------------------------------------------------------- #
# relative durations & ranges
# --------------------------------------------------------------------------- #


def test_relative_duration():
    c = Cosmo("en")
    assert c.relative_duration(-3, "day") == "3 days ago"
    assert c.relative_duration(2, "hour") == "in 2 hours"
    with pytest.raises(CosmoError):
        c.relative_duration(1, "fortnight")


def test_relative_duration_between():
    c = Cosmo("en")
    base = datetime.datetime(2020, 1, 1, 12, 0)
    assert c.relative_duration_between(base + datetime.timedelta(days=5), base) == "in 5 days"
    assert c.relative_duration_between(base - datetime.timedelta(days=3), base) == "3 days ago"


def test_number_and_money_ranges():
    c = Cosmo("en_US")
    assert c.number_range(3, 5) == "3–5"
    assert c.money_range(3, 5, "USD") == "$3.00 – $5.00"
    assert Cosmo("en").money_range(3, 5) == ""  # no currency


# --------------------------------------------------------------------------- #
# calendar metadata & case
# --------------------------------------------------------------------------- #


def test_month_weekday_names():
    en = Cosmo("en")
    assert en.month_names()[0] == "January"
    assert len(en.month_names()) == 12
    assert en.weekday_names()[0] == "Sunday"  # Sunday-first
    assert len(en.weekday_names()) == 7
    assert "فروردین" in Cosmo("fa_IR").month_names()  # Persian calendar months


def test_week_info():
    info = Cosmo("en_GB").week_info()
    assert info["first_day"] == 1  # Monday (ISO)
    assert "minimal_days" in info
    assert Cosmo("en_US").week_info()["first_day"] == 7  # Sunday


def test_likely_subtags():
    assert Cosmo("en").add_likely_subtags().locale == "en_Latn_US"
    assert Cosmo("en_Latn_US").remove_likely_subtags().locale == "en"


def test_time_zone_name():
    c = Cosmo("en", {"timeZone": "Australia/Sydney"})
    assert "Australian Eastern" in c.time_zone_name("long")
    assert c.time_zone_name("short") in ("AEST", "AEDT", "GMT+10", "GMT+11")


def test_case_transforms():
    assert Cosmo("en").upper("istanbul") == "ISTANBUL"
    assert Cosmo("tr").upper("istanbul") == "İSTANBUL"  # Turkish dotted I
    assert Cosmo("en").lower("HELLO") == "hello"


# --------------------------------------------------------------------------- #
# raw ICU access
# --------------------------------------------------------------------------- #


def test_get_resource_bundle():
    eur = Cosmo("en").get(Bundle.CURRENCY, "Currencies", "EUR")
    assert eur.get(1).getString() == "Euro"
    assert Cosmo("en").get(Bundle.CURRENCY, "Currencies", "NOPE") is None


# --------------------------------------------------------------------------- #
# v1.1 additions — cross-port parity features
# --------------------------------------------------------------------------- #


def test_display_name():
    c = Cosmo("en")
    assert c.display_name("language", "fr") == "French"
    assert c.display_name("region", "JP") == "Japan"
    assert "Simplified" in c.display_name("script", "Hans")
    assert c.display_name("calendar", "buddhist") == "Buddhist Calendar"
    assert c.display_name("currency", "EUR") == "Euro"
    with pytest.raises(CosmoError):
        c.display_name("nope", "x")


def test_split_graphemes():
    c = Cosmo("en")
    assert c.split_graphemes("a👩‍👧b") == ["a", "👩‍👧", "b"]  # emoji ZWJ stays whole
    assert c.split_graphemes("") == []


def test_split_methods_handle_non_bmp():
    # Regression: ICU returns UTF-16 offsets; segments must stay aligned past the BMP.
    c = Cosmo("en")
    assert c.split_words("hi 👩‍👧 café") == ["hi", "café"]


def test_supported_values():
    c = Cosmo("en")
    assert "Australia/Sydney" in c.supported_values("timeZone")
    assert "standard" in c.supported_values("collation")
    assert "latn" in c.supported_values("numberingSystem")
    assert "gigabyte" in c.supported_values("unit")
    with pytest.raises(CosmoError):
        c.supported_values("currency")  # not enumerable via PyICU
    with pytest.raises(CosmoError):
        c.supported_values("bogus")


def test_duration_multi_unit():
    c = Cosmo("en")
    assert c.duration({"hours": 3, "minutes": 5}, with_words=True) == "3 hours, 5 minutes"
    assert "2 days" in c.duration({"days": 2, "hours": 3})
    assert c.duration(1221440) == "339:17:20"  # scalar seconds unchanged
    assert c.duration({}) == ""


def test_number_options():
    c = Cosmo("en")
    assert c.number(2.9, {"rounding_mode": "floor", "maximum_fraction_digits": 0}) == "2"
    assert c.number(2.1, {"rounding_mode": "ceil", "maximum_fraction_digits": 0}) == "3"
    assert c.number(1.23, {"rounding_increment": 5, "minimum_fraction_digits": 2, "maximum_fraction_digits": 2}) == "1.25"
    assert c.number(12345, {"use_grouping": False}) == "12345"
    assert c.money(9.991, "USD", options={"rounding_mode": "ceil"}) == "$10.00"
    assert c.percentage(0.12349, 2, {"rounding_mode": "floor"}) == "12.34%"
    with pytest.raises(CosmoError):
        c.number(1, {"rounding_mode": "bogus"})


def test_collation_options():
    c = Cosmo("en")
    assert c.compare("item2", "item10", {"numeric": True}) < 0
    assert c.sort(["item10", "item2", "item1"], options={"numeric": True}) == ["item1", "item2", "item10"]
    assert c.sort(["b", "B", "a", "A"], options={"case_first": "upper"}) == ["A", "a", "B", "b"]


# --------------------------------------------------------------------------- #
# locale negotiation, transforms, spoofing, index, parsing
# --------------------------------------------------------------------------- #


def test_best_match():
    # CLDR language distance: en_AU is served better by en-GB than en-US.
    assert Cosmo("en_AU").best_match(["en-US", "en-GB", "fr"]) == "en-GB"
    assert Cosmo("ja").best_match(["fr", "de"]) == "fr"  # fallback: first supported
    with pytest.raises(CosmoError):
        Cosmo("en").best_match([])


def test_from_accept_language_negotiated():
    c = Cosmo.from_accept_language("fr-CH, en;q=0.9", supported=["en-US", "fr-FR"])
    assert c.locale == "fr_FR"
    assert Cosmo.from_accept_language("", supported=["en-US", "fr-FR"]).locale == "en_US"


def test_transliterate_romanize():
    c = Cosmo("en")
    assert c.romanize("Москва") == "Moskva"
    assert c.transliterate("Łódź café", "Any-Latin; Latin-ASCII") == "Lodz cafe"
    with pytest.raises(CosmoError):
        c.transliterate("x", "Nope-Nope")
    assert "Any-Latin" in c.supported_values("transliterator")


def test_spoof_checks():
    c = Cosmo("en")
    assert c.confusable("paypal", "раураl") is True  # Cyrillic look-alike
    assert c.confusable("hello", "world") is False
    assert c.suspicious("pаypal") is True  # mixed Latin/Cyrillic
    assert c.suspicious("paypal") is False


def test_index_buckets():
    buckets = Cosmo("en").index_buckets(["banana", "apple", "Cherry", "avocado"])
    assert list(buckets) == ["A", "B", "C"]
    assert buckets["A"] == ["apple", "avocado"]


def test_parsing():
    assert Cosmo("de").parse_number("1.234,56") == 1234.56
    assert Cosmo("en_US").parse_money("$12.30") == {"amount": 12.3, "currency": "USD"}
    utc = Cosmo("en_US", {"timeZone": "UTC"})
    assert utc.parse_moment("2020-02-02", "yyyy-MM-dd").timestamp() == 1580601600.0
    assert utc.date(utc.parse_date("February 2, 2020", "long"), "long") == "February 2, 2020"
    with pytest.raises(CosmoError):
        Cosmo("en").parse_number("not a number")
