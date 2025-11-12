# 🚀 Quick Start Guide - SmartBilliardTracker

## For Developers

### 1. Clone & Setup

```bash
cd SmartBilliardTracker-9-balls

# Ensure model file is in place
ls models/yolov8n-ball-v.1.0.0.pt
```

### 2. Option A: Docker (Fastest)

```bash
# Start everything
./start.sh

# OR manually
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Option B: Manual Development

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

### 4. Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 5. Test Upload

1. Open http://localhost:3000
2. Drag & drop a billiards video
3. Watch real-time processing
4. View collisions when complete
5. Download results

### 6. API Example

```bash
# Upload video
curl -X POST http://localhost:8000/api/sessions/upload \
  -F "file=@your_video.mp4"

# Get session
curl http://localhost:8000/api/sessions/{session_id}

# Export collisions
curl http://localhost:8000/api/sessions/{session_id}/collisions/export?format=json
```

### 7. Stop Services

```bash
docker-compose down
```

## Troubleshooting

**Port already in use:**
```bash
# Change ports in docker-compose.yml
ports:
  - "3001:3000"  # Frontend
  - "8001:8000"  # Backend
```

**Model not found:**
```bash
# Ensure model is in correct location
mkdir -p models
cp /path/to/your/model.pt models/yolov8n-ball-v.1.0.0.pt
```

**Memory issues:**
- Reduce video resolution before upload
- Use CPU instead of GPU in backend/main.py
- Increase Docker memory limit

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) for future features
- View API docs at http://localhost:8000/docs

Happy coding! 🎱
