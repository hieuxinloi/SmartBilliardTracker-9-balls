#!/bin/bash

# 🎱 Smart Billiards AI Referee - Quick Start Script

echo "🎱 Starting Smart Billiards AI Referee System..."
echo ""

#!/bin/bash

echo "🎱 SmartBilliardTracker - Complete System Startup"
echo "=================================================="
echo ""

# Check if Git LFS is installed
if ! command -v git-lfs &> /dev/null; then
    echo "❌ Git LFS is not installed!"
    echo "Installing Git LFS..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y git-lfs
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install git-lfs
    else
        echo "Please install Git LFS manually: https://git-lfs.github.com/"
        exit 1
    fi
fi

# Initialize Git LFS and pull models
echo "📦 Pulling model files with Git LFS..."
git lfs install
git lfs pull

if [ ! -f "models/yolov8n-ball-v.1.0.0.pt" ]; then
    echo "❌ Model file not found after git lfs pull!"
    echo "Please check your Git LFS setup"
    exit 1
fi

echo "✅ Model files ready"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "Please start Docker and try again"
    exit 1
fi

echo "� Building and starting Docker containers..."
echo "   - Backend (Video Processing): Port 8000"
echo "   - Backend (Live Game System): Port 8001"
echo "   - Frontend (React UI): Port 3000"
echo ""
docker compose up -d --build

echo ""
echo "⏳ Waiting for services to start..."
sleep 15

# Check if services are running
RUNNING_SERVICES=$(docker compose ps --services --filter "status=running" | wc -l)

if [ "$RUNNING_SERVICES" -ge 3 ]; then
    echo ""
    echo "✅ All systems operational!"
    echo "=================================================="
    echo ""
    echo "� Access Points:"
    echo "   📱 Main Application: http://localhost:3000"
    echo "      └─ Choose between:"
    echo "         • Video Processing Mode (analyze recorded videos)"
    echo "         • Live Game Mode (real-time AI referee)"
    echo ""
    echo "   � API Endpoints:"
    echo "      • Video Processing API: http://localhost:8000"
    echo "      • Live Game API: http://localhost:8001"
    echo ""
    echo "   📚 Documentation:"
    echo "      • API Docs (Video): http://localhost:8000/docs"
    echo "      • API Docs (Game): http://localhost:8001/docs"
    echo "      • User Guide: GAME_SYSTEM_README.md"
    echo "      • Deployment: DEPLOYMENT_GUIDE.md"
    echo ""
    echo "🎮 Quick Start:"
    echo "   1. Open http://localhost:3000"
    echo "   2. Select your mode:"
    echo "      • Video Processing: Upload and analyze match recordings"
    echo "      • Live Game: Real-time referee for 9-ball billiards"
    echo "   3. Follow the on-screen instructions"
    echo ""
    echo "📊 Monitoring:"
    echo "   • View logs: docker compose logs -f"
    echo "   • Check status: docker compose ps"
    echo "   • Resource usage: docker stats"
    echo ""
    echo "🛑 System Control:"
    echo "   • Stop all services: docker compose down"
    echo "   • Restart: docker compose restart"
    echo "   • View specific logs: docker compose logs -f [backend|backend-game|frontend]"
    echo ""
    echo "🎉 Ready! The AI-powered billiards system is now running."
    echo "=================================================="
else
    echo ""
    echo "⚠️  Warning: Not all services started successfully"
    echo "Running services: $RUNNING_SERVICES / 3"
    echo ""
    echo "Checking service status..."
    docker compose ps
    echo ""
    echo "For detailed logs, run:"
    echo "   docker compose logs backend"
    echo "   docker compose logs backend-game"
    echo "   docker compose logs frontend"
    echo ""
    echo "Common issues:"
    echo "   • Port already in use: Check if ports 3000, 8000, 8001 are available"
    echo "   • Out of memory: Ensure at least 8GB RAM available for Docker"
    echo "   • Model not loaded: Run 'git lfs pull' manually"
    exit 1
fi
