"""Names of the ICU resource bundles reachable through :meth:`Cosmo.get`.

These mirror the constants in the PHP port's ``Bundle`` class. They are the
package identifiers PyICU's :class:`icu.ResourceBundle` understands.
"""


class Bundle:
    """ICU resource-bundle package names."""

    #: Break-iterator rule source data.
    BRKITR = "ICUDATA-brkitr"
    #: Currency symbols and display names.
    CURRENCY = "ICUDATA-curr"
    #: The per-locale bundle (delimiters, layout, …).
    LOCALE = "ICUDATA"
    #: Language / script / calendar display names.
    LANGUAGE = "ICUDATA-lang"
