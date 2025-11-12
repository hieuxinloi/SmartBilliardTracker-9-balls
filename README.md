# 🎱 SmartBilliardTracker v2.0

**AI-Powered Billiards Analysis & Real-Time Referee System**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/react-18.2.0-blue.svg)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

---

## 🌟 Overview

SmartBilliardTracker is a comprehensive AI-powered system for billiards analysis and automatic refereeing. It combines computer vision, deep learning, and real-time processing to provide two powerful modes:

### 📹 Video Processing Mode
Analyze recorded billiards matches with:
- Automatic ball detection and tracking
- Collision detection and analysis
- Detailed match reports (JSON/CSV)
- Annotated video output
- Session management

### 🎮 Live Game Mode (NEW!)
Real-time AI referee for 9-ball billiards:
- Live ball detection from video or webcam
- Automatic turn management
- Foul detection and alerts
- Rule enforcement (9-ball)
- Match statistics and history
- Player vs Player gameplay

---

## ✨ Features

### Core Features
- ✅ **YOLOv8 Detection**: State-of-the-art object detection for accurate ball tracking
- ✅ **Real-time Processing**: Low-latency analysis with instant feedback
- ✅ **Dual Mode System**: Video analysis OR live game refereeing
- ✅ **WebSocket Support**: Real-time updates and event streaming
- ✅ **Modern UI**: Beautiful, responsive React interface
- ✅ **Export Capabilities**: JSON, CSV, and video outputs
- ✅ **Docker Ready**: One-command deployment

### Live Game Features
- ✅ Turn-based 9-ball gameplay
- ✅ Lowest ball rule enforcement
- ✅ Automatic foul detection
- ✅ Ball potting validation
- ✅ Victory conditions
- ✅ Match history saving
- ✅ Animated UI feedback

---

## 🚀 Quick Start

### Prerequisites

**Required:**
- Docker 20.10+ & Docker Compose 1.29+
- Git with Git LFS
- 8GB+ RAM
- Modern web browser

**Optional:**
- NVIDIA GPU with CUDA (for faster processing)
- Webcam (for live game mode)

### Installation

**Option 1: One-Command Start (Recommended)**

```bash
# Clone the repository
git clone https://github.com/yourusername/SmartBilliardTracker-9-balls.git
cd SmartBilliardTracker-9-balls

# Run the startup script
chmod +x start_game_system.sh
./start_game_system.sh
```

**Option 2: Manual Docker Start**

```bash
# Ensure Git LFS is installed
git lfs install
git lfs pull

# Start all services
docker compose up -d --build

# Check status
docker compose ps
```

**Option 3: Development Setup**

Backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start video processing API (port 8000)
uvicorn main:app --host 0.0.0.0 --port 8000

# Start game system API (port 8001)
python main_game.py
```

Frontend:
```bash
cd frontend
npm install
npm start  # Runs on port 3000
```

### Access the Application

Once started, open your browser:

- **Main App**: http://localhost:3000
- **Video Processing API**: http://localhost:8000 ([docs](http://localhost:8000/docs))
- **Live Game API**: http://localhost:8001 ([docs](http://localhost:8001/docs))

---

## 📖 Usage

### Video Processing Mode

1. **Access** http://localhost:3000 and select **"Video Processing"**
2. **Upload** a billiards video (MP4, AVI, MOV, MKV)
3. **Wait** for automatic processing
4. **Review** detected collisions and statistics
5. **Export** results as JSON/CSV or download annotated video

**Supported formats:** MP4, AVI, MOV, MKV  
**Max file size:** 500MB (configurable)

### Live Game Mode

1. **Access** http://localhost:3000 and select **"Live Game Mode"**
2. **Setup** player names and starting player
3. **Choose** video file OR enable webcam
4. **Click** "Start Game"
5. **Play** - AI automatically:
	 - Detects balls in real-time
	 - Tracks collisions
	 - Enforces 9-ball rules
	 - Detects fouls
	 - Switches turns
	 - Declares winner

**9-Ball Rules Enforced:**
- Must hit lowest numbered ball first
- Valid pot allows continuation
- Invalid hit = foul + turn change
- Potting 9-ball legally = win

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Frontend (React)                    │
│  ┌─────────────┐              ┌──────────────────┐  │
│  │   MainApp   │              │   Components     │  │
│  │  (Launcher) │──────────────│  - GameBoard     │  │
│  └─────────────┘              │  - PlayerPanel   │  │
│       │      │                │  - BallBar       │  │
│       │      │                │  - VictoryModal  │  │
│       │      └────────────────│  - FoulAlert     │  │
│       │                       └──────────────────┘  │
│       ▼                                              │
│  Video Mode          Live Game Mode                 │
└──────┬──────────────────────┬────────────────────────┘
			 │                      │
			 │ HTTP/WS              │ HTTP/WS
			 │ :8000                │ :8001
			 ▼                      ▼
┌──────────────────┐   ┌───────────────────────┐
│  Backend         │   │  Backend Game         │
│  (Video API)     │   │  (Real-time AI)       │
│                  │   │                       │
│  - main.py       │   │  - main_game.py       │
│  - Sessions      │   │  - game_manager.py    │
│  - Export        │   │  - Turn logic         │
└──────┬───────────┘   └───────┬───────────────┘
			 │                       │
			 └───────────┬───────────┘
									 ▼
				 ┌─────────────────────┐
				 │   AI Engine         │
				 │                     │
				 │  - YOLOv8 (balls)   │
				 │  - Collision detect │
				 │  - Pocket detection │
				 │  - Ball tracking    │
				 └─────────────────────┘
```

---

## 📂 Project Structure

```
SmartBilliardTracker-9-balls/
├── backend/
│   ├── main.py                 # Video processing API
│   ├── main_game.py           # Live game API
│   ├── game_manager.py        # Game logic & rules
│   ├── ball_detect.py         # YOLO detection
│   ├── detect_collision.py    # Collision algorithm
│   ├── pocket_detection.py    # Pocket detection (new)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── MainApp.js         # Mode launcher
│       ├── App.js             # Video processing UI
│       ├── AppGame.js         # Live game UI
│       ├── hooks/
│       │   └── useWebSocket.js
│       └── components/
│           ├── GameBoard.js
│           ├── PlayerPanel.js
│           ├── BallBar.js
│           ├── VictoryModal.js
│           └── FoulAlert.js
├── models/
│   └── yolov8n-ball-v.1.0.0.pt  # Custom trained model
├── docker-compose.yml         # Multi-service orchestration
├── start_game_system.sh       # Quick start script
├── GAME_SYSTEM_README.md      # Detailed user guide
├── DEPLOYMENT_GUIDE.md        # Production deployment
├── PRODUCT_ROADMAP.md         # Future plans
└── README.md                  # This file
```

---

## 🔌 API Reference

### Video Processing API (Port 8000)

**Upload Video**
```bash
POST /api/sessions/upload
Content-Type: multipart/form-data

# Response
{
	"session_id": "abc123",
	"video_name": "match.mp4",
	"status": "processing"
}
```

**Get Sessions**
```bash
GET /api/sessions

# Response
{
	"sessions": [
		{
			"session_id": "abc123",
			"video_name": "match.mp4",
			"status": "completed",
			"collisions_count": 8
		}
	]
}
```

### Live Game API (Port 8001)

**Start Game**
```bash
POST /api/game/start
{
	"player1_name": "Alice",
	"player2_name": "Bob",
	"starting_player": 0,
	"video_source": "path/to/video.mp4"
}
```

**WebSocket Events**
```javascript
ws://localhost:8001/ws/game

// Events received:
- frame_update    // Ball positions
- collision       // Collision detected
- foul           // Foul occurred
- turn_change    // Player turn switched
- game_end       // Winner declared
```

Full API documentation: [http://localhost:8000/docs](http://localhost:8000/docs) & [http://localhost:8001/docs](http://localhost:8001/docs)

---

## 🧪 Testing

```bash
# Test with provided video
# Video file is in: video_test/10.mp4

# Option 1: Via UI
# 1. Open http://localhost:3000
# 2. Select "Video Processing" or "Live Game Mode"
# 3. Upload video_test/10.mp4

# Option 2: Via API
curl -X POST http://localhost:8000/api/sessions/upload \
	-F "file=@video_test/10.mp4"
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```bash
# Backend
API_PORT=8000
GAME_API_PORT=8001
MODEL_PATH=models/yolov8n-ball-v.1.0.0.pt
CONFIDENCE_THRESHOLD=0.1
MAX_UPLOAD_SIZE=500000000

# Frontend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_GAME_API_URL=http://localhost:8001
REACT_APP_GAME_WS_URL=ws://localhost:8001/ws/game
```

### Model Configuration

The system uses a custom-trained YOLOv8 model for billiard ball detection. The model file is managed via Git LFS and automatically pulled during setup.

**Model details:**
- Format: PyTorch (.pt)
- Size: ~6MB
- Classes: cueball, ball_1-9
- Training: Custom dataset of billiards videos

---

## 📊 Performance

**Video Processing:**
- Detection speed: ~30 FPS (CPU), ~60+ FPS (GPU)
- Accuracy: >95% ball detection
- Processing time: ~1 min per minute of video (CPU)

**Live Game:**
- Latency: <100ms per frame
- Real-time updates via WebSocket
- Supports 720p and 1080p streams

---

## 🚢 Production Deployment

See **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** for comprehensive deployment instructions including:

- Docker production configuration
- AWS deployment (ECS, EC2)
- Azure deployment (ACI, App Service)
- GCP deployment (Cloud Run, GKE)
- Nginx configuration
- SSL/HTTPS setup
- Scaling strategies
- Monitoring & logging

---

## 🗺️ Roadmap

See **[PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)** for detailed future plans.

**Upcoming Features:**
- [ ] Enhanced pocket detection (visual detection)
- [ ] Mobile app (React Native)
- [ ] Multi-camera support
- [ ] Tournament bracket mode
- [ ] Advanced analytics dashboard
- [ ] Player recognition
- [ ] Shot prediction
- [ ] Replay system with timeline

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📞 Support

- **Documentation**: See [GAME_SYSTEM_README.md](GAME_SYSTEM_README.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/SmartBilliardTracker-9-balls/issues)
- **Deployment**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## 🙏 Acknowledgments

- YOLOv8 by Ultralytics
- FastAPI framework
- React & TailwindCSS
- OpenCV community
- Billiards community for testing and feedback

---

## 📸 Screenshots

### Mode Selection
Beautiful landing page to choose between Video Processing or Live Game modes.

### Live Game Interface
Real-time game board with ball detection overlays, player panels, ball tracker, and instant foul alerts.

### Video Processing
Session management with collision detection, detailed reports, and export capabilities.

---

**Built with ❤️ for the billiards community**

**Version 2.0** | Last Updated: 2025-11-12

---

## 🚀 Getting Started Now

```bash
# Quick start in 3 commands:
git clone https://github.com/yourusername/SmartBilliardTracker-9-balls.git
cd SmartBilliardTracker-9-balls
./start_game_system.sh

# Then open: http://localhost:3000
```

**That's it! Start analyzing and refereeing billiards matches with AI! 🎱**
