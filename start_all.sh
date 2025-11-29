#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Voice Chatbot System Launcher${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping all services...${NC}"

    if [ ! -z "$BACKEND_PID" ]; then
        echo -e "${YELLOW}Stopping Backend API (PID: $BACKEND_PID)${NC}"
        kill $BACKEND_PID 2>/dev/null
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        echo -e "${YELLOW}Stopping Frontend (PID: $FRONTEND_PID)${NC}"
        kill $FRONTEND_PID 2>/dev/null
    fi

    # Kill any remaining child processes
    pkill -P $$ 2>/dev/null

    # Also clean up any api_server.py processes
    pkill -f "api_server.py" 2>/dev/null

    # Clean up any processes on port 5000
    BACKEND_PORT=$(lsof -ti:5000 2>/dev/null)
    if [ ! -z "$BACKEND_PORT" ]; then
        kill $BACKEND_PORT 2>/dev/null
    fi

    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup INT TERM

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed.${NC}"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed.${NC}"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
CHATBOT_DIR="$SCRIPT_DIR/chatbot"

# Check if directories exist
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}Error: Frontend directory not found at $FRONTEND_DIR${NC}"
    exit 1
fi

if [ ! -d "$CHATBOT_DIR" ]; then
    echo -e "${RED}Error: Chatbot directory not found at $CHATBOT_DIR${NC}"
    exit 1
fi

# Check and install frontend dependencies
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd "$FRONTEND_DIR"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install frontend dependencies${NC}"
        exit 1
    fi
    cd "$SCRIPT_DIR"
fi

# Check backend dependencies
echo -e "${BLUE}Checking backend dependencies...${NC}"
python3 -c "import flask; import flask_cors" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Installing backend dependencies...${NC}"
    pip3 install flask flask-cors
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install backend dependencies${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}Starting services...${NC}"
echo ""

# Check and kill any existing backend API processes
echo -e "${BLUE}Checking for existing processes...${NC}"
EXISTING_BACKEND=$(lsof -ti:5000 2>/dev/null)
if [ ! -z "$EXISTING_BACKEND" ]; then
    echo -e "${YELLOW}Found existing process on port 5000 (PID: $EXISTING_BACKEND), stopping it...${NC}"
    kill $EXISTING_BACKEND 2>/dev/null
    sleep 1
fi

# Also check for any api_server.py processes
pkill -f "api_server.py" 2>/dev/null
sleep 1

# Start Backend API
echo -e "${BLUE}[1/2] Starting Backend API...${NC}"
cd "$CHATBOT_DIR"
python3 api_server.py > /tmp/backend_api.log 2>&1 &
BACKEND_PID=$!
sleep 3

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Failed to start Backend API${NC}"
    echo -e "${YELLOW}Check logs: tail -f /tmp/backend_api.log${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Backend API started (PID: $BACKEND_PID)${NC}"
echo -e "  URL: ${BLUE}http://localhost:5000${NC}"
echo -e "  Logs: ${YELLOW}tail -f /tmp/backend_api.log${NC}"
echo ""

# Start Frontend
echo -e "${BLUE}[2/2] Starting Frontend...${NC}"
cd "$FRONTEND_DIR"
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 3

# Check if frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Failed to start Frontend${NC}"
    echo -e "${YELLOW}Check logs: tail -f /tmp/frontend.log${NC}"
    cleanup
    exit 1
fi
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "  URL: ${BLUE}http://localhost:3000${NC}"
echo -e "  Logs: ${YELLOW}tail -f /tmp/frontend.log${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Backend & Frontend Running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "  Backend API:  http://localhost:5000"
echo -e "  Frontend:     http://localhost:3000"
echo ""
echo -e "${BLUE}Background Logs:${NC}"
echo -e "  Backend:  tail -f /tmp/backend_api.log"
echo -e "  Frontend: tail -f /tmp/frontend.log"
echo ""
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}   Starting Chatbot (Interactive)${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo -e "${GREEN}Now you can interact with the chatbot!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""
echo -e "${BLUE}---[ Chatbot Output Below ]---${NC}"
echo ""

# Start Chatbot in foreground (interactive mode)
cd "$CHATBOT_DIR"

# Set environment variables for ONNX Runtime (required for Piper TTS on ARM64)
export OMP_NUM_THREADS=1
export ONNXRUNTIME_INTRA_OP_NUM_THREADS=1
export ONNXRUNTIME_INTER_OP_NUM_THREADS=1

# Enable GPU-accelerated Piper TTS (ONNX Runtime 1.23.0 + CUDA)
export USE_PIPER_TTS=true

python3 chatbot_cli.py

# When chatbot exits or Ctrl+C is pressed, cleanup
cleanup
