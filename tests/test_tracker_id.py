"""``Tracker.id`` is the one place the colon-free rule is enforced.

``railroad_club.vehicle_keys`` builds and splits Redis keys on the first colon
and does not re-check the id, so this validator is what makes that safe.
"""

from __future__ import annotations

import pytest

from railroad_club.models.tracker import Tracker, generate_tracker_id


def test_a_generated_id_is_colon_free():
    assert ":" not in generate_tracker_id()


def test_a_colon_in_the_id_is_refused():
    with pytest.raises(ValueError, match="must not contain"):
        Tracker(id="bad:id", nickname="Bus", feed_id=1)


def test_an_empty_nickname_is_refused():
    """Guarded by the same hook. As a ``@field_validator`` it never ran: a
    SQLModel ``table=True`` model skips Pydantic validation on init."""
    with pytest.raises(ValueError, match="nickname must not be empty"):
        Tracker(nickname="   ", feed_id=1)


def test_a_hand_written_colon_free_id_is_accepted():
    """The dev seed pins readable ids such as ``amtrak-live``; they are not
    uuid4 hex and do not need to be, only colon-free."""
    tracker = Tracker(id="amtrak-live", nickname="Amtrak", feed_id=1)
    assert tracker.id == "amtrak-live"
