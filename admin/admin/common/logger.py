"""Shared logger for the seed package.

Uses control_plane.logs' configured ``simple`` logger so seed output is not dropped after
``control_plane.logs`` runs ``dictConfig`` (the root logger is WARNING-only; ``basicConfig`` is a no-op).
"""

from __future__ import annotations

import logging

from control_plane.logs import SIMPLE_LOGGER_NAME

logger = logging.getLogger(SIMPLE_LOGGER_NAME)
