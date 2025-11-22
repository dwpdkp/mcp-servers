# Weather MCP Server

A Model Context Protocol (MCP) server that provides weather alerts and forecasts using the National Weather Service (NWS) API.

## Features

- Get active weather alerts for any US state
- Get detailed weather forecasts for any location by coordinates
- Uses the official NWS API (no API key required)
- Async HTTP requests with proper error handling

## Prerequisites

- Python 3.13 or higher
- Internet connection (for NWS API access)

## Installation

1. Clone or navigate to this repository
2. Install dependencies:

```bash
pip install -e .
```

Or using uv:

```bash
uv pip install -e .
```

### Dependencies

- `httpx>=0.28.1` - Async HTTP client
- `mcp[cli]>=1.14.1` - Model Context Protocol SDK

## Usage

### Running the Server

Start the MCP server:

```bash
python weather.py
```

The server will start in stdio mode.

### MCP Configuration

Add this configuration to your MCP client settings:

```json
{
  "mcpServers": {
    "weather": {
      "command": "uvx",
      "args": [
        "mcp[cli]",
        "run",
        "<install path>/weather/weather.py"
      ]
    }
  }
}
```

Replace `<install path>` with the actual path where you installed this package.

### Available Tools

#### get_alerts

Get active weather alerts for a US state.

**Parameters:**
- `state` (string): Two-letter US state code (e.g., CA, NY, TX)

**Returns:**
- Formatted list of active alerts including:
  - Event type
  - Affected area
  - Severity level
  - Description
  - Instructions
- Message indicating no alerts if none are active
- Error message if unable to fetch data

**Example Usage:**
```
get_alerts("CA")  # Get alerts for California
get_alerts("NY")  # Get alerts for New York
```

#### get_forecast

Get weather forecast for a specific location.

**Parameters:**
- `latitude` (float): Latitude of the location
- `longitude` (float): Longitude of the location

**Returns:**
- Detailed forecast for the next 5 periods, each including:
  - Period name (e.g., "Tonight", "Monday", "Monday Night")
  - Temperature with unit
  - Wind speed and direction
  - Detailed forecast description
- Error message if unable to fetch data

**Example Usage:**
```
get_forecast(37.7749, -122.4194)  # San Francisco
get_forecast(40.7128, -74.0060)   # New York City
```

## Technical Details

### API Information

This server uses the National Weather Service API:
- Base URL: `https://api.weather.gov`
- User-Agent: `weather-app/1.0`
- Accept Header: `application/geo+json`
- Request timeout: 30 seconds

### Error Handling

The server handles the following error scenarios:
- HTTP errors from the NWS API
- Network/connection errors
- Invalid JSON responses
- Missing data in API responses

All errors return user-friendly messages rather than crashing the server.

### Notes

- The NWS API only covers US locations
- The server registers as "weather" in MCP client interfaces
- Forecasts show 5 periods to balance detail with readability
- The `main.py` file is a placeholder; the actual server is in `weather.py`

## MCP Integration

This server implements the Model Context Protocol, allowing AI assistants to access real-time weather data. The server can be connected to any MCP-compatible client such as Claude Desktop or other MCP-enabled applications.

## License

This project uses the public NWS API which is free and does not require authentication.
