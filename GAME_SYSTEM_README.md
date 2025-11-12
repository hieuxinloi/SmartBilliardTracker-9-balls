# 🎱 Smart Billiards AI Referee - Game System

Real-time AI-powered referee system for 9-ball billiards with automatic turn tracking, foul detection, and game management.

## 🎯 Features

### Core Game Features
- ✅ **Real-time Ball Detection** - YOLOv8 AI detects all balls on table
- ✅ **Collision Detection** - Automatic cueball-to-ball collision tracking  
- ✅ **Turn Management** - Automatic player turn switching
- ✅ **Foul Detection** - Identifies invalid hits and rule violations
- ✅ **Score Tracking** - Tracks potted balls for each player
- ✅ **9-Ball Win Condition** - Auto-detects game winner
- ✅ **Live WebSocket Updates** - Real-time game events
- ✅ **Video or Camera Support** - Upload videos or use live webcam

### UI Features
- 🎨 **Modern React Interface** - Beautiful, responsive design
- 📊 **Player Panels** - Live stats, potted balls, fouls
- 🎯 **Ball Tracker** - Visual display of all balls on table
- 🚨 **Foul Alerts** - Animated red flash warnings
- 🏆 **Victory Modal** - End-game celebration with match stats
- 🎮 **Easy Setup** - Simple player name and video selection

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git LFS (for model files)
- 8GB+ RAM recommended

### Installation

```bash
# Clone repository
git clone <repository-url>
cd SmartBilliardTracker-9-balls

# Run quick start script
./start_game_system.sh
```

That's it! The system will:
1. Install Git LFS if needed
2. Pull model files
3. Build Docker containers
4. Start all services

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws/game

## 🎮 How to Use

### 1. Setup Game
1. Open http://localhost:3000
2. Enter player names (Player 1 & Player 2)
3. Select who starts first
4. Choose video source:
   - **Upload Video**: Select MP4/AVI/MOV file
   - **Use Camera**: Enable webcam (requires camera permission)

### 2. Start Game
1. Click "🎮 Start Game"
2. AI begins detecting balls in real-time
3. Watch the game board for live detection overlays

### 3. Game Rules (9-Ball)
- Players alternate turns
- Must hit **lowest numbered ball first**
- If valid ball is potted, player continues
- **Fouls** result in turn change and ball reversion
- Game ends when **9-ball is legally potted**

### 4. During Game
- **Green circle** = Cueball detection
- **Colored circles** = Numbered balls
- **Yellow line** = Collision detected
- **Red flash** = Foul occurred
- **Turn indicator** = Shows current player

### 5. Game End
- Victory modal displays winner
- Match statistics shown
- Options to restart or view details

## 📁 Project Structure

```
SmartBilliardTracker-9-balls/
├── backend/
│   ├── main_game.py              # New game API server
│   ├── game_manager.py           # Game logic and state
│   ├── ball_detect.py            # YOLO detection
│   ├── detect_collision.py       # Collision algorithm
│   ├── utils.py                  # Helper functions
│   ├── requirements.txt
│   └── data/
│       └── matches.json          # Match history
├── frontend/
│   └── src/
│       ├── AppGame.js            # Main game UI
│       ├── hooks/
│       │   └── useWebSocket.js   # WebSocket hook
│       └── components/
│           ├── GameBoard.js      # Video + detection overlay
│           ├── PlayerPanel.js    # Player info display
│           ├── BallBar.js        # Ball tracker
│           ├── VictoryModal.js   # End-game modal
│           └── FoulAlert.js      # Foul warning
├── models/
│   └── yolov8n-ball-v.1.0.0.pt  # Trained model
├── docker-compose.yml
└── start_game_system.sh          # Quick start script
```

## 🔌 API Endpoints

### Game Management

#### Start Game
```http
POST /api/game/start
Content-Type: application/json

{
  "player1_name": "Alice",
  "player2_name": "Bob",
  "starting_player": 0,
  "use_camera": false,
  "video_path": "/path/to/video.mp4"
}
```

#### Stop Game
```http
POST /api/game/stop
Content-Type: application/json

{
  "reason": "user_stop"
}
```

#### Get Game State
```http
GET /api/game/state
```

Response:
```json
{
  "state": "playing",
  "match_id": "20251112_143022",
  "players": [
    {
      "id": 0,
      "name": "Alice",
      "potted_balls": [1, 3, 5],
      "foul_count": 1,
      "is_current": true
    },
    {
      "id": 1,
      "name": "Bob",
      "potted_balls": [2, 4],
      "foul_count": 0,
      "is_current": false
    }
  ],
  "current_player": "Alice",
  "balls_on_table": [6, 7, 8, 9],
  "lowest_ball": 6,
  "last_hit_ball": 6,
  "balls_moving": false
}
```

#### Restart Game
```http
POST /api/game/restart
```

#### Match History
```http
GET /api/game/history
```

### WebSocket Events

Connect to: `ws://localhost:8000/ws/game`

#### Client → Server
```json
{
  "type": "heartbeat"
}
```

#### Server → Client Events

**Connection**
```json
{
  "event": "connected",
  "game_state": { ... }
}
```

**Frame Update**
```json
{
  "event": "frame_update",
  "frame_idx": 123,
  "balls": [
    {
      "name": "cueball",
      "x": 640.5,
      "y": 360.2,
      "r": 12.5,
      "conf": 0.95
    }
  ],
  "game_state": { ... }
}
```

**Collision**
```json
{
  "event": "first_hit",
  "ball": 5,
  "ball_name": "bi5",
  "valid": true,
  "lowest_ball": 5,
  "player": "Alice",
  "message": "Alice hit ball 5"
}
```

**Foul**
```json
{
  "event": "foul",
  "player": "Bob",
  "reason": "Did not hit ball 3 first",
  "reverted_balls": [5, 7],
  "message": "Foul by Bob: Did not hit ball 3 first"
}
```

**Turn Change**
```json
{
  "event": "turn_change",
  "player": "Alice",
  "message": "Turn: Alice"
}
```

**Game End**
```json
{
  "event": "game_end",
  "winner": "Alice",
  "winner_id": 0,
  "player1_score": 5,
  "player2_score": 4,
  "player1_fouls": 1,
  "player2_fouls": 2,
  "duration": 1250.5,
  "message": "🏆 Alice wins!"
}
```

## 🎯 Game Logic

### Turn Flow
1. Player's turn starts
2. Cueball must hit **lowest numbered ball** first
3. If valid hit and ball potted → player continues
4. If invalid hit → **FOUL** → turn changes
5. If no ball potted after movement stops → turn changes

### Foul Conditions
- ❌ Hit wrong ball first (not lowest)
- ❌ Cueball scratched (potted)
- ❌ No ball hit
- ❌ Ball off table

### Win Condition
- ✅ Legally pot the 9-ball (after hitting lowest ball first)

## 🛠️ Development

### Run Backend Only
```bash
cd backend
python main_game.py
```

### Run Frontend Only
```bash
cd frontend
npm install
npm start
```

### Watch Logs
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### Rebuild Containers
```bash
docker compose up -d --build
```

## 🧪 Testing

### Test Video Processing
```bash
# Upload test video
curl -X POST -F "file=@video_test/10.mp4" http://localhost:8000/api/sessions/upload

# Start game with video
curl -X POST http://localhost:8000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{
    "player1_name": "Test Player 1",
    "player2_name": "Test Player 2",
    "starting_player": 0,
    "use_camera": false,
    "video_path": "uploads/20251112_143022_10.mp4"
  }'
```

### Test WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/game');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
};

// Send heartbeat
ws.send(JSON.stringify({ type: 'heartbeat' }));
```

## 📊 Performance

### System Requirements
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **GPU**: Optional (CUDA for faster processing)
- **Storage**: 2GB for models and dependencies

### Processing Speed
- **Detection**: ~30 FPS on CPU, ~60+ FPS on GPU
- **Collision**: Real-time (< 100ms per frame)
- **Latency**: < 200ms end-to-end

## 🔧 Troubleshooting

### Model File Issues
```bash
# Re-pull model files
git lfs pull

# Check model file
file models/yolov8n-ball-v.1.0.0.pt
# Should show: "Zip archive data" (not "ASCII text")
```

### Docker Issues
```bash
# Reset everything
docker compose down -v
docker system prune -af
./start_game_system.sh
```

### WebSocket Not Connecting
- Check firewall settings
- Verify backend is running: `curl http://localhost:8000/health`
- Check browser console for errors

### Camera Not Working
- Grant camera permissions in browser
- Check if camera is available: `ls /dev/video*`
- Try different browser (Chrome recommended)

## 📝 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Submit pull request

## 📧 Support

- Issues: Create GitHub issue
- Docs: See PRODUCT_ROADMAP.md
- API: http://localhost:8000/docs

---

**Made with ❤️ for billiards enthusiasts and AI developers**

🎱 **Game on!**
