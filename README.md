# Cosmo

Turn raw values — numbers, amounts, dates, codes — into the polished text your users
actually read. Effortlessly: no formatting code to write, no duplication to maintain.

Your app stores machine values — a number, a timestamp, a country code. Your users
want to read them the way their part of the world writes them. Cosmo does that
conversion in a single call, so you stop scattering ad-hoc formatting logic across
your codebase and delete the near-duplicate code that collects around it. It's dead
simple, production-ready, and fast.

You don't need a multi-language app to benefit — point Cosmo at a single region and
everything just comes out right. The same one line already scales to every language,
script, calendar and time zone if you ever grow, with no data to ship or maintain.

```text
  ┌─ iphone.json ───────────────────┐     ┌─ locale ──────────────────┐
  │ {                               │     │                           │
  │   "model":    "iPhone 17 Pro",  │     │   en_US · en_GB · pt_BR   │
  │   "price":    999,              │     │   zh_CN · ar_SA · hi_IN   │
  │   "speed":    2000,             │     │                           │
  │   "pixels":   1234567,          │     └─────────────┬─────────────┘
  │   "cameras":  3,                │                   │
  │   "released": "2025-09-19"      │                   │
  │ }                               │                   │
  └────────────────┬────────────────┘                   │
                   └─────────────────┬──────────────────┘
                                     ▼
                               ┌───────────┐
                               │   Cosmo   │
                               └─────┬─────┘
                                     ▼
   🇺🇸  United States   ─►  September 19, 2025 · $999.00 · 2,000 MB/s · 1,234,567 · 3 cameras
   🇬🇧  United Kingdom  ─►  19 September 2025 · £999.00 · 2,000 MB/s · 1,234,567 · 3 cameras
   🇧🇷  Brazil          ─►  19 de setembro de 2025 · R$ 999,00 · 2.000 MB/s · 1.234.567 · 3 câmeras
   🇨🇳  China           ─►  2025年9月19日 · ¥999.00 · 2,000 MB/秒 · 1,234,567 · 3 个摄像头
   🇸🇦  Saudi Arabia    ─►  ٢٧ ربيع الأول ١٤٤٧ هـ · ٩٩٩٫٠٠ ر.س. · ٢٬٠٠٠ م.ب/ث · ١٬٢٣٤٬٥٦٧ · ٣ كاميرات
   🇮🇳  India           ─►  19 सितंबर 2025 · ₹999.00 · 2,000 MB/से॰ · 12,34,567 · 3 कैमरे
```

You pass a locale code; Cosmo decides the rest. There's no currency in the data, yet
each region gets its own (`$` / `£` / `R$` / `¥` / `ر.س` / `₹`). The thousands separator
follows local habit — even India's `12,34,567` grouping — Saudi Arabia switches to the
Hijri calendar and right-to-left Arabic-Indic digits, and the camera count takes the
correct plural form. All automatically.

Cosmo is implemented consistently across five languages — the same concepts, method
names and behaviour:
[JavaScript](https://github.com/cosmo-intl/cosmo-js) ([docs](https://cosmo.miloun.com/?lang=js)) ·
**Python** ·
[Java](https://github.com/cosmo-intl/cosmo-java) ([docs](https://cosmo.miloun.com/?lang=java)) ·
[.NET / C#](https://github.com/cosmo-intl/cosmo-csharp) ·
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

Cosmo is built around the **locale** — a short language-and-region tag like `en_US`,
`de_DE` or `fa_IR` that picks all of these conventions at once. Everything it produces
is **locale-aware** and read straight from ICU/[CLDR](https://cldr.unicode.org/), so
coverage is complete and always current — no locale tables of your own to bundle or
keep up to date. All methods are `snake_case`. Underscore locales (`en_AU`) and [BCP-47](https://www.rfc-editor.org/info/bcp47)
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