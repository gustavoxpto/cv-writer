"""Shared vocabulary for language proficiency levels (Language.proficiency free-text values).

Lives at the profile layer, the lowest-level package, so neither matching (an *approximate*
signal for the match report) nor generation (criterion 20's *authoritative* gate on what
language a CV can be generated in) has to depend on the other to share one definition of
"working proficiency or above." A code-review pass on slice 4 found these two packages had
quietly drifted into two different vocabularies for the same field — this module is the fix.
"""

from __future__ import annotations

WORKING_PROFICIENCY_LEVELS = frozenset(
    {
        "native",
        "fluent",
        "working",
        "professional",
        "advanced",
        "c1",
        "c2",
        "full professional",
    }
)
