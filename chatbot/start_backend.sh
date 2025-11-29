#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Starting Backend API Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    # Try to use the agent310 virtual environment
    if [ -f "$SCRIPT_DIR/../agent310/bin/activate" ]; then
        echo -e "${YELLOW}Activating virtual environment...${NC}"
        source "$SCRIPT_DIR/../agent310/bin/activate"
    else
        echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    fi
fi

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"
python -c "import flask; import flask_cors" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install flask flask-cors
fi

echo ""
echo -e "${GREEN}Starting Backend API Server...${NC}"
echo -e "${BLUE}URL: http://localhost:5000${NC}"
echo -e "${BLUE}Health check: http://localhost:5000/health${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Start the backend API
cd "$SCRIPT_DIR"
python api_server.py
