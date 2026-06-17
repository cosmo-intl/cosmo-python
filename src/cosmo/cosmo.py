"""Cosmo — application localisation for Python.

A thin, ergonomic layer over **ICU** (reached through `PyICU`). It bundles **no**
locale data of its own — every result comes straight from ICU. PyICU exposes the
same raw ICU that PHP's ``ext-intl`` does, so this port can offer the full PHP
surface (RBNF ``spellout``/``ordinal``, CLDR ``quote``, raw resource ``get``,
arbitrary date ``patterns``) *and* the conveniences the JS port grew on top of
``Intl`` (``compact``, number/money/date ranges, ``relative_duration``, ``join``,
collation, segmentation, calendar metadata) — all without a single hardcoded
data table.

The only principled omission is the *weekend* days in :meth:`Cosmo.week_info`:
PyICU 2.16 does not bind ICU's ``getDayOfWeekType`` API, and the design rule
forbids hardcoding the data, so the weekend is left out rather than faked.
"""

from __future__ import annotations

import datetime as _dt
from typing import Callable, Iterable, Optional, Sequence, Union

import icu

from .bundle import Bundle
from .errors import CosmoError, InvalidArgumentError, UnsupportedError

__all__ = [
    "Cosmo",
    "Bundle",
    "CosmoError",
    "InvalidArgumentError",
    "UnsupportedError",
]

#: A moment in time accepted by the date/time methods: a :class:`datetime.datetime`,
#: a :class:`datetime.date`, or a POSIX timestamp in **seconds** (Python's
#: ``time.time()`` / ``datetime.timestamp()`` convention — note JS uses ms).
Moment = Union[_dt.datetime, _dt.date, int, float]

_VALID_WIDTHS = ("none", "short", "medium", "long", "full")

_DATE_STYLE = {
    "none": icu.DateFormat.kNone,
    "short": icu.DateFormat.kShort,
    "medium": icu.DateFormat.kMedium,
    "long": icu.DateFormat.kLong,
    "full": icu.DateFormat.kFull,
}

# full/long -> widest, medium -> short, short -> narrow. Mirrors the JS port's
# WIDTH_TO_UNIT_DISPLAY and is reused for units, lists, month/weekday names.
_MEASURE_WIDTH = {
    "none": icu.UMeasureFormatWidth.WIDE,
    "short": icu.UMeasureFormatWidth.NARROW,
    "medium": icu.UMeasureFormatWidth.SHORT,
    "long": icu.UMeasureFormatWidth.WIDE,
    "full": icu.UMeasureFormatWidth.WIDE,
}

_LIST_WIDTH = {
    "none": icu.UListFormatterWidth.WIDE,
    "short": icu.UListFormatterWidth.NARROW,
    "medium": icu.UListFormatterWidth.SHORT,
    "long": icu.UListFormatterWidth.WIDE,
    "full": icu.UListFormatterWidth.WIDE,
}

_LIST_TYPE = {
    "conjunction": icu.UListFormatterType.AND,
    "disjunction": icu.UListFormatterType.OR,
    "unit": icu.UListFormatterType.UNITS,
}

# Date-format-symbols width (for month_names / weekday_names).
_SYMBOL_WIDTH = {
    "none": icu.DateFormatSymbols.WIDE,
    "short": icu.DateFormatSymbols.NARROW,
    "medium": icu.DateFormatSymbols.ABBREVIATED,
    "long": icu.DateFormatSymbols.WIDE,
    "full": icu.DateFormatSymbols.WIDE,
}

_RELATIVE_UNIT = {
    "second": icu.URelativeDateTimeUnit.SECOND,
    "minute": icu.URelativeDateTimeUnit.MINUTE,
    "hour": icu.URelativeDateTimeUnit.HOUR,
    "day": icu.URelativeDateTimeUnit.DAY,
    "week": icu.URelativeDateTimeUnit.WEEK,
    "month": icu.URelativeDateTimeUnit.MONTH,
    "quarter": icu.URelativeDateTimeUnit.QUARTER,
    "year": icu.URelativeDateTimeUnit.YEAR,
}

_TZ_NAME_STYLE = {
    "long": icu.TimeZone.LONG,
    "short": icu.TimeZone.SHORT,
    "longOffset": icu.TimeZone.LONG_GMT,
    "shortOffset": icu.TimeZone.SHORT_GMT,
    "longGeneric": icu.TimeZone.LONG_GENERIC,
    "shortGeneric": icu.TimeZone.SHORT_GENERIC,
}

# Number-symbol names -> DecimalFormatSymbols constant. Keys are normalised:
# lower-cased with separators removed and any trailing "symbol"/"separator"/"sign".
_DFS = icu.DecimalFormatSymbols
_SYMBOLS = {
    "decimal": _DFS.kDecimalSeparatorSymbol,
    "grouping": _DFS.kGroupingSeparatorSymbol,
    "group": _DFS.kGroupingSeparatorSymbol,
    "pattern": _DFS.kPatternSeparatorSymbol,
    "percent": _DFS.kPercentSymbol,
    "permill": _DFS.kPerMillSymbol,
    "permille": _DFS.kPerMillSymbol,
    "minus": _DFS.kMinusSignSymbol,
    "plus": _DFS.kPlusSignSymbol,
    "currency": _DFS.kCurrencySymbol,
    "intlcurrency": _DFS.kIntlCurrencySymbol,
    "monetary": _DFS.kMonetarySeparatorSymbol,
    "exponential": _DFS.kExponentialSymbol,
    "exponent": _DFS.kExponentialSymbol,
    "nan": _DFS.kNaNSymbol,
    "infinity": _DFS.kInfinitySymbol,
    "digit": _DFS.kDigitSymbol,
    "zerodigit": _DFS.kZeroDigitSymbol,
    "zero": _DFS.kZeroDigitSymbol,
    "significantdigit": _DFS.kSignificantDigitSymbol,
    "significant": _DFS.kSignificantDigitSymbol,
    "padescape": _DFS.kPadEscapeSymbol,
    "pad": _DFS.kPadEscapeSymbol,
}


# Cross-port rounding-mode name -> NumberFormat.kRound* attribute (all have a
# direct ICU equivalent, matching the JS and PHP ports).
_ROUNDING_MODES = {
    "ceil": "kRoundCeiling",
    "floor": "kRoundFloor",
    "expand": "kRoundUp",
    "trunc": "kRoundDown",
    "halfExpand": "kRoundHalfUp",
    "halfTrunc": "kRoundHalfDown",
    "halfEven": "kRoundHalfEven",
}

# Every key a number-options dict may carry (built once; O(1) membership tests).
# The JS-only options are accepted but ignored here; anything else is a typo and raises.
_KNOWN_NUMBER_OPTIONS = frozenset({
    "minimum_integer_digits",
    "minimum_fraction_digits",
    "maximum_fraction_digits",
    "minimum_significant_digits",
    "maximum_significant_digits",
    "rounding_mode",
    "rounding_increment",
    "use_grouping",
    "sign_display",
    "trailing_zero_display",
    "rounding_priority",
    "notation",
    "compact_display",
})

# Every key a collation-options dict may carry (built once; O(1) membership tests).
_KNOWN_COLLATION_OPTIONS = frozenset({"numeric", "case_first"})

# Units accepted by duration() in its multi-unit (dict) form, longest first.
_DURATION_UNITS = (
    "years",
    "months",
    "weeks",
    "days",
    "hours",
    "minutes",
    "seconds",
    "milliseconds",
)


def _apply_number_options(fmt, options) -> None:
    """Apply a portable NumberOptions dict to an ICU NumberFormat.

    The JS-only options (``sign_display``, ``trailing_zero_display``,
    ``rounding_priority``, ``notation``, ``compact_display``) have no equivalent in
    ICU's legacy ``DecimalFormat`` and are silently ignored, matching the contract.
    """
    # ICU's NumberFormat defaults to HALF_EVEN (banker's rounding) whereas the JS
    # port inherits Intl.NumberFormat's HALF_EXPAND (round half away from zero).
    # Default to HALF_EXPAND so money/number/percentage round identically across
    # ports; an explicit ``rounding_mode`` option below still overrides this.
    fmt.setRoundingMode(fmt.kRoundHalfUp)
    if not options:
        return
    for key in options:
        if key not in _KNOWN_NUMBER_OPTIONS:
            raise InvalidArgumentError(f'"{key}" is not a valid number option.')
    if "minimum_integer_digits" in options:
        fmt.setMinimumIntegerDigits(options["minimum_integer_digits"])
    if "minimum_fraction_digits" in options:
        fmt.setMinimumFractionDigits(options["minimum_fraction_digits"])
    if "maximum_fraction_digits" in options:
        fmt.setMaximumFractionDigits(options["maximum_fraction_digits"])
    # ICU treats significant-digit limits as mutually exclusive with fraction
    # digits; the setters turn the significant-digit mode on.
    if "minimum_significant_digits" in options:
        fmt.setMinimumSignificantDigits(options["minimum_significant_digits"])
    if "maximum_significant_digits" in options:
        fmt.setMaximumSignificantDigits(options["maximum_significant_digits"])
    if "use_grouping" in options:
        fmt.setGroupingUsed(bool(options["use_grouping"]))
    if options.get("rounding_increment") is not None:
        # Match the JS/Intl contract: the increment is expressed in units of the
        # last fraction digit (e.g. increment 5 at 2 fraction digits → step 0.05),
        # whereas ICU's setRoundingIncrement takes the literal step value.
        scale = options.get("maximum_fraction_digits", 0)
        fmt.setRoundingIncrement(options["rounding_increment"] * (10 ** -scale))
    mode = options.get("rounding_mode")
    if mode is not None:
        const = _ROUNDING_MODES.get(mode)
        if const is None:
            raise InvalidArgumentError(
                f'"{mode}" is not a valid rounding mode '
                f"(use {'/'.join(_ROUNDING_MODES)})."
            )
        fmt.setRoundingMode(getattr(fmt, const))


def _apply_collation_options(collator, options) -> None:
    """Apply portable collation tailoring (numeric, case_first) to an ICU Collator."""
    if not options:
        return
    for key in options:
        if key not in _KNOWN_COLLATION_OPTIONS:
            raise InvalidArgumentError(f'"{key}" is not a valid collation option.')
    if "numeric" in options:
        collator.setAttribute(
            icu.UCollAttribute.NUMERIC_COLLATION,
            icu.UCollAttributeValue.ON if options["numeric"] else icu.UCollAttributeValue.OFF,
        )
    case_first = options.get("case_first")
    if case_first is not None:
        value = {
            "upper": icu.UCollAttributeValue.UPPER_FIRST,
            "lower": icu.UCollAttributeValue.LOWER_FIRST,
            "false": icu.UCollAttributeValue.OFF,
        }.get(case_first)
        if value is None:
            raise InvalidArgumentError(f'"{case_first}" is not a valid case_first value.')
        collator.setAttribute(icu.UCollAttribute.CASE_FIRST, value)


def _assert_width(width: str) -> str:
    if width not in _DATE_STYLE:
        raise InvalidArgumentError(
            f'"{width}" is not a valid format width (use {"/".join(_VALID_WIDTHS)}).'
        )
    return width


def _to_seconds(moment: Moment) -> float:
    """Normalise a :data:`Moment` to a POSIX timestamp in seconds."""
    if isinstance(moment, _dt.datetime):
        return moment.timestamp()
    if isinstance(moment, _dt.date):
        # Anchor a bare calendar date at noon UTC so it renders as the same day
        # in every practical formatting time zone (no day-boundary drift).
        return _dt.datetime(
            moment.year, moment.month, moment.day, 12, tzinfo=_dt.timezone.utc
        ).timestamp()
    return float(moment)


def _formattable(value) -> "icu.Formattable":
    if isinstance(value, _dt.datetime):
        return icu.Formattable(value.timestamp(), icu.Formattable.kIsDate)
    if isinstance(value, bool):  # bool is an int subclass — guard first
        return icu.Formattable(int(value))
    return icu.Formattable(value)


class Cosmo:
    """A locale-aware formatter. Construct once per locale and reuse."""

    def __init__(self, locale: Optional[str] = None, modifiers: Optional[dict] = None):
        """
        :param locale: BCP-47 / underscore locale id (``en_AU``, ``fa-IR``,
            ``en_AU@calendar=buddhist``). Defaults to the system locale.
        :param modifiers: optional overrides — ``calendar``, ``currency`` and
            ``timeZone`` (the legacy lowercase ``timezone`` key is accepted too).
        """
        raw = (locale or "").replace("-", "_").strip() or icu.Locale.getDefault().getName()
        self._loc = icu.Locale.createCanonical(raw)
        #: Canonical ICU locale id, e.g. ``"en_AU"``.
        self.locale = self._loc.getName()

        self.subtags = {
            "language": self._loc.getLanguage(),
            "script": self._loc.getScript(),
            "region": self._loc.getCountry(),
        }

        modifiers = dict(modifiers or {})
        if "timezone" in modifiers and "timeZone" not in modifiers:
            modifiers["timeZone"] = modifiers.pop("timezone")
        modifiers.setdefault("calendar", self._loc.getKeywordValue("calendar") or None)
        modifiers.setdefault("currency", None)
        modifiers.setdefault("timeZone", None)

        # PHP-style region -> currency inference (ICU-backed, no data table).
        if self.subtags["region"] and not modifiers["currency"]:
            code = icu.NumberFormat.createCurrencyInstance(self._loc).getCurrency()
            if code and code != "XXX":
                modifiers["currency"] = code

        self.modifiers = modifiers

    # ------------------------------------------------------------------ #
    # constructors
    # ------------------------------------------------------------------ #

    @classmethod
    def from_subtags(cls, subtags: dict, modifiers: Optional[dict] = None) -> "Cosmo":
        """Build from a subtag dict, e.g. ``{"language": "en", "region": "AU"}``."""
        builder = icu.LocaleBuilder()
        if subtags.get("language"):
            builder.setLanguage(subtags["language"])
        if subtags.get("script"):
            builder.setScript(subtags["script"])
        if subtags.get("region"):
            builder.setRegion(subtags["region"])
        return cls(builder.build().getName(), modifiers)

    @classmethod
    def from_accept_language(
        cls,
        header: str,
        modifiers: Optional[dict] = None,
        supported: Optional[Sequence[str]] = None,
    ) -> "Cosmo":
        """Build from an HTTP ``Accept-Language`` header.

        Without ``supported``, picks the highest-quality tag. With ``supported``
        (the locale ids your app ships), negotiates the best match using ICU's
        ``LocaleMatcher`` (CLDR language-distance data) and builds the matching
        *supported* locale — falling back to the first one.
        """
        tags = cls._parse_accept_language(header)
        if supported is None:
            return cls(tags[0] if tags else None, modifiers)
        return cls(cls._best_match(tags, supported), modifiers)

    @staticmethod
    def _parse_accept_language(header: str) -> list:
        """Header tags ordered by descending quality (ties keep header order)."""
        entries = []
        for part in (header or "").split(","):
            piece = part.strip()
            if not piece:
                continue
            tag, _, params = piece.partition(";")
            tag = tag.strip()
            if not tag or tag == "*":
                continue
            q = 1.0
            for p in params.split(";"):
                p = p.strip()
                if p.startswith("q="):
                    try:
                        q = float(p[2:])
                    except ValueError:
                        q = 0.0
            entries.append((tag, q))
        entries.sort(key=lambda entry: -entry[1])  # stable sort
        return [tag for tag, _ in entries]

    def best_match(self, supported: Sequence[str]) -> str:
        """The supported locale that best serves this locale, using CLDR
        language-distance data — e.g. ``en_AU`` picks ``en-GB`` over ``en-US``,
        and ``sr-Latn`` is served better by ``hr`` than by ``sr-Cyrl``. Falls
        back to the first supported locale when nothing matches well.

        :returns: the matching entry exactly as it appears in ``supported``.
        """
        return self._best_match([self.locale], supported)

    @staticmethod
    def _best_match(desired: Sequence[str], supported: Sequence[str]) -> str:
        if not supported:
            raise InvalidArgumentError("At least one supported locale is required.")
        originals: dict = {}
        builder = icu.LocaleMatcher.Builder()
        for tag in supported:
            loc = icu.Locale(tag.replace("-", "_"))
            originals.setdefault(loc.getName(), tag)
            builder.addSupportedLocale(loc)
        desired_locales = [icu.Locale(t.replace("-", "_")) for t in desired]
        if not desired_locales:
            return next(iter(originals.values()))
        # The default match (when nothing comes close) is the first supported locale.
        match = builder.build().getBestMatch(desired_locales)
        return originals[match.getName()]

    # ------------------------------------------------------------------ #
    # resource-bundle access
    # ------------------------------------------------------------------ #

    def get(self, bundle_name: str, *path: str):
        """Read a value from an ICU resource bundle, falling back locale → language → root.

        Returns a leaf value (str/int) or a nested :class:`icu.ResourceBundle`;
        ``None`` if the path is absent. Mirrors the PHP port's ``get()``.
        """
        for loc in (self.locale, self._loc.getLanguage(), "root"):
            result = self._extract(loc, bundle_name, path)
            if result is not None:
                return result
        return None

    @staticmethod
    def _extract(locale: str, bundle_name: str, path: Sequence[str]):
        try:
            current = icu.ResourceBundle(bundle_name, icu.Locale(locale))
        except Exception:
            return None
        for key in path:
            try:
                current = current.get(key)
            except Exception:
                return None
        if isinstance(current, icu.ResourceBundle):
            # Collapse a string leaf to its value for convenience.
            try:
                return current.getString()
            except Exception:
                return current
        return current

    # ------------------------------------------------------------------ #
    # key -> value lookups
    # ------------------------------------------------------------------ #

    def language(self, code: Optional[str] = None) -> str:
        """Localised language name (``"en"`` → ``"English"``)."""
        code = self.locale if code is None else code
        if not code:
            return ""
        return icu.Locale(code.replace("-", "_")).getDisplayLanguage(self._loc)

    def country(self, code: Optional[str] = None) -> str:
        """Localised country/region name (``"AU"`` → ``"Australia"``)."""
        if code is None:
            code = self.subtags["region"]
        if not code:
            return ""
        # Locale needs a region context: prefix a bare region with "_".
        loc = code.replace("-", "_")
        if "_" not in loc:
            loc = "_" + loc
        return icu.Locale(loc).getDisplayCountry(self._loc)

    def script(self, code: Optional[str] = None) -> str:
        """Localised script name (``"Hans"`` → ``"Simplified"``).

        Reads the CLDR ``Scripts`` table like the PHP port (and like JS's
        ``Intl.DisplayNames``); ``getDisplayScript`` would return the
        stand-alone variant ("Simplified Han") and disagree with both.
        """
        if code is None:
            code = self.subtags["script"]
        if not code:
            return ""
        return str(self.get(Bundle.LANGUAGE, "Scripts", code.title()) or "")

    def calendar(self, code: str) -> str:
        """Localised calendar name (``"buddhist"`` → ``"Buddhist Calendar"``)."""
        if not code:
            return ""
        return str(self.get(Bundle.LANGUAGE, "Types", "calendar", code) or "")

    def direction(self, language: Optional[str] = None) -> str:
        """Text direction of the locale (or a given language): ``"rtl"`` or ``"ltr"``."""
        language = self.locale if language is None else language
        try:
            # Resolve the (likely) script via maximisation, then ask ICU whether
            # that script is right-to-left. Script-based detection covers minority
            # RTL languages (e.g. Dhivehi/Thaana, N'Ko) that carry no locale-level
            # `layout` data — the old bundle lookup silently fell back to "ltr".
            loc = icu.Locale(language.replace("-", "_")).addLikelySubtags()
            script = loc.getScript()
            if not script:
                return "ltr"
            code = icu.Script.getCode(script)[0]
            return "rtl" if icu.Script(code).isRightToLeft() else "ltr"
        except Exception:
            return "ltr"

    def flag(self, country: Optional[str] = None) -> str:
        """Country flag emoji for a region (``"AU"`` → ``"🇦🇺"``). Pure codepoint math."""
        if country is None:
            country = self.subtags["region"]
        country = (country or "").upper()
        if len(country) != 2 or not country.isalpha():
            return ""
        # 0x1F1E6 (regional indicator A) minus ord('A').
        offset = 0x1F1E6 - ord("A")
        return chr(ord(country[0]) + offset) + chr(ord(country[1]) + offset)

    def currency(
        self,
        code: Optional[str] = None,
        symbol: bool = False,
        strict: bool = False,
    ) -> str:
        """Localised currency name (default) or symbol.

        :param code: ISO 4217 code; defaults to the ``currency`` modifier.
        :param symbol: return the disambiguated symbol (``"A$"``) instead of the name.
        :param strict: raise on an unknown code instead of echoing it back.
        """
        code = self.modifiers["currency"] if code is None else code
        code = (code or "").upper()
        if not code:
            return ""
        entry = self.get(Bundle.CURRENCY, "Currencies", code)
        if entry is None or not isinstance(entry, icu.ResourceBundle):
            if strict:
                raise InvalidArgumentError(f'"{code}" is not a valid currency code.')
            return code
        return entry.get(0).getString() if symbol else entry.get(1).getString()

    # ------------------------------------------------------------------ #
    # numbers
    # ------------------------------------------------------------------ #

    def number(self, value: float, options: Optional[dict] = None) -> str:
        """Format a number with the locale's default decimal format.

        :param options: optional number-formatting controls — ``minimum_integer_digits``,
            ``minimum_fraction_digits``, ``maximum_fraction_digits``,
            ``minimum_significant_digits``, ``maximum_significant_digits``,
            ``rounding_mode``, ``rounding_increment``, ``use_grouping`` (all portable
            across the JS/PHP ports). The JS-only options (``sign_display``,
            ``trailing_zero_display``, ``rounding_priority``, ``notation``,
            ``compact_display``) have no ICU equivalent here and are ignored.
        """
        fmt = icu.NumberFormat.createInstance(self._loc)
        _apply_number_options(fmt, options)
        return fmt.format(value)

    def precision(self, value: float, fraction_digits: int = 2, options: Optional[dict] = None) -> str:
        """Format a number with a fixed number of fraction digits.

        Always exactly ``fraction_digits`` digits (default 2), padding with trailing
        zeros and rounding as needed: ``1`` renders as ``"1.00"`` and ``1.002`` stays
        ``"1.00"``, never ``"1.0"``. Pass an
        ``options`` bag (see :meth:`number`) to widen the band — e.g.
        ``{"maximum_fraction_digits": 3}`` — or tweak rounding/grouping.
        """
        fmt = icu.NumberFormat.createInstance(self._loc)
        fmt.setMinimumFractionDigits(fraction_digits)
        fmt.setMaximumFractionDigits(fraction_digits)
        _apply_number_options(fmt, options)
        return fmt.format(value)

    def percentage(self, value: float, precision: int = 3, options: Optional[dict] = None) -> str:
        """Format a fraction as a percentage (``0.2`` → ``"20%"``)."""
        fmt = icu.NumberFormat.createPercentInstance(self._loc)
        fmt.setMaximumFractionDigits(precision)
        _apply_number_options(fmt, options)
        return fmt.format(value)

    def money(
        self,
        value: float,
        code: Optional[str] = None,
        precision: Optional[int] = None,
        strict: bool = False,
        options: Optional[dict] = None,
    ) -> str:
        """Format a monetary value.

        With no ``code`` the ``currency`` modifier is used (inferred from the
        region when the locale has one). Returns ``""`` when no currency is
        available, unless ``strict``.
        """
        code = self.modifiers["currency"] if code is None else code
        code = (code or "").upper()
        if not code:
            if strict:
                raise InvalidArgumentError(
                    "No currency provided. Pass a code or set the `currency` modifier."
                )
            return ""
        # A malformed code makes ICU raise a raw ICUError (or mangle the output);
        # reject it up front so every port raises the same branded error.
        if not (len(code) == 3 and code.isascii() and code.isalpha()):
            raise InvalidArgumentError(f'"{code}" is not a valid currency code.')
        fmt = icu.NumberFormat.createCurrencyInstance(self._loc)
        fmt.setCurrency(code)
        if precision is not None:
            fmt.setMinimumFractionDigits(precision)
            fmt.setMaximumFractionDigits(precision)
        _apply_number_options(fmt, options)
        return fmt.format(value)

    def symbol(self, name: str) -> str:
        """Return a localised number symbol (``"decimal"``, ``"percent"``, …).

        Accepts any ``DecimalFormatSymbols`` name (case-insensitive; the
        ``_symbol``/``_separator``/``_sign`` suffixes and separators are ignored).
        """
        key = name.lower().replace("_", "").replace("-", "").replace(" ", "")
        for suffix in ("symbol", "separator", "sign"):
            if key.endswith(suffix) and key != suffix:
                key = key[: -len(suffix)]
        constant = _SYMBOLS.get(key)
        if constant is None:
            raise InvalidArgumentError(f'"{name}" is not a valid number-symbol name.')
        return icu.DecimalFormatSymbols(self._loc).getSymbol(constant)

    def unit(self, category: str, unit: str, value: float, width: str = "full") -> str:
        """Format a measurement with a localised unit (``2.19`` gigabytes).

        :param category: informational grouping (e.g. ``"digital"``); not required by ICU.
        :param unit: ICU unit identifier, e.g. ``"gigabyte"``, ``"celsius"``,
            ``"mile-per-hour"``.
        :param width: ``full``/``long`` → wide, ``medium`` → short, ``short`` → narrow.
        """
        del category  # accepted for descriptive parity; ICU derives it from the unit.
        try:
            measure_unit = icu.MeasureUnit.forIdentifier(unit)
        except Exception:
            raise InvalidArgumentError(f'"{unit}" is not a unit supported by ICU.')
        fmt = icu.MeasureFormat(self._loc, _MEASURE_WIDTH[_assert_width(width)])
        return fmt.formatMeasures([icu.Measure(value, measure_unit)])

    def scientific(self, value: float) -> str:
        """Scientific notation (``12345`` → ``"1.2345E4"``)."""
        return icu.NumberFormat.createScientificInstance(self._loc).format(value)

    def compact(self, value: float, width: str = "short") -> str:
        """Compact notation (``1200`` → ``"1.2K"`` or ``"1.2 thousand"``)."""
        notation = (
            icu.Notation.compactLong() if width in ("full", "long") else icu.Notation.compactShort()
        )
        fmt = icu.NumberFormatter.withLocale(self._loc).notation(notation)
        return str(fmt.formatDouble(float(value)))

    def ordinal(self, number: int) -> str:
        """Ordinal text (``1`` → ``"1st"``). Uses ICU RBNF."""
        return icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.ORDINAL, self._loc).format(number)

    def spellout(self, number: float) -> str:
        """Spell a number out (``42`` → ``"forty-two"``). Uses ICU RBNF."""
        return icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.SPELLOUT, self._loc).format(number)

    def duration(self, value, with_words: bool = False) -> str:
        """Format an **undirected** duration.

        :param value: either a number of **seconds** (rendered as the
            ``"339:17:20"`` clock form) or a **dict of units** —
            ``{"hours": 3, "minutes": 5}`` — for multi-unit output
            (``"3 hours, 5 minutes"``). Accepted units: years, months, weeks,
            days, hours, minutes, seconds, milliseconds.
        :param with_words: scalar form → spell the units out where the locale's
            RBNF has a ``%with-words`` ruleset; dict form → wide units (vs the
            abbreviated default). Directed ("3 days ago") form:
            :meth:`relative_duration`.
        """
        if isinstance(value, dict):
            return self._duration_parts(value, with_words)
        fmt = icu.RuleBasedNumberFormat(icu.URBNFRuleSetTag.DURATION, self._loc)
        if with_words:
            try:
                fmt.setDefaultRuleSet("%with-words")
            except Exception:
                pass
        return fmt.format(value)

    def _duration_parts(self, parts: dict, with_words: bool) -> str:
        # PyICU's MeasureFormat.formatMeasures binds only a single measure, so
        # format each unit and join with the locale's CLDR unit-list pattern.
        width = icu.UMeasureFormatWidth.WIDE if with_words else icu.UMeasureFormatWidth.SHORT
        list_width = icu.UListFormatterWidth.WIDE if with_words else icu.UListFormatterWidth.SHORT
        mf = icu.MeasureFormat(self._loc, width)
        pieces = []
        for unit in _DURATION_UNITS:
            amount = parts.get(unit)
            if amount:
                measure = icu.Measure(float(amount), icu.MeasureUnit.forIdentifier(unit[:-1]))
                pieces.append(mf.formatMeasures([measure]))
        if not pieces:
            return ""
        lf = icu.ListFormatter.createInstance(self._loc, icu.UListFormatterType.UNITS, list_width)
        return lf.format(pieces)

    # ------------------------------------------------------------------ #
    # dates & times
    # ------------------------------------------------------------------ #

    def _calendar_locale(self, calendar: Optional[str]) -> "icu.Locale":
        cal = calendar if calendar is not None else self.modifiers["calendar"]
        loc = icu.Locale(self.locale)
        if cal:
            loc.setKeywordValue("calendar", "gregorian" if cal == "gregorian" else cal)
        return loc

    def _apply_timezone(self, formatter) -> None:
        if self.modifiers["timeZone"]:
            formatter.setTimeZone(icu.TimeZone.createTimeZone(self.modifiers["timeZone"]))

    def moment(
        self,
        value: Moment,
        date_width: str = "short",
        time_width: str = "short",
        calendar: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> str:
        """Format a date and/or time using the locale's conventions.

        :param date_width / time_width: ``none``/``short``/``medium``/``long``/``full``.
        :param calendar: ``"gregorian"`` forces Gregorian; otherwise the
            locale/modifier calendar is used.
        :param pattern: optional raw ICU date/time pattern (overrides the widths).
        """
        _assert_width(date_width)
        _assert_width(time_width)
        loc = self._calendar_locale(calendar)

        if pattern:
            fmt = icu.SimpleDateFormat(pattern, loc)
        elif date_width == "none" and time_width == "none":
            return ""
        elif time_width == "none":
            fmt = icu.DateFormat.createDateInstance(_DATE_STYLE[date_width], loc)
        elif date_width == "none":
            fmt = icu.DateFormat.createTimeInstance(_DATE_STYLE[time_width], loc)
        else:
            fmt = icu.DateFormat.createDateTimeInstance(
                _DATE_STYLE[date_width], _DATE_STYLE[time_width], loc
            )
        self._apply_timezone(fmt)
        return fmt.format(_to_seconds(value))

    def date(self, value: Moment, width: str = "short") -> str:
        """Format just the date part of a moment."""
        return self.moment(value, width, "none")

    def time(self, value: Moment, width: str = "short") -> str:
        """Format just the time (clock) part of a moment."""
        return self.moment(value, "none", width)

    def format_moment(self, value: Moment, pattern: str, calendar: Optional[str] = None) -> str:
        """Format a moment with a raw ICU pattern (``"yyyy-MM-dd"``)."""
        return self.moment(value, "none", "none", calendar, pattern)

    def date_range(
        self,
        start: Moment,
        end: Moment,
        date_width: str = "medium",
        time_width: str = "none",
    ) -> str:
        """Format a moment range (``"2–5 Feb 2020"``)."""
        _assert_width(date_width)
        _assert_width(time_width)
        skeleton = _RANGE_SKELETON.get((date_width, time_width))
        if skeleton is None:
            raise InvalidArgumentError(
                "date_range supports the documented width combinations only."
            )
        fmt = icu.DateIntervalFormat.createInstance(skeleton, self._calendar_locale(None))
        interval = icu.DateInterval(_to_seconds(start), _to_seconds(end))
        return fmt.format(interval)

    # ------------------------------------------------------------------ #
    # collation
    # ------------------------------------------------------------------ #

    def compare(self, a: str, b: str, options: Optional[dict] = None) -> int:
        """Locale-aware comparison of two strings (``-1`` / ``0`` / ``1``).

        :param options: optional collation tailoring — ``numeric`` (bool) and
            ``case_first`` (``"upper"``/``"lower"``/``"false"``).
        """
        collator = icu.Collator.createInstance(self._loc)
        _apply_collation_options(collator, options)
        return collator.compare(a, b)

    def sort(self, items: Iterable, key: Optional[Callable] = None, options: Optional[dict] = None) -> list:
        """Return a new list sorted by the locale's collation rules.

        :param options: optional collation tailoring (see :meth:`compare`).
        """
        collator = icu.Collator.createInstance(self._loc)
        _apply_collation_options(collator, options)
        get = key or (lambda x: str(x))
        return sorted(items, key=lambda item: collator.getSortKey(get(item)))

    def contains(
        self,
        haystack: str,
        needle: str,
        sensitivity: str = "base",
        options: Optional[dict] = None,
    ) -> bool:
        """Locale-aware substring test (accents/case can be ignored).

        :param sensitivity: ``base`` (ignore case & accents, default), ``accent``,
            ``case``, or ``variant`` (exact).
        :param options: optional collation tailoring (see :meth:`compare`).
        """
        if needle == "":
            return True
        if sensitivity not in ("base", "accent", "case", "variant"):
            raise InvalidArgumentError(f'"{sensitivity}" is not a valid sensitivity.')
        collator = icu.Collator.createInstance(self._loc)
        if sensitivity == "base":
            collator.setStrength(icu.Collator.PRIMARY)
        elif sensitivity == "accent":
            collator.setStrength(icu.Collator.SECONDARY)
        elif sensitivity == "case":
            # Distinguish case but not accents: PRIMARY so "à" = "a",
            # plus CASE_LEVEL so "a" ≠ "A". Mirrors PHP/Java.
            collator.setStrength(icu.Collator.PRIMARY)
            collator.setAttribute(icu.UCollAttribute.CASE_LEVEL, icu.UCollAttributeValue.ON)
        else:  # variant
            # All differences matter; TERTIARY matches PHP/Java.
            # IDENTICAL would also reject normalisation differences, which
            # the JS Intl definition does not require.
            collator.setStrength(icu.Collator.TERTIARY)
        _apply_collation_options(collator, options)
        hay = self._graphemes(haystack)
        need_len = len(self._graphemes(needle))
        for i in range(0, len(hay) - need_len + 1):
            if collator.compare("".join(hay[i : i + need_len]), needle) == 0:
                return True
        return False

    # ------------------------------------------------------------------ #
    # text segmentation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _u16_slicer(text: str):
        # ICU BreakIterator boundaries are UTF-16 code-unit offsets, which differ
        # from Python's codepoint indices for non-BMP characters (emoji). Slice on
        # a UTF-16-LE buffer so segments stay correct across the whole BMP+SMP.
        buf = text.encode("utf-16-le")
        return lambda s, e: buf[s * 2 : e * 2].decode("utf-16-le")

    def _graphemes(self, text: str) -> list:
        it = icu.BreakIterator.createCharacterInstance(self._loc)
        it.setText(text)
        slice16 = self._u16_slicer(text)
        out, start = [], it.first()
        for end in it:
            out.append(slice16(start, end))
            start = end
        return out

    def split_words(self, text: str) -> list:
        """Split text into words (drops whitespace/punctuation)."""
        it = icu.BreakIterator.createWordInstance(self._loc)
        it.setText(text)
        slice16 = self._u16_slicer(text)
        out, start = [], it.first()
        for end in it:
            if it.getRuleStatus() != icu.UWordBreak.NONE:
                out.append(slice16(start, end))
            start = end
        return out

    def split_sentences(self, text: str) -> list:
        """Split text into sentences using the locale's boundary rules."""
        it = icu.BreakIterator.createSentenceInstance(self._loc)
        it.setText(text)
        slice16 = self._u16_slicer(text)
        out, start = [], it.first()
        for end in it:
            piece = slice16(start, end).strip()
            if piece:
                out.append(piece)
            start = end
        return out

    def ellipsize(self, text: str, max_graphemes: int, ellipsis: str = "…") -> str:
        """Truncate to at most ``max_graphemes`` graphemes on a word boundary."""
        graphemes = self._graphemes(text)
        if len(graphemes) <= max_graphemes:
            return text
        budget = max(0, max_graphemes - len(self._graphemes(ellipsis)))
        head = "".join(graphemes[:budget])
        # Prefer to cut at the last word-break *boundary* that still fits (like the
        # JS/PHP ports). split_words is the wrong tool here: it drops non-word
        # segments (spaces, emoji, punctuation), so a head like "👩‍👧‍👦 fa" looks
        # like a single word and the partial-word backoff would never fire.
        it = icu.BreakIterator.createWordInstance(self._loc)
        it.setText(head)
        boundary = it.preceding(len(head.encode("utf-16-le")) // 2)
        if boundary > 0:
            cut = self._u16_slicer(head)(0, boundary).rstrip()
            if cut:
                return cut + ellipsis
        return head.rstrip() + ellipsis

    def split_graphemes(self, text: str) -> list:
        """Split text into grapheme clusters (combining marks / emoji stay intact)."""
        return self._graphemes(text)

    # ------------------------------------------------------------------ #
    # messages, plurals, quoting
    # ------------------------------------------------------------------ #

    def message(self, pattern: str, args=None) -> str:
        """Format an ICU MessageFormat pattern.

        ``args`` may be a dict (named placeholders) or a list/tuple (positional).
        """
        fmt = icu.MessageFormat(pattern, self._loc)
        if args is None:
            args = {}
        if isinstance(args, dict):
            names = list(args.keys())
            values = [_formattable(args[k]) for k in names]
            return fmt.format(names, values)
        return fmt.format([_formattable(v) for v in args])

    def plural_category(self, value, ordinal: bool = False) -> str:
        """The LDML plural category for ``value`` (``1`` → ``"one"``).

        :param ordinal: use ordinal rules (1st/2nd/3rd …) instead of cardinal.
        """
        if ordinal:
            pattern = (
                "{0,selectordinal,zero{zero}one{one}two{two}few{few}many{many}other{other}}"
            )
            return icu.MessageFormat(pattern, self._loc).format([_formattable(value)])
        return icu.PluralRules.forLocale(self._loc).select(value)

    def quote(self, text: str) -> str:
        """Wrap text in the locale's quotation marks (``"x"`` in en, ``«x»`` in fa)."""
        start = self.get(Bundle.LOCALE, "delimiters", "quotationStart") or '"'
        end = self.get(Bundle.LOCALE, "delimiters", "quotationEnd") or '"'
        return f"{start}{text}{end}"

    def join(self, items: Sequence[str], type: str = "conjunction", width: str = "full") -> str:
        """Join a list the locale's way (``"A, B and C"``).

        :param type: ``conjunction`` (and), ``disjunction`` (or), or ``unit``.
        """
        list_type = _LIST_TYPE.get(type)
        if list_type is None:
            raise InvalidArgumentError(f'"{type}" is not a valid list type.')
        fmt = icu.ListFormatter.createInstance(self._loc, list_type, _LIST_WIDTH[_assert_width(width)])
        return fmt.format(list(items))

    # ------------------------------------------------------------------ #
    # relative durations & ranges
    # ------------------------------------------------------------------ #

    def relative_duration(self, amount: float, unit: str, numeric: str = "always") -> str:
        """Render a directed duration (``(-3, "day")`` → ``"3 days ago"``).

        :param amount: signed — negative = past (``"… ago"``), positive = future (``"in …"``).
        :param unit: ``second``/``minute``/``hour``/``day``/``week``/``month``/``quarter``/``year``.
        :param numeric: ``always`` (default, "1 day ago"). ``"auto"`` is accepted
            but PyICU does not expose ICU's auto word-forms ("yesterday") cleanly,
            so the numeric form is produced either way — never a wrong result.
        """
        rel = _RELATIVE_UNIT.get(unit)
        if rel is None:
            raise InvalidArgumentError(f'"{unit}" is not a valid relative unit.')
        return icu.RelativeDateTimeFormatter(self._loc).formatNumeric(amount, rel)

    def relative_duration_between(
        self,
        target: Moment,
        reference: Optional[Moment] = None,
        numeric: str = "auto",
    ) -> str:
        """Directed duration **between two moments** (``"in 5 days"``, ``"3 days ago"``).

        Computes ``target − reference`` (``reference`` defaults to now) and picks
        the largest sensible unit.
        """
        ref = _dt.datetime.now().timestamp() if reference is None else _to_seconds(reference)
        diff = _to_seconds(target) - ref
        divisions = [
            (60, "second"),
            (60, "minute"),
            (24, "hour"),
            (7, "day"),
            (4.34524, "week"),
            (12, "month"),
            (float("inf"), "year"),
        ]
        amount = diff
        for size, unit in divisions:
            if abs(amount) < size:
                return self.relative_duration(round(amount), unit, numeric)
            amount /= size
        return self.relative_duration(round(amount), "year", numeric)

    def number_range(self, start: float, end: float) -> str:
        """Format a numeric range (``"3–5"``)."""
        nrf = icu.NumberRangeFormatter.withLocale(self._loc)
        return str(nrf.formatDoubleRange(float(start), float(end)))

    def money_range(self, start: float, end: float, code: Optional[str] = None) -> str:
        """Format a monetary range (``"$3.00 – $5.00"``). ``""`` if no currency."""
        code = self.modifiers["currency"] if code is None else code
        code = (code or "").upper()
        if not code:
            return ""
        both = icu.NumberFormatter.with_().unit(icu.CurrencyUnit(code))
        nrf = icu.NumberRangeFormatter.withLocale(self._loc).numberFormatterBoth(both)
        return str(nrf.formatDoubleRange(float(start), float(end)))

    # ------------------------------------------------------------------ #
    # locale metadata
    # ------------------------------------------------------------------ #

    def add_likely_subtags(self) -> "Cosmo":
        """A new Cosmo with likely subtags added (``"en"`` → ``"en_Latn_US"``)."""
        loc = icu.Locale(self.locale)
        loc.addLikelySubtags()
        return Cosmo(loc.getName(), dict(self.modifiers))

    def remove_likely_subtags(self) -> "Cosmo":
        """A new Cosmo with likely subtags removed (``"en_Latn_US"`` → ``"en"``)."""
        loc = icu.Locale(self.locale)
        loc.minimizeSubtags()
        return Cosmo(loc.getName(), dict(self.modifiers))

    def month_names(self, width: str = "full") -> list:
        """Localised month names, following the active calendar."""
        cal = self.modifiers["calendar"]
        if not cal:
            # Resolve the calendar the locale implies (e.g. fa_IR -> persian).
            cal = icu.Calendar.createInstance(self._loc).getType()
        elif cal == "gregorian":
            cal = "gregorian"
        symbols = icu.DateFormatSymbols(self._loc, cal)
        names = symbols.getMonths(icu.DateFormatSymbols.FORMAT, _SYMBOL_WIDTH[_assert_width(width)])
        return [n for n in names if n]

    def weekday_names(self, width: str = "full") -> list:
        """Localised weekday names, **Sunday first** (ICU symbol order)."""
        symbols = icu.DateFormatSymbols(self._loc)
        days = symbols.getWeekdays(icu.DateFormatSymbols.FORMAT, _SYMBOL_WIDTH[_assert_width(width)])
        # ICU returns 8 entries with index 0 empty and 1..7 = Sunday..Saturday.
        return [d for d in days if d]

    def week_info(self) -> dict:
        """Week conventions: ``first_day`` (1=Mon…7=Sun) and ``minimal_days``.

        The weekend days are intentionally omitted: PyICU does not expose ICU's
        ``getDayOfWeekType``, and the library bundles no data of its own.
        """
        cal = icu.Calendar.createInstance(self._loc)
        # ICU first day is 1=Sunday..7=Saturday; convert to ISO 1=Monday..7=Sunday.
        first = ((cal.getFirstDayOfWeek() + 5) % 7) + 1
        return {"first_day": first, "minimal_days": cal.getMinimalDaysInFirstWeek()}

    def time_zone_name(self, style: str = "long") -> str:
        """Display name of the ``timeZone`` modifier (or the system zone)."""
        tz_id = self.modifiers["timeZone"]
        tz = (
            icu.TimeZone.createTimeZone(tz_id) if tz_id else icu.TimeZone.createDefault()
        )
        tz_style = _TZ_NAME_STYLE.get(style)
        if tz_style is None:
            raise InvalidArgumentError(f'"{style}" is not a valid time-zone name style.')
        return tz.getDisplayName(False, tz_style, self._loc)

    def display_name(self, type: str, code: str) -> str:
        """Generic localised display name — one entry point over the dedicated lookups.

        :param type: ``language``, ``region``, ``script``, ``calendar``, or ``currency``.
        """
        dispatch = {
            "language": self.language,
            "region": self.country,
            "script": self.script,
            "calendar": self.calendar,
            "currency": self.currency,
        }
        fn = dispatch.get(type)
        if fn is None:
            raise InvalidArgumentError(
                f'"{type}" is not a display-name type '
                "(use language/region/script/calendar/currency)."
            )
        return fn(code)

    def supported_values(self, key: str) -> list:
        """Values the runtime's ICU supports for ``key`` (e.g. all IANA time zones).

        Supported keys: ``timeZone``, ``collation``, ``numberingSystem``, ``unit``.
        ``currency`` and ``calendar`` are not enumerable through PyICU and raise
        (rather than return a hardcoded list).
        """
        if key == "timeZone":
            return list(icu.TimeZone.createEnumeration())
        if key == "collation":
            return list(icu.Collator.getKeywordValues("collation"))
        if key == "numberingSystem":
            return list(icu.NumberingSystem.getAvailableNames())
        if key == "unit":
            out = []
            for unit_type in icu.MeasureUnit.getAvailableTypes():
                out.extend(u.getSubtype() for u in icu.MeasureUnit.getAvailable(unit_type))
            return out
        if key == "transliterator":
            return list(icu.Transliterator.getAvailableIDs())
        if key in ("currency", "calendar"):
            raise UnsupportedError(
                f'supported_values("{key}") is not available through PyICU '
                "(ICU exposes no enumeration binding for it)."
            )
        raise InvalidArgumentError(
            f'"{key}" is not a valid key '
            "(use timeZone/collation/numberingSystem/unit/transliterator)."
        )

    # ------------------------------------------------------------------ #
    # case transforms
    # ------------------------------------------------------------------ #

    def upper(self, text: str) -> str:
        """Locale-aware upper-casing (e.g. Turkish dotted/dotless I)."""
        return str(icu.UnicodeString(text).toUpper(self._loc))

    def lower(self, text: str) -> str:
        """Locale-aware lower-casing."""
        return str(icu.UnicodeString(text).toLower(self._loc))

    # ------------------------------------------------------------------ #
    # transliteration & spoof detection
    # ------------------------------------------------------------------ #

    def transliterate(self, text: str, id: str) -> str:
        """Run an ICU transform over the text — script conversion, romanisation,
        accent folding (``"Any-Latin; Latin-ASCII"`` makes ASCII slugs).

        :param id: a compound ICU transliterator id; see
            ``supported_values("transliterator")`` for the building blocks.
        """
        try:
            transform = icu.Transliterator.createInstance(id)
        except Exception:
            raise InvalidArgumentError(f'"{id}" is not a valid transliterator id.')
        return transform.transliterate(text)

    def romanize(self, text: str) -> str:
        """Romanise text (``"Москва"`` → ``"Moskva"``); shorthand for ``Any-Latin``."""
        return self.transliterate(text, "Any-Latin")

    def confusable(self, a: str, b: str) -> bool:
        """Whether two strings are visually confusable (``"paypal"`` vs a
        Cyrillic ``"раураl"``) per UTS #39. Locale-independent."""
        return icu.SpoofChecker().areConfusable(a, b) != 0

    def suspicious(self, text: str) -> bool:
        """Whether a string fails ICU's default spoof checks (mixed scripts,
        restriction level, invisible characters) per UTS #39."""
        return icu.SpoofChecker().check(text) != 0

    # ------------------------------------------------------------------ #
    # alphabetic index (contact-list buckets)
    # ------------------------------------------------------------------ #

    def index_buckets(self, names: Iterable[str]) -> dict:
        """Group strings under locale-correct index headers (A–Z in en, 가나다 in
        ko, あかさ in ja, with the right under/overflow buckets). Buckets keep
        the locale's label order; empty buckets are omitted; items are collated.
        """
        index = icu.AlphabeticIndex(self._loc)
        for name in names:
            index.addRecord(name, name)
        out: dict = {}
        while index.nextBucket():
            items = []
            while index.nextRecord():
                items.append(index.recordData)
            if items:
                out[index.bucketLabel] = items
        return out

    # ------------------------------------------------------------------ #
    # locale-aware parsing (the inverse formatters)
    # ------------------------------------------------------------------ #

    def parse_number(self, text: str) -> float:
        """Parse a localised number (``"1.234,56"`` in de → ``1234.56``)."""
        try:
            return icu.NumberFormat.createInstance(self._loc).parse(text).getDouble()
        except Exception:
            raise InvalidArgumentError(
                f'"{text}" cannot be parsed as a number in {self.locale}.'
            )

    def parse_money(self, text: str) -> dict:
        """Parse a localised monetary string (``"$12.30"`` →
        ``{"amount": 12.3, "currency": "USD"}``)."""
        try:
            amount = icu.NumberFormat.createCurrencyInstance(self._loc).parseCurrency(text)
        except Exception:
            raise InvalidArgumentError(
                f'"{text}" cannot be parsed as money in {self.locale}.'
            )
        return {"amount": amount.getNumber().getDouble(), "currency": amount.getISOCurrency()}

    def parse_date(self, text: str, width: str = "short") -> _dt.datetime:
        """Parse a localised date written at the given width (the inverse of
        :meth:`date`). Returns an aware UTC :class:`~datetime.datetime`."""
        _assert_width(width)
        if width == "none":
            raise InvalidArgumentError('"none" is not a valid parse width.')
        fmt = icu.DateFormat.createDateInstance(_DATE_STYLE[width], self._calendar_locale(None))
        self._apply_timezone(fmt)
        try:
            seconds = fmt.parse(text)
        except Exception:
            raise InvalidArgumentError(
                f'"{text}" cannot be parsed as a date in {self.locale}.'
            )
        return _dt.datetime.fromtimestamp(seconds, tz=_dt.timezone.utc)

    def parse_moment(self, text: str, pattern: str) -> _dt.datetime:
        """Parse a moment with a raw ICU pattern (the inverse of
        :meth:`format_moment`). Returns an aware UTC :class:`~datetime.datetime`."""
        fmt = icu.SimpleDateFormat(pattern, self._calendar_locale(None))
        self._apply_timezone(fmt)
        try:
            seconds = fmt.parse(text)
        except Exception:
            raise InvalidArgumentError(f'"{text}" does not match the pattern "{pattern}".')
        return _dt.datetime.fromtimestamp(seconds, tz=_dt.timezone.utc)


# Width combos date_range supports, mapped to ICU interval skeletons.
_RANGE_SKELETON = {
    ("short", "none"): "yMd",
    ("medium", "none"): "yMMMd",
    ("long", "none"): "yMMMMd",
    ("full", "none"): "yMMMMEEEEd",
    ("none", "short"): "jm",
    ("none", "medium"): "jms",
    ("medium", "short"): "yMMMdjm",
    ("short", "short"): "yMdjm",
}
