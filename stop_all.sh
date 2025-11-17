#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping all Voice Chatbot services...${NC}"
echo ""

# Function to kill process by name and port
kill_by_port() {
    local port=$1
    local name=$2

    PID=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$PID" ]; then
        echo -e "${YELLOW}Stopping $name (Port $port, PID: $PID)${NC}"
        kill $PID 2>/dev/null
        sleep 1
        # Force kill if still running
        if kill -0 $PID 2>/dev/null; then
            kill -9 $PID 2>/dev/null
        fi
        echo -e "${GREEN}✓ $name stopped${NC}"
    else
        echo -e "${GREEN}✓ $name not running${NC}"
    fi
}

# Stop Backend API (port 5000)
kill_by_port 5000 "Backend API"

# Stop Frontend (port 3000)
kill_by_port 3000 "Frontend"

# Stop Chatbot (by process name)
echo -e "${YELLOW}Stopping Chatbot...${NC}"
CHATBOT_PIDS=$(pgrep -f "python.*main.py" 2>/dev/null)
if [ ! -z "$CHATBOT_PIDS" ]; then
    for PID in $CHATBOT_PIDS; do
        # Check if this is the chatbot main.py
        if ps -p $PID -o args= | grep -q "chatbot.*main.py"; then
            kill $PID 2>/dev/null
            sleep 1
            if kill -0 $PID 2>/dev/null; then
                kill -9 $PID 2>/dev/null
            fi
            echo -e "${GREEN}✓ Chatbot stopped (PID: $PID)${NC}"
        fi
    done
else
    echo -e "${GREEN}✓ Chatbot not running${NC}"
fi

# Clean up log files (optional)
if [ "$1" == "--clean-logs" ]; then
    echo ""
    echo -e "${YELLOW}Cleaning log files...${NC}"
    rm -f /tmp/backend_api.log /tmp/frontend.log /tmp/chatbot.log
    echo -e "${GREEN}✓ Logs cleaned${NC}"
fi

echo ""
echo -e "${GREEN}All services stopped.${NC}"
