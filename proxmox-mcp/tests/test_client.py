"""Tests for ProxmoxClient with httpx mocking."""

import pytest
import httpx
from unittest.mock import patch
from pydantic import BaseModel
from mcp.server.fastmcp.exceptions import ToolError

from proxmox_mcp.api.client import ProxmoxClient
from proxmox_mcp.models import ProxmoxNodeListResponse, ProxmoxTaskResponse


@pytest.fixture
def client():
    return ProxmoxClient(
        url="https://proxmox.test:8006/api2/json",
        token_name="user@pam!token",
        token_value="secret-value",
        verify_ssl=False,
    )


VALID_NODE_RESPONSE = {
    "data": [{"node": "pve1", "status": "online", "maxcpu": 4, "maxmem": 8_000_000}]
}

VALID_TASK_RESPONSE = {"data": "UPID:pve1:00001234:task:100:user@pam:"}


class TestFetchAndValidateSuccess:
    async def test_get_request(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://proxmox.test:8006/api2/json/nodes",
            json=VALID_NODE_RESPONSE,
        )
        result = await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)
        assert result["data"][0]["node"] == "pve1"

    async def test_post_request(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://proxmox.test:8006/api2/json/nodes/pve1/lxc/100/status/start",
            json=VALID_TASK_RESPONSE,
        )
        result = await client.fetch_and_validate(
            "/nodes/pve1/lxc/100/status/start",
            ProxmoxTaskResponse, method="POST",
        )
        assert "UPID" in result["data"]

    async def test_put_request(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://proxmox.test:8006/api2/json/nodes/pve1/qemu/200/config",
            json={"data": {"hostname": "test"}},
        )
        from proxmox_mcp.models import ProxmoxConfigResponse
        result = await client.fetch_and_validate(
            "/nodes/pve1/qemu/200/config",
            ProxmoxConfigResponse, method="PUT", params={"ciuser": "root"},
        )
        assert result["data"]["hostname"] == "test"

    async def test_delete_request(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://proxmox.test:8006/api2/json/nodes/pve1/lxc/100",
            json=VALID_TASK_RESPONSE,
        )
        result = await client.fetch_and_validate(
            "/nodes/pve1/lxc/100",
            ProxmoxTaskResponse, method="DELETE",
        )
        assert "UPID" in result["data"]

    async def test_auth_header_sent(self, client, httpx_mock):
        httpx_mock.add_response(json=VALID_NODE_RESPONSE)
        await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)
        request = httpx_mock.get_request()
        assert "PVEAPIToken=user@pam!token=secret-value" in request.headers["authorization"]

    async def test_get_with_params(self, client, httpx_mock):
        httpx_mock.add_response(json=VALID_NODE_RESPONSE)
        await client.fetch_and_validate(
            "/nodes", ProxmoxNodeListResponse, params={"timeframe": "hour"},
        )
        request = httpx_mock.get_request()
        assert "timeframe=hour" in str(request.url)


class TestFetchAndValidateErrors:
    async def test_401_unauthorized(self, client, httpx_mock):
        httpx_mock.add_response(status_code=401)
        with pytest.raises(ToolError, match="401 Unauthorized"):
            await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)

    async def test_403_forbidden_with_permission_hint(self, client, httpx_mock):
        httpx_mock.add_response(status_code=403)
        with pytest.raises(ToolError, match="403 Forbidden"):
            await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)

    async def test_404_not_found(self, client, httpx_mock):
        httpx_mock.add_response(status_code=404)
        with pytest.raises(ToolError, match="404 Not Found"):
            await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)

    async def test_500_server_error(self, client, httpx_mock):
        httpx_mock.add_response(status_code=500, text="Internal Server Error")
        with pytest.raises(ToolError, match="500"):
            await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)

    async def test_contract_divergence(self, client, httpx_mock):
        """Valid HTTP response but data doesn't match the model."""
        httpx_mock.add_response(json={"wrong_key": "bad_data"})
        with pytest.raises(ToolError, match="API_CONTRACT_DIVERGENCE"):
            await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)

    async def test_connection_error(self, client, httpx_mock):
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
        with pytest.raises(ToolError, match="Unexpected Error"):
            await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)

    async def test_timeout_error(self, client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
        with pytest.raises(ToolError, match="Unexpected Error"):
            await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)

    async def test_403_includes_permission_details(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://proxmox.test:8006/api2/json/nodes",
            status_code=403,
        )
        with pytest.raises(ToolError, match="Sys.Audit"):
            await client.fetch_and_validate("/nodes", ProxmoxNodeListResponse)
