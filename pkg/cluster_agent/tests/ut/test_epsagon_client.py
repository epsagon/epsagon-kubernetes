"""
EpsagonClient tests
"""
import base64
import pytest
from epsagon_client import EpsagonClient

TEST_EPSAGON_TOKEN = "123"
ENCODED_TOKEN = base64.b64encode(f"{TEST_EPSAGON_TOKEN}:".encode()).decode()
TEST_PATH = "/post_path"

@pytest.mark.asyncio
async def test_initialize_no_epsagon_token():
    """ Initialize test - no epsagon token """
    with pytest.raises(ValueError):
        await EpsagonClient.create(None)


@pytest.mark.asyncio
async def test_post(httpserver):
    """ post sanity test """
    data = {
        "a": "A"
    }
    def handler(request):
        assert "Authorization" in request.headers
        assert request.headers["Authorization"] == f"Basic {ENCODED_TOKEN}"
    httpserver.expect_request(
        TEST_PATH,
        method="POST",
    ).respond_with_handler(handler)
    client = await EpsagonClient.create(TEST_EPSAGON_TOKEN)
    await client.post(httpserver.url_for(TEST_PATH), data)
