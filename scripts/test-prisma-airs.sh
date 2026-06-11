#!/bin/bash
# Test Palo Alto Prisma AIRS API connectivity and authentication

set -e

echo "========================================="
echo "Palo Alto Prisma AIRS Diagnostic Test"
echo "========================================="
echo

# Load API key from .env
if [ -f .env ]; then
    export $(grep PRISMA_AIRS_API_KEY .env | xargs)
    export $(grep PRISMA_AIRS_REGION .env | xargs)
fi

API_KEY="${PRISMA_AIRS_API_KEY:-}"
REGION="${PRISMA_AIRS_REGION:-americas}"
ENDPOINT="https://service.api.aisecurity.paloaltonetworks.com"

echo "Configuration:"
echo "  Endpoint: $ENDPOINT"
echo "  Region:   $REGION"
echo "  API Key:  ${API_KEY:0:20}***"
echo

if [ -z "$API_KEY" ]; then
    echo "❌ ERROR: PRISMA_AIRS_API_KEY is not set in .env"
    exit 1
fi

echo "Testing connectivity..."
echo

# Test 1: DNS Resolution
echo "1. DNS Resolution Test:"
if nslookup service.api.aisecurity.paloaltonetworks.com > /dev/null 2>&1; then
    echo "   ✅ Endpoint resolves correctly"
else
    echo "   ❌ FAILED: Cannot resolve endpoint"
    exit 1
fi

echo

# Test 2: HTTPS Connection
echo "2. HTTPS Connection Test:"
if curl -s -I -H "x-pan-token: $API_KEY" \
    "$ENDPOINT/scan" > /dev/null 2>&1; then
    echo "   ✅ HTTPS connection successful"
else
    echo "   ⚠️  Connection test inconclusive (expected, API returns 405 for HEAD)"
fi

echo

# Test 3: API Authentication
echo "3. API Authentication Test:"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$ENDPOINT/scan" \
    -H "x-pan-token: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "metadata": {"type": "prompt"},
        "contents": {"prompt": "test"}
    }' 2>&1)

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "   HTTP Status: $HTTP_CODE"

case $HTTP_CODE in
    200)
        echo "   ✅ AUTHENTICATION SUCCESSFUL"
        echo "   ✅ API Key is valid"
        echo
        echo "   Response:"
        echo "$BODY" | head -n 3
        ;;
    401)
        echo "   ❌ AUTHENTICATION FAILED"
        echo "   Cause: Invalid API key or incorrect region"
        echo
        echo "   Actions:"
        echo "   1. Verify API key from Palo Alto dashboard"
        echo "   2. Confirm PRISMA_AIRS_REGION matches key region"
        echo "   3. Ensure API key is activated in Palo Alto"
        ;;
    403)
        echo "   ❌ FORBIDDEN"
        echo "   Cause: Key doesn't have permission for this API"
        ;;
    *)
        echo "   ⚠️  Unexpected HTTP code: $HTTP_CODE"
        echo "   Response: $BODY"
        ;;
esac

echo
echo "========================================="
echo "Diagnostic Complete"
echo "========================================="
