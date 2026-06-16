#!/bin/bash
# Test Palo Alto Prisma AIRS API connectivity, authentication and scanning.

set -e

echo "========================================="
echo "Palo Alto Prisma AIRS Diagnostic Test"
echo "========================================="
echo

# Load config from .env
if [ -f .env ]; then
    export $(grep -E '^PRISMA_AIRS_' .env | xargs)
fi

API_KEY="${PRISMA_AIRS_API_KEY:-}"
PROFILE_NAME="${PRISMA_AIRS_PROFILE_NAME:-}"
PROFILE_ID="${PRISMA_AIRS_PROFILE_ID:-}"
ENDPOINT="https://service.api.aisecurity.paloaltonetworks.com"
SCAN_PATH="/v1/scan/sync/request"

echo "Configuration:"
echo "  Endpoint: $ENDPOINT$SCAN_PATH"
echo "  API Key:  ${API_KEY:0:20}***"
echo "  Profile:  ${PROFILE_NAME:-${PROFILE_ID:-<none>}}"
echo

if [ -z "$API_KEY" ]; then
    echo "❌ ERROR: PRISMA_AIRS_API_KEY is not set in .env"
    exit 1
fi

# Build ai_profile block (name preferred, else id)
if [ -n "$PROFILE_NAME" ]; then
    AI_PROFILE="{\"profile_name\":\"$PROFILE_NAME\"}"
elif [ -n "$PROFILE_ID" ]; then
    AI_PROFILE="{\"profile_id\":\"$PROFILE_ID\"}"
else
    AI_PROFILE="{\"profile_name\":\"\"}"
fi

echo "1. DNS Resolution Test:"
if nslookup service.api.aisecurity.paloaltonetworks.com > /dev/null 2>&1; then
    echo "   ✅ Endpoint resolves correctly"
else
    echo "   ❌ FAILED: Cannot resolve endpoint"
    exit 1
fi
echo

echo "2. Scan API Test (auth + profile):"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$ENDPOINT$SCAN_PATH" \
    -H "x-pan-token: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"ai_profile\":$AI_PROFILE,\"metadata\":{\"app_name\":\"sql-agent\",\"app_user\":\"diag\"},\"contents\":[{\"prompt\":\"test\"}]}" 2>&1)

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "   HTTP Status: $HTTP_CODE"
case $HTTP_CODE in
    200)
        echo "   ✅ SUCCESS — key authenticated and profile valid"
        echo "   Response: $BODY"
        ;;
    400)
        if echo "$BODY" | grep -qi "profile"; then
            echo "   ⚠️  Key authenticates, but AI profile is missing/invalid."
            echo "   Set PRISMA_AIRS_PROFILE_NAME in .env to a profile that exists"
            echo "   in your Palo Alto tenant (Strata Cloud Manager > AI security profiles)."
        else
            echo "   ⚠️  Bad request: $BODY"
        fi
        ;;
    401)
        echo "   ❌ AUTH FAILED (401): Invalid/inactive API key"
        ;;
    403)
        echo "   ❌ FORBIDDEN (403): $BODY"
        ;;
    *)
        echo "   ⚠️  Unexpected: $BODY"
        ;;
esac

echo
echo "========================================="
echo "Diagnostic Complete"
echo "========================================="
