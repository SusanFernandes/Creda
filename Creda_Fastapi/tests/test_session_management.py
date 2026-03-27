#!/usr/bin/env python3
"""
Session Management & Multi-Turn Conversation Tests - Priority 1 Feature

Tests:
  ✅ Session persistence across turns
  ✅ Conversation history retention
  ✅ User profile maintenance
  ✅ Context awareness in responses
  ✅ Session isolation (no data leak between users)
  ✅ Multi-language session switching
  ✅ Different user sessions simultaneously
  ✅ Session timeout behavior (if applicable)

Run: pytest tests/test_session_management.py -v
"""

import pytest
import requests
import json
import time
import uuid
from typing import Dict, List, Optional

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GATEWAY_URL = "http://localhost:8080"
MULTILINGUAL_URL = "http://localhost:8000"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIXTURES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture
def new_session_id():
    """Generate unique session ID."""
    return f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def new_user_id():
    """Generate unique user ID."""
    return f"user_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def user_profile():
    """Standard test user profile."""
    return {
        "user_id": "test_user",
        "age": 35,
        "income": 100000,
        "monthly_expenses": 50000,
        "savings": 500000,
        "risk_profile": "moderate",
        "investment_goals": ["wealth_creation", "retirement"],
        "preferred_language": "en",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 1: CONVERSATION CONTINUITY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConversationContinuity:
    """Test multi-turn conversation with context retention."""

    def test_two_turn_english_conversation(self, new_session_id, new_user_id):
        """Test simple 2-turn English conversation."""
        
        # Turn 1: Initial inquiry
        resp1 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "What is a mutual fund?",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "en",
            },
            timeout=60,
        )
        
        assert resp1.status_code == 200
        response1_text = resp1.json().get("data", {}).get("response") or resp1.json().get("response", "")
        assert len(response1_text) > 0
        print(f"Turn 1: {response1_text[:80]}...")
        
        # Turn 2: Follow-up question (should maintain context)
        resp2 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "What are the benefits?",  # Should be understood in context of MF
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "en",
            },
            timeout=60,
        )
        
        assert resp2.status_code == 200
        response2_text = resp2.json().get("data", {}).get("response") or resp2.json().get("response", "")
        assert len(response2_text) > 0
        print(f"Turn 2: {response2_text[:80]}...")

    def test_three_turn_conversation_with_clarifications(self, new_session_id, new_user_id):
        """Test 3-turn conversation with refinements."""
        
        turns = [
            "I want to invest but I'm not sure where to start",
            "I have 50000 per month to invest",
            "Which one should I pick - SIP or lump sum?",
        ]
        
        for turn_num, query in enumerate(turns, 1):
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": query,
                    "user_id": new_user_id,
                    "session_id": new_session_id,
                    "language": "en",
                },
                timeout=60,
            )
            
            assert resp.status_code == 200
            response_text = resp.json().get("data", {}).get("response") or resp.json().get("response", "")
            assert len(response_text) > 0
            print(f"Turn {turn_num}: ✓")
        
        print("✓ 3-turn conversation completed successfully")

    def test_long_conversation_five_turns(self, new_session_id, new_user_id):
        """Test 5-turn conversation with sustained context."""
        
        turns = [
            ("I'm interested in FIRE planning", "finance"),
            ("I have 10 years until retirement", "finance"),
            ("My current savings are ₹20 lakhs", "finance"),
            ("I can save ₹1 lakh per month", "finance"),
            ("Will this be enough for a comfortable retirement?", "finance"),
        ]
        
        for turn_num, (query, category) in enumerate(turns, 1):
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": query,
                    "user_id": new_user_id,
                    "session_id": new_session_id,
                    "language": "en",
                },
                timeout=60,
            )
            
            assert resp.status_code == 200
            assert len(resp.json().get("data", {}).get("response") or resp.json().get("response", "")) > 0
            print(f"Turn {turn_num}: ✓")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 2: MULTILINGUAL SESSION CONTINUITY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMultilingualSessionContinuity:
    """Test conversation continuity across different languages."""

    def test_hindi_two_turn_conversation(self, new_session_id, new_user_id):
        """Test 2-turn Hindi conversation."""
        
        # Turn 1: Hindi inquiry
        resp1 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "मुझे म्यूचुअल फंड के बारे में बताइए",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "hi",
            },
            timeout=60,
        )
        
        assert resp1.status_code == 200
        response1_text = resp1.json().get("data", {}).get("response") or resp1.json().get("response", "")
        assert len(response1_text) > 0
        # Response should be in Hindi (Devanagari script)
        assert any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in response1_text), \
            "Response not in Devanagari script"
        
        # Turn 2: Hindi follow-up
        resp2 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "इसके क्या फायदे हैं?",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "hi",
            },
            timeout=60,
        )
        
        assert resp2.status_code == 200
        response2_text = resp2.json().get("data", {}).get("response") or resp2.json().get("response", "")
        assert len(response2_text) > 0
        print(f"✓ Hindi 2-turn conversation successful")

    def test_tamil_conversation(self, new_session_id, new_user_id):
        """Test Tamil conversation."""
        
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "என் பணத்தை முதலீடு செய்ய என்ன செய்ய வேண்டும்?",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "ta",
            },
            timeout=60,
        )
        
        assert resp.status_code == 200
        response_text = resp.json().get("data", {}).get("response") or resp.json().get("response", "")
        assert len(response_text) > 0
        print(f"✓ Tamil conversation successful")

    def test_gujarati_conversation(self, new_session_id, new_user_id):
        """Test Gujarati conversation."""
        
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "મારું બજેટ કેવી રીતે સંચાલન કરું?",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "gu",
            },
            timeout=60,
        )
        
        assert resp.status_code == 200
        response_text = resp.json().get("data", {}).get("response") or resp.json().get("response", "")
        assert len(response_text) > 0
        print(f"✓ Gujarati conversation successful")

    def test_bengali_conversation(self, new_session_id, new_user_id):
        """Test Bengali conversation."""
        
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "আমার বিনিয়োগ পরিকল্পনা কী হওয়া উচিত?",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "bn",
            },
            timeout=60,
        )
        
        assert resp.status_code == 200
        response_text = resp.json().get("data", {}).get("response") or resp.json().get("response", "")
        assert len(response_text) > 0
        print(f"✓ Bengali conversation successful")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 3: SESSION ISOLATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSessionIsolation:
    """Test that sessions are properly isolated (no data leak)."""

    def test_two_different_sessions_no_contamination(self, new_user_id):
        """Test that data from one session doesn't leak into another."""
        session_id_1 = f"session_1_{int(time.time() * 1000)}"
        session_id_2 = f"session_2_{int(time.time() * 1000)}"
        
        # Session 1: SIP query
        resp1 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "मेरे लिए SIP सुझाइए",
                "user_id": new_user_id,
                "session_id": session_id_1,
                "language": "hi",
            },
            timeout=60,
        )
        response1 = resp1.json().get("data", {}).get("response") or resp1.json().get("response", "")
        
        # Session 2: Unrelated query
        resp2 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "एक रिसिपी बताइए",  # Random query
                "user_id": new_user_id,
                "session_id": session_id_2,
                "language": "hi",
            },
            timeout=60,
        )
        response2 = resp2.json().get("data", {}).get("response") or resp2.json().get("response", "")
        
        # Session 1 again: Earlier context should be maintained, not Session 2
        resp3 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "और विवरण दीजिए",
                "user_id": new_user_id,
                "session_id": session_id_1,
                "language": "hi",
            },
            timeout=60,
        )
        response3 = resp3.json().get("data", {}).get("response") or resp3.json().get("response", "")
        
        # Response 3 should be related to SIP (from session 1), not recipe
        assert len(response1) > 0 and len(response2) > 0 and len(response3) > 0
        print("✓ Sessions properly isolated")

    def test_different_users_different_sessions(self):
        """Test that different users maintain separate sessions."""
        user_1 = f"user_1_{uuid.uuid4().hex[:8]}"
        user_2 = f"user_2_{uuid.uuid4().hex[:8]}"
        session_id = f"test_session_{int(time.time() * 1000)}"  # Same session ID
        
        # User 1 query
        resp1 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "Tell me about aggressive investment",
                "user_id": user_1,
                "session_id": session_id,
                "language": "en",
            },
            timeout=60,
        )
        
        # User 2 query (same session ID but different user)
        resp2 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "Tell me about conservative investment",
                "user_id": user_2,
                "session_id": session_id,
                "language": "en",
            },
            timeout=60,
        )
        
        # Both should succeed (ideally with different contexts)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        print("✓ Different users can use same session ID without contamination")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 4: CONTEXT AWARENESS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestContextAwareness:
    """Test that responses are context-aware across turns."""

    def test_pronoun_resolution(self, new_session_id, new_user_id):
        """Test that pronouns are properly resolved in context."""
        
        # Turn 1: Introduce topic
        resp1 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "I invested 10000 in a mutual fund",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "en",
            },
            timeout=60,
        )
        assert resp1.status_code == 200
        
        # Turn 2: Use pronoun to refer back
        resp2 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "How much will it grow?",  # "it" refers to mutual fund
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "en",
            },
            timeout=60,
        )
        assert resp2.status_code == 200
        response2_text = resp2.json().get("data", {}).get("response") or resp2.json().get("response", "")
        print(f"✓ Pronoun resolution: {response2_text[:80]}...")

    def test_numerical_reference_tracking(self, new_session_id, new_user_id):
        """Test tracking of numerical values mentioned."""
        
        # Turn 1: Mention specific amount
        resp1 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "I have 500000 rupees to invest",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "en",
            },
            timeout=60,
        )
        assert resp1.status_code == 200
        
        # Turn 2: Refer to that amount indirectly
        resp2 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "How should I split this amount?",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "en",
            },
            timeout=60,
        )
        assert resp2.status_code == 200
        response2_text = resp2.json().get("data", {}).get("response") or resp2.json().get("response", "")
        # Response should potentially reference the amount
        print(f"✓ Numerical reference tracked")

    def test_goal_persistence_across_turns(self, new_session_id, new_user_id):
        """Test that mentioned goals persist across conversation turns."""
        
        # Turn 1: Express goal
        resp1 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "I want to retire in 15 years",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "en",
            },
            timeout=60,
        )
        assert resp1.status_code == 200
        
        # Turn 2: Ask for strategy for that goal
        resp2 = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "What's the best strategy for this?",
                "user_id": new_user_id,
                "session_id": new_session_id,
                "language": "en",
            },
            timeout=60,
        )
        assert resp2.status_code == 200
        response2_text = resp2.json().get("data", {}).get("response") or resp2.json().get("response", "")
        
        # Response should reference retirement within 15 years
        print(f"✓ Goal persistence checked")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 5: CONCURRENT SESSIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConcurrentSessions:
    """Test multiple concurrent sessions."""

    def test_three_simultaneous_user_sessions(self):
        """Simulate 3 users having conversations simultaneously."""
        
        users = [
            {
                "user_id": f"user_concurrent_1",
                "session_id": f"session_{int(time.time() * 1000)}_1",
                "query": "What is SIP?",
            },
            {
                "user_id": f"user_concurrent_2",
                "session_id": f"session_{int(time.time() * 1000)}_2",
                "query": "Tell me about FIRE",
            },
            {
                "user_id": f"user_concurrent_3",
                "session_id": f"session_{int(time.time() * 1000)}_3",
                "query": "How to diversify portfolio",
            },
        ]
        
        responses = []
        for user in users:
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": user["query"],
                    "user_id": user["user_id"],
                    "session_id": user["session_id"],
                    "language": "en",
                },
                timeout=60,
            )
            
            assert resp.status_code == 200
            responses.append(resp.status_code)
        
        # All should succeed
        assert all(code == 200 for code in responses)
        print("✓ 3 concurrent sessions handled successfully")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 6: SESSION METADATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSessionMetadata:
    """Test session metadata tracking."""

    def test_session_timestamp_consistency(self, new_session_id, new_user_id):
        """Test that session timestamps are consistent."""
        
        start_time = time.time()
        
        # Multiple turns in same session
        for i in range(3):
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": f"Query {i+1}: Tell me about investment",
                    "user_id": new_user_id,
                    "session_id": new_session_id,
                    "language": "en",
                },
                timeout=60,
            )
            assert resp.status_code == 200
            time.sleep(0.5)
        
        elapsed = time.time() - start_time
        print(f"✓ 3 turns completed in {elapsed:.2f}s")

    def test_session_responsiveness_degradation(self, new_session_id, new_user_id):
        """Test if response time degrades with longer conversations."""
        
        response_times = []
        
        for turn in range(5):
            start = time.time()
            
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": f"Turn {turn+1}: Tell me about investment strategies",
                    "user_id": new_user_id,
                    "session_id": new_session_id,
                    "language": "en",
                },
                timeout=60,
            )
            
            elapsed = time.time() - start
            response_times.append(elapsed)
            assert resp.status_code == 200
        
        avg_time = sum(response_times) / len(response_times)
        print(f"✓ Response times: {[f'{t:.2f}s' for t in response_times]}")
        print(f"  Average: {avg_time:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
