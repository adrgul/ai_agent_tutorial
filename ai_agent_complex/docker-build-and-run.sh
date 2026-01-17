#!/bin/bash
# Docker Build and Run Script for AI Agent Complex with Advanced Agent
# Date: 2026-01-13
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${2}${1}${NC}"
}

# Print section header
print_header() {
    echo ""
    echo "========================================================================"
    print_message "$1" "$BLUE"
    echo "========================================================================"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_message "❌ Docker is not installed!" "$RED"
        print_message "Please install Docker from: https://www.docker.com/get-started" "$YELLOW"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_message "❌ docker-compose is not installed!" "$RED"
        print_message "Please install docker-compose" "$YELLOW"
        exit 1
    fi

    print_message "✅ Docker and docker-compose are installed" "$GREEN"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_message "⚠️  .env file not found. Creating from .env.example..." "$YELLOW"
        cp .env.example .env
        print_message "📝 Please edit .env and add your API keys:" "$YELLOW"
        print_message "   - OPENAI_API_KEY (required)" "$YELLOW"
        print_message "   - ALPHAVANTAGE_API_KEY (optional, defaults to 'demo')" "$YELLOW"
        print_message "" "$YELLOW"
        read -p "Press Enter after you've updated .env file, or Ctrl+C to exit..."
    else
        print_message "✅ .env file found" "$GREEN"
    fi

    # Check if required keys are set
    source .env
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        print_message "❌ OPENAI_API_KEY is not set in .env file!" "$RED"
        print_message "Please edit .env and add your OpenAI API key" "$YELLOW"
        exit 1
    fi

    print_message "✅ OPENAI_API_KEY is set" "$GREEN"

    if [ -z "$ALPHAVANTAGE_API_KEY" ] || [ "$ALPHAVANTAGE_API_KEY" = "your_alphavantage_api_key_here" ]; then
        print_message "⚠️  ALPHAVANTAGE_API_KEY not set, using 'demo' (rate limited)" "$YELLOW"
        export ALPHAVANTAGE_API_KEY="demo"
    else
        print_message "✅ ALPHAVANTAGE_API_KEY is set" "$GREEN"
    fi
}

# Stop and remove existing containers
cleanup_containers() {
    print_header "Cleaning up existing containers"

    if [ "$(docker ps -aq -f name=ai-agent)" ]; then
        print_message "Stopping and removing existing containers..." "$YELLOW"
        docker-compose down -v
        print_message "✅ Cleanup complete" "$GREEN"
    else
        print_message "No existing containers to clean up" "$GREEN"
    fi
}

# Build Docker images
build_images() {
    print_header "Building Docker Images"

    print_message "Building backend image..." "$YELLOW"
    docker-compose build backend
    print_message "✅ Backend image built" "$GREEN"

    print_message "Building frontend image..." "$YELLOW"
    docker-compose build frontend
    print_message "✅ Frontend image built" "$GREEN"
}

# Start containers
start_containers() {
    print_header "Starting Containers"

    print_message "Starting services with docker-compose..." "$YELLOW"
    docker-compose up -d

    print_message "✅ Containers started" "$GREEN"
}

# Wait for services to be healthy
wait_for_services() {
    print_header "Waiting for Services to Start"

    print_message "Waiting for backend to be ready..." "$YELLOW"
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker exec ai-agent-backend curl -s http://localhost:8000/ > /dev/null 2>&1; then
            print_message "✅ Backend is ready!" "$GREEN"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    echo ""

    if [ $elapsed -ge $timeout ]; then
        print_message "⚠️  Backend health check timed out (might still be starting)" "$YELLOW"
    fi

    print_message "Waiting for frontend to be ready..." "$YELLOW"
    sleep 5
    print_message "✅ Frontend should be ready!" "$GREEN"
}

# Show status
show_status() {
    print_header "Container Status"
    docker-compose ps
}

# Show logs
show_logs() {
    print_header "Recent Logs"
    print_message "Backend logs:" "$BLUE"
    docker-compose logs --tail=20 backend
    echo ""
    print_message "Frontend logs:" "$BLUE"
    docker-compose logs --tail=20 frontend
}

# Show access information
show_access_info() {
    print_header "🎉 Application is Running!"

    echo ""
    print_message "📱 Frontend (Web UI):" "$GREEN"
    print_message "   URL: http://localhost:3000" "$BLUE"
    echo ""

    print_message "🔧 Backend (API):" "$GREEN"
    print_message "   URL: http://localhost:8000" "$BLUE"
    print_message "   Docs: http://localhost:8000/docs" "$BLUE"
    echo ""

    print_message "🤖 Advanced Agent Features:" "$GREEN"
    print_message "   ✅ MCP Integration (AlphaVantage + DeepWiki)" "$BLUE"
    print_message "   ✅ Parallel Execution (2-6x speedup)" "$BLUE"
    print_message "   ✅ Plan-and-Execute Pattern" "$BLUE"
    print_message "   ✅ Dynamic Routing" "$BLUE"
    print_message "   ✅ Multi-step Loop-back" "$BLUE"
    echo ""

    print_message "📋 Useful Commands:" "$YELLOW"
    echo "   View logs:        docker-compose logs -f"
    echo "   Stop services:    docker-compose down"
    echo "   Restart:          docker-compose restart"
    echo "   Rebuild:          docker-compose up -d --build"
    echo ""

    print_message "🧪 Test Prompts:" "$GREEN"
    echo "   Try: 'Get me the current stock prices for Apple (AAPL), Microsoft (MSFT), and Google (GOOGL).'"
    echo "   See: ADVANCED_AGENT_TEST_PROMPTS.md for more examples"
    echo ""
}

# Main execution
main() {
    print_header "🚀 AI Agent Complex - Docker Build and Run"
    print_message "Advanced Agent is ACTIVE with MCP Integration!" "$GREEN"

    # Check prerequisites
    check_docker
    check_env_file

    # Ask for confirmation
    echo ""
    read -p "Ready to build and run? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_message "Cancelled by user" "$YELLOW"
        exit 0
    fi

    # Execute build and run steps
    cleanup_containers
    build_images
    start_containers
    wait_for_services
    show_status
    show_logs
    show_access_info

    print_message "✅ All done! Open http://localhost:3000 in your browser" "$GREEN"
}

# Run main function
main
