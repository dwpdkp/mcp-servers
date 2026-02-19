"""
Bacularis MCP Server — Read-only access to Bacula/Bareos backup management via Bacularis REST API.
"""

import json
import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Bacularis")

BACULARIS_URL = os.environ.get("BACULARIS_URL", "http://10.100.0.42:9097")
BACULARIS_USER = os.environ.get("BACULARIS_USER", "")
BACULARIS_PASSWORD = os.environ.get("BACULARIS_PASSWORD", "")


def _get(path: str, params: Optional[dict] = None) -> str:
    """GET request to Bacularis API v3, return JSON string."""
    try:
        with httpx.Client(
            base_url=f"{BACULARIS_URL}/api/v3",
            auth=(BACULARIS_USER, BACULARIS_PASSWORD),
            verify=False,
            timeout=30.0,
        ) as client:
            resp = client.get(path, params=params)
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}", "detail": e.response.text[:500]})
    except httpx.ConnectError:
        return json.dumps({"error": "Connection failed", "detail": f"Cannot reach {BACULARIS_URL}"})
    except Exception as e:
        return json.dumps({"error": str(type(e).__name__), "detail": str(e)})


# --- Jobs ---


@mcp.tool()
def get_jobs(
    limit: int = 25,
    name: Optional[str] = None,
    jobstatus: Optional[str] = None,
    client: Optional[str] = None,
    level: Optional[str] = None,
) -> str:
    """List backup jobs with optional filters.

    Args:
        limit: Max number of jobs to return (default 25)
        name: Filter by job name
        jobstatus: Filter by status (T=OK, E=Error, R=Running, A=Canceled, f=Failed, etc.)
        client: Filter by client name
        level: Filter by backup level (F=Full, I=Incremental, D=Differential)
    """
    params = {"limit": limit}
    if name:
        params["name"] = name
    if jobstatus:
        params["jobstatus"] = jobstatus
    if client:
        params["client"] = client
    if level:
        params["level"] = level
    return _get("/jobs", params)


@mcp.tool()
def get_job(jobid: int) -> str:
    """Get details for a specific job by its JobId.

    Args:
        jobid: The Bacula job ID
    """
    return _get(f"/jobs/{jobid}")


@mcp.tool()
def get_job_files(jobid: int, limit: int = 100, offset: int = 0, search: Optional[str] = None) -> str:
    """List files and directories backed up in a specific job.

    Args:
        jobid: The Bacula job ID
        limit: Max files to return (default 100)
        offset: Offset for pagination
        search: Search pattern to filter files
    """
    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search
    return _get(f"/jobs/{jobid}/files", params)


@mcp.tool()
def get_job_totals() -> str:
    """Get total bytes and files across all backup jobs."""
    return _get("/jobs/totals")


@mcp.tool()
def get_job_log(jobid: int) -> str:
    """Show bconsole output / details for a specific job.

    Args:
        jobid: The Bacula job ID
    """
    return _get(f"/jobs/{jobid}/show")


# --- Clients ---


@mcp.tool()
def get_clients(limit: int = 100) -> str:
    """List all backup clients (file daemons).

    Args:
        limit: Max clients to return (default 100)
    """
    return _get("/clients", {"limit": limit})


@mcp.tool()
def get_client(clientid: int) -> str:
    """Get details for a specific backup client.

    Args:
        clientid: The Bacula client ID
    """
    return _get(f"/clients/{clientid}")


@mcp.tool()
def get_client_jobs(clientid: int) -> str:
    """List all jobs for a specific client.

    Args:
        clientid: The Bacula client ID
    """
    return _get(f"/clients/{clientid}/jobs")


# --- Volumes & Pools ---


@mcp.tool()
def get_volumes(limit: int = 100) -> str:
    """List all backup volumes (tapes/disk volumes).

    Args:
        limit: Max volumes to return (default 100)
    """
    return _get("/volumes", {"limit": limit})


@mcp.tool()
def get_pools() -> str:
    """List all backup pools."""
    return _get("/pools")


@mcp.tool()
def get_pool_volumes(poolid: int) -> str:
    """List all volumes in a specific pool.

    Args:
        poolid: The Bacula pool ID
    """
    return _get(f"/pools/{poolid}/volumes")


# --- Storage ---


@mcp.tool()
def get_storages() -> str:
    """List all storage daemons."""
    return _get("/storages")


@mcp.tool()
def get_storage_status(storageid: int) -> str:
    """Get status of a specific storage daemon.

    Args:
        storageid: The Bacula storage ID
    """
    return _get(f"/storages/{storageid}/status")


if __name__ == "__main__":
    mcp.run(transport="stdio")
