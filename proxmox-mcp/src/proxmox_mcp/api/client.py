import logging
import httpx
from typing import Any, Optional
from pydantic import ValidationError
from mcp.server.fastmcp.exceptions import ToolError
from proxmox_mcp.api.permissions import get_required_permission

logger = logging.getLogger("proxmox-mcp")


class ProxmoxClient:
    def __init__(self, url: str, token_name: str, token_value: str, verify_ssl: bool = True):
        self.base_url = url
        self.headers = {"Authorization": f"PVEAPIToken={token_name}={token_value}"}
        self.verify_ssl = verify_ssl

    async def fetch_and_validate(self, endpoint: str, model_class: Any, method: str = "GET", params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            try:
                logger.info(f"Proxmox API Request: {method} {url}")
                if method == "POST":
                    response = await client.post(url, headers=self.headers, data=params)
                elif method == "PUT":
                    response = await client.put(url, headers=self.headers, data=params)
                elif method == "DELETE":
                    response = await client.delete(url, headers=self.headers)
                else:
                    response = await client.get(url, headers=self.headers, params=params)

                if response.status_code == 403:
                    privs = get_required_permission(method, url, self.base_url)
                    raise ToolError(
                        f"403 Forbidden. The API token does not have sufficient permissions.\n"
                        f"Minimum privileges required: {privs}\n"
                        "Please update the API Token's permissions in the Proxmox Datacenter > Permissions panel."
                    )

                response.raise_for_status()
                raw_data = response.json()
                try:
                    validated_response = model_class(**raw_data)
                    logger.info(f"Success: {method} {url}")
                    return validated_response.model_dump()
                except ValidationError as ve:
                    logger.error(f"Contract Divergence at {url}: {ve}")
                    raise ToolError(f"API_CONTRACT_DIVERGENCE: Proxmox returned unexpected data. Details: {str(ve)}")
            except ToolError:
                raise
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 401:
                    msg = "401 Unauthorized. Check API Token."
                elif status == 404:
                    msg = f"404 Not Found at {url}."
                else:
                    msg = f"Proxmox API Error ({status}): {e.response.text}"
                logger.error(msg)
                raise ToolError(msg)
            except Exception as e:
                msg = f"Unexpected Error: {type(e).__name__}: {str(e)}"
                logger.error(msg)
                raise ToolError(msg)
