#!/bin/bash

# Proxmox MCP - Setup Script

set -e

echo "Initializing Proxmox MCP Server..."

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install it first."
    exit 1
fi

# 2. Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

# 3. Install package in editable mode
echo "Installing package..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e ".[dev]"

# 4. Handle .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "ACTION REQUIRED: Please edit the '.env' file with your Proxmox credentials."
else
    echo ".env file already exists."
fi

echo "--------------------------------------------------------"
echo "Setup Complete!"
echo "--------------------------------------------------------"
echo "1. Verify your credentials in the '.env' file."
echo "2. Test your connection: .venv/bin/python scripts/test_connection.py"
echo "3. Run the dashboard:    .venv/bin/python scripts/admin_dashboard.py"
echo "4. Run the server:       .venv/bin/python -m proxmox_mcp"
echo "5. Run tests:            .venv/bin/pytest"
echo "--------------------------------------------------------"
