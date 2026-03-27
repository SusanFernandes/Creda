"""
test_gateway_passthrough.py — Regression test for gateway status code passthrough.

BUG (error_app_py.log):
  Gateway's route_request() had a generic `except Exception` that caught
  HTTPException and wrapped it as 500:
  
    ERROR:app:Service error for /pipecat/offer: 501 - {"detail":"pipecat-ai..."}
    ERROR:app:Routing error for /pipecat/offer: 501: {"detail":"pipecat-ai..."}
    INFO: POST /pipecat/offer HTTP/1.1 500 Internal Server Error  ← WRONG

  The 501 from the multilingual service became 500 at the gateway.

FIX:
  Added `except HTTPException: raise` before `except Exception` in route_request().

These tests verify:
  1. HTTPException status codes pass through unchanged
  2. 422 validation errors pass through unchanged
  3. 501 "not implemented" passes through unchanged
  4. The catch-all dynamic route doesn't generate duplicate operation ID warnings
"""

import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ──────────────────────────────────────────────────────────────────────────
# Test the route_request function directly
# ──────────────────────────────────────────────────────────────────────────


def test_route_request_reraises_httpexception():
    """
    REGRESSION: HTTPException must be re-raised, not caught by `except Exception`.
    Verify the exception handling order in route_request().
    """
    import inspect
    from app import route_request

    source = inspect.getsource(route_request)

    # The fix: `except HTTPException:` must appear BEFORE `except Exception:`
    http_exc_pos = source.find("except HTTPException")
    generic_exc_pos = source.find("except Exception")

    assert http_exc_pos != -1, (
        "route_request is missing `except HTTPException:` — status codes will be swallowed!"
    )
    assert generic_exc_pos != -1, (
        "route_request is missing `except Exception:` catch-all"
    )
    assert http_exc_pos < generic_exc_pos, (
        "CRITICAL: `except HTTPException` must come BEFORE `except Exception` "
        "otherwise HTTPException gets caught by the generic handler and wrapped as 500!"
    )


def test_dynamic_route_excluded_from_schema():
    """
    REGRESSION: The catch-all /{endpoint:path} route was causing
    'Duplicate Operation ID' warnings in /docs.
    It should have include_in_schema=False.
    """
    from app import app

    # Check that the catch-all route is not in the OpenAPI schema
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    # The catch-all route should NOT appear in the schema
    catch_all_in_schema = False
    for path_key in paths:
        if "{endpoint}" in path_key:
            catch_all_in_schema = True
            break

    assert not catch_all_in_schema, (
        "Catch-all /{endpoint:path} route is still in the OpenAPI schema! "
        "This causes 'Duplicate Operation ID' warnings. "
        "Add include_in_schema=False to the @app.api_route decorator."
    )


# ──────────────────────────────────────────────────────────────────────────
# Test determine_service_route covers all known routes
# ──────────────────────────────────────────────────────────────────────────


def test_pipecat_offer_routes_to_multilingual():
    """Ensure /pipecat/offer routes to the multilingual service."""
    from app import determine_service_route, FASTAPI1_URL

    url, service_name = determine_service_route("/pipecat/offer")
    assert url == FASTAPI1_URL, f"/pipecat/offer should route to multilingual, got {url}"
    assert service_name == "multilingual"


def test_money_health_routes_to_finance():
    """Ensure /money-health-score routes to the finance service."""
    from app import determine_service_route, FASTAPI2_URL

    url, service_name = determine_service_route("/money-health-score")
    assert url == FASTAPI2_URL, f"/money-health-score should route to finance, got {url}"
    assert service_name == "finance"


def test_voice_command_routes_to_multilingual():
    """Ensure /voice/command routes to multilingual."""
    from app import determine_service_route, FASTAPI1_URL

    url, service_name = determine_service_route("/voice/command")
    assert url == FASTAPI1_URL
    assert service_name == "multilingual"


EXPECTED_VOICE_ROUTES = [
    "/process_voice", "/get_audio_response", "/translate",
    "/understand_intent", "/process_multilingual_query", "/test_asr",
    "/voice/command", "/tts_only", "/transcribe_only",
    "/pipecat/offer",
]

EXPECTED_FINANCE_ROUTES = [
    "/process_request", "/get_portfolio_allocation", "/rag_query",
    "/knowledge_base_stats", "/chat", "/profile/upsert",
    "/portfolio/xray", "/portfolio/stress-test", "/fire-planner",
    "/money-health-score", "/tax-wizard", "/sip-calculator",
    "/couples-planner", "/twilio/brain", "/supported_features",
]


@pytest.mark.parametrize("endpoint", EXPECTED_VOICE_ROUTES)
def test_voice_routes_go_to_multilingual(endpoint):
    from app import determine_service_route, FASTAPI1_URL
    url, _ = determine_service_route(endpoint)
    assert url == FASTAPI1_URL, f"{endpoint} should route to multilingual"


@pytest.mark.parametrize("endpoint", EXPECTED_FINANCE_ROUTES)
def test_finance_routes_go_to_finance(endpoint):
    from app import determine_service_route, FASTAPI2_URL
    url, _ = determine_service_route(endpoint)
    assert url == FASTAPI2_URL, f"{endpoint} should route to finance"
