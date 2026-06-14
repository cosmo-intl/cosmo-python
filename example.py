"""Runnable tour of cosmo. `python example.py`"""

import datetime

from cosmo import Cosmo

when = datetime.datetime(2020, 2, 2, 9, 30, tzinfo=datetime.timezone.utc)

for tag in ("en_AU", "fa_IR", "de_DE"):
    c = Cosmo(tag, {"timeZone": "UTC"})
    print(f"\n=== {tag} ===")
    print("language(en):  ", c.language("en"))
    print("country/flag:  ", c.country(), c.flag())
    print("number:        ", c.number(1234567.89))
    print("money:         ", c.money(1234.5))
    print("percentage:    ", c.percentage(0.1234))
    print("compact:       ", c.compact(1_200_000, "long"))
    print("spellout/ord:  ", c.spellout(42), "/", c.ordinal(21))
    print("moment:        ", c.moment(when, "full", "short"))
    print("month[0]:      ", c.month_names()[0])
    print("relative:      ", c.relative_duration(-3, "day"))
    print("join:          ", c.join(["apples", "pears", "figs"]))
    print("quote:         ", c.quote("hi"))
    print("plural(2):     ", c.plural_category(2))
    print(
        "message:       ",
        c.message("{0, plural, one {# file} other {# files}}", [3]),
    )
