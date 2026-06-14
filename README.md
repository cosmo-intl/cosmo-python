# Cosmo

Ergonomic application localisation for Python, powered by [ICU](https://icu.unicode.org/).

Cosmo is a thin, ergonomic layer over **ICU**, reached through
[PyICU](https://gitlab.pyicu.org/main/pyicu). Give it a locale (and optionally a
time zone) and it formats numbers, money, dates, units, lists and messages exactly
the way your users expect. There is **no bundled locale data** — every result comes
straight from ICU and [CLDR](https://cldr.unicode.org/), covering all languages,
scripts, calendars and time zones.

Cosmo is implemented consistently across four languages — the same concepts, method
names and behaviour, each built directly on its platform's ICU:
[JavaScript](https://github.com/cosmo-intl/cosmo-js) ([docs](https://cosmo.miloun.com/?lang=js)) ·
**Python** ·
[Java](https://github.com/cosmo-intl/cosmo-java) ([docs](https://cosmo.miloun.com/?lang=java)) ·
[PHP](https://github.com/salarmehr/cosmopolitan) ([docs](https://cosmo.miloun.com/?lang=php)).

📖 **Full documentation, API reference and live playground:** https://cosmo.miloun.com/?lang=python

## Requirements

- Python 3.9+
- System ICU development libraries for PyICU (e.g. `libicu-dev` + `pkg-config`)

## Install

```bash
pip install cosmo-intl        # pulls in PyICU; the import package is `cosmo`
```

## Quick start

```python
from cosmo import Cosmo

Cosmo("es_ES").money(11000.4, "EUR")                       # "11.000,40 €"
Cosmo("en").percentage(0.2)                                # "20%"
Cosmo("en_AU").money(1234.5)                               # "$1,234.50"  (currency inferred)
Cosmo("en").spellout(42)                                   # "forty-two"
Cosmo("fa").language("en")                                 # "انگلیسی"
```

All methods are `snake_case`. Underscore locales (`en_AU`) and [BCP-47](https://www.rfc-editor.org/info/bcp47)
[Unicode extensions](https://unicode.org/reports/tr35/#u_Extension)
(`fa-IR-u-nu-latn-ca-buddhist`) are both accepted.

## What you get

- **Locale display names** — languages, regions, scripts, calendars and currencies, plus emoji flags and writing direction.
- **Numbers & money** — decimals, percentages, currencies (inferred from the region), units, compact notation, scientific, ranges, plus spelled-out and ordinal text.
- **Dates & times** — locale formats in any calendar (Gregorian, Persian, Buddhist…), custom ICU patterns, durations, date ranges, and relative times.
- **Text** — locale-aware sort and search, word/sentence/grapheme segmentation, case mapping and quotation marks.
- **Messages** — [ICU MessageFormat](https://unicode-org.github.io/icu/userguide/format_parse/messages/) (`plural`, `selectordinal`, `select`).
- **Parsing & transforms** — the inverse formatters for numbers, money and dates, transliteration, UTS #39 spoof checks, locale negotiation and contact-list index buckets.
- **Raw ICU access** — resource-bundle lookups for data the high-level methods don't cover.

See the [full API reference](https://cosmo.miloun.com/api-reference/?lang=python) for every method,
the [platform notes](https://cosmo.miloun.com/platform-notes/) for PyICU's binding
limits, and [resources](https://cosmo.miloun.com/resources/) for ICU/CLDR references.

## Development

The dev environment is managed with [uv](https://docs.astral.sh/uv/), which
provisions a matching Python automatically. You still need the system ICU
libraries (e.g. `libicu-dev` + `pkg-config`) for PyICU to build and link.

```bash
uv run --extra test pytest      # run the test suite
uv build                        # build the wheel + sdist into dist/
```

`uv.lock` pins the dev/test toolchain for reproducible local runs and CI. It does
**not** affect anyone who `pip install cosmo-intl` — they resolve from the
dependency ranges in `pyproject.toml`.

## Errors

Recoverable problems raise `CosmoError`, with `InvalidArgumentError` and
`UnsupportedError` subclasses — an invalid currency in strict mode, an unsupported
unit, an unknown symbol name, an unformattable date, and the like.

## License

MIT © Aiden Adrian