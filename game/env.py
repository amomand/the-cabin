"""Explicit environment loading for The Cabin's entry points.

Importing the game package must have no environment side effects (issue #178).
A harness that pops ``OPENAI_API_KEY`` to force an offline run has to stay
offline, or it silently makes live API calls and produces results that do not
reproduce.

So entry points load ``.env`` themselves: ``main.py``, ``server/app.py``, and
``game/devtools/model_eval.py``. This module deliberately imports nothing from
``game``, so calling it really does happen before the rest of the package is
imported. Anything that reads the environment at module scope, such as
``ai_interpreter.OPENAI_TIMEOUT_SECONDS``, would otherwise be frozen before the
load ran.
"""

from __future__ import annotations

from typing import Optional


def load_game_dotenv() -> Optional[str]:
    """Load the nearest ``.env``, searching upwards from the working directory.

    Returns the path loaded, or ``None`` when python-dotenv is missing or there
    is no ``.env`` to find. Existing environment variables win, so an explicitly
    exported value is never overwritten by the file.
    """
    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore
    except Exception:
        # dotenv is optional at runtime; if missing, rely on the environment.
        return None

    path = find_dotenv(usecwd=True)
    if not path:
        return None
    load_dotenv(path)
    return path
