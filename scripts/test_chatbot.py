#!/usr/bin/env python3
"""Test chatbot functionality end-to-end."""

import os
import sys
import requests
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8084"
USERNAME = os.environ.get("AGENT_ADMIN_USER", "agentadmin")
# Never hardcode credentials. Provide via env: AGENT_ADMIN_PASSWORD=... python scripts/test_chatbot.py
PASSWORD = os.environ.get("AGENT_ADMIN_PASSWORD", "")


def test_api_health():
    """Test that API is running."""
    print("\n[1/6] Testing API health...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✓ API is running on port 8084")
            return True
        else:
            print(f"✗ API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to API on localhost:8084")
        print("  Start the API with: python3 main.py run --config config.yaml")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_login():
    """Test login and get JWT token."""
    print("\n[2/6] Testing login...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=5,
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                print(f"✓ Login successful, token received")
                return token
            else:
                print("✗ No token in response")
                return None
        else:
            print(f"✗ Login failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_chatbot_config(token):
    """Test getting chatbot config."""
    print("\n[3/6] Testing chatbot config endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{BASE_URL}/api/chatbot/config",
            headers=headers,
            timeout=5,
        )
        if response.status_code == 200:
            config = response.json()
            print(f"✓ Config retrieved:")
            print(f"  - Provider: {config.get('llm_provider')}")
            print(f"  - Model: {config.get('llm_model')}")
            print(f"  - Tools enabled: {len(config.get('tools', []))} of 5")
            print(f"  - Enabled: {config.get('enabled')}")
            return config
        else:
            print(f"✗ Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_available_tools(token):
    """Test getting available tools."""
    print("\n[4/6] Testing available tools endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{BASE_URL}/api/chatbot/tools",
            headers=headers,
            timeout=5,
        )
        if response.status_code == 200:
            tools = response.json()
            print(f"✓ {len(tools)} tools available:")
            for tool_name, tool_def in tools.items():
                print(f"  - {tool_name}: {tool_def.get('description')}")
            return tools
        else:
            print(f"✗ Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_chat_message(token):
    """Test sending a chat message."""
    print("\n[5/6] Testing chat message endpoint...")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⊘ Skipped: ANTHROPIC_API_KEY not set")
        print("  Set it with: export ANTHROPIC_API_KEY='sk-ant-...'")
        return None

    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(
            f"{BASE_URL}/api/chatbot/chat",
            json={"message": "How many customers are in the database?"},
            headers=headers,
            timeout=30,
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Chat message sent successfully")
            print(f"  - Tools used: {result.get('tools_used', [])}")
            print(f"  - Response length: {len(result.get('assistant_message', ''))} chars")
            print(f"  - Stop reason: {result.get('stop_reason')}")
            return result
        else:
            print(f"✗ Failed: {response.status_code}")
            if response.status_code == 503:
                print("  Reason: API key not configured")
                print("  Set ANTHROPIC_API_KEY environment variable")
            else:
                print(f"  Error: {response.json().get('detail')}")
            return None
    except requests.exceptions.Timeout:
        print("✗ Request timeout (30s) - Claude API may be slow")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_chat_history(token):
    """Test getting chat history."""
    print("\n[6/6] Testing chat history endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{BASE_URL}/api/chatbot/history?limit=10",
            headers=headers,
            timeout=5,
        )
        if response.status_code == 200:
            messages = response.json()
            print(f"✓ Chat history retrieved: {len(messages)} messages")
            if messages:
                latest = messages[-1]
                print(f"  - Latest: {latest.get('user_message')[:50]}...")
            return messages
        else:
            print(f"✗ Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def main():
    """Run all tests."""
    print("=" * 60)
    print("SQL Agent Chatbot - End-to-End Test")
    print("=" * 60)

    # Check API health
    if not test_api_health():
        print("\n✗ API is not running. Start with:")
        print("  python3 main.py run --config config.yaml")
        return 1

    # Test login
    token = test_login()
    if not token:
        return 1

    # Test chatbot endpoints
    test_chatbot_config(token)
    test_available_tools(token)
    test_chat_message(token)
    test_chat_history(token)

    print("\n" + "=" * 60)
    print("✓ All tests completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Deploy ChatBot.tsx to arm2: frontend/src/components/ChatBot.tsx")
    print("2. Deploy AdminPage.tsx to arm2: frontend/src/pages/AdminPage.tsx")
    print("3. Import components in arm2 App.tsx")
    print("4. Rebuild and deploy dashboard on arm2")
    print("\nSee frontend/README.md for detailed integration instructions")

    return 0


if __name__ == "__main__":
    sys.exit(main())
