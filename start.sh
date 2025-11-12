#!/bin/bash

echo "🎱 Starting SmartBilliardTracker..."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
mkdir -p uploads outputs models

# Check if model exists
if [ ! -f "models/yolov8n-ball-v.1.0.0.pt" ]; then
    echo "⚠️  Model file not found at models/yolov8n-ball-v.1.0.0.pt"
    echo "Please place your trained model in the models/ directory"
    exit 1
fi

# Start services
echo "🚀 Starting services with Docker Compose..."
docker compose up -d

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📱 Access the application:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "📊 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo ""
