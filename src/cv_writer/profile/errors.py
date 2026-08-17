"""Errors for the profile package.

Kept separate from models.py so callers can catch profile-loading failures
without importing the whole Pydantic model surface.
"""

from __future__ import annotations


class ProfileValidationError(Exception):
    """Raised when a profile source (YAML file or in-memory dict) fails validation.

    Covers three distinct failure modes, all surfaced through this one type so
    callers have a single thing to catch (spec criterion 1):
      - the source isn't valid YAML at all,
      - the parsed YAML isn't a mapping at the root,
      - the mapping doesn't satisfy the Profile schema (Pydantic ValidationError,
        reformatted here so every offending field's path is named in the message).
    """
