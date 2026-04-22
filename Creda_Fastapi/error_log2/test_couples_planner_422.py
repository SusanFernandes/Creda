"""
test_couples_planner_422.py — Regression test for /couples-planner 422 error.

BUG (error_log2):
  Frontend sends {partner1_user_id, partner2_user_id, combined_goal}
  but CouplesRequest expected {user_id_1, user_id_2, combined_goals}.
  Result: 422 "Field required" for `user_id_1`.

FIX:
  Added alias fields (partner1_user_id, partner2_user_id, combined_goal)
  to CouplesRequest with helper methods get_user_id_1() / get_user_id_2().
"""

import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_couples_request_accepts_frontend_field_names():
    """CouplesRequest must accept partner1_user_id / partner2_user_id."""
    from fastapi2_finance import CouplesRequest

    req = CouplesRequest(
        partner1_user_id="alice",
        partner2_user_id="bob",
        combined_goal="buy a house",
    )
    assert req.get_user_id_1() == "alice"
    assert req.get_user_id_2() == "bob"
    assert req.combined_goal == "buy a house"


def test_couples_request_accepts_original_field_names():
    """CouplesRequest must still accept user_id_1 / user_id_2."""
    from fastapi2_finance import CouplesRequest

    req = CouplesRequest(
        user_id_1="alice",
        user_id_2="bob",
        combined_goals=["retirement"],
    )
    assert req.get_user_id_1() == "alice"
    assert req.get_user_id_2() == "bob"


def test_couples_request_prefers_explicit_user_id():
    """If both old and new fields are set, original user_id_1 wins."""
    from fastapi2_finance import CouplesRequest

    req = CouplesRequest(
        user_id_1="primary",
        partner1_user_id="alias",
    )
    assert req.get_user_id_1() == "primary"


def test_couples_request_falls_back_to_anonymous():
    """If no user ID field is provided at all, falls back to 'anonymous'."""
    from fastapi2_finance import CouplesRequest

    req = CouplesRequest()
    assert req.get_user_id_1() == "anonymous"
    assert req.get_user_id_2() == "anonymous"


def test_couples_request_combined_goal_singular():
    """combined_goal (singular from frontend) is accepted."""
    from fastapi2_finance import CouplesRequest

    req = CouplesRequest(combined_goal="retirement")
    assert req.combined_goal == "retirement"
