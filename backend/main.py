"""
SmartBilliardTracker Backend API
FastAPI server for billiards referee support system
"""

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
import shutil

# Add parent directory to path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import get_collisions_from_video

app = FastAPI(
    title="SmartBilliardTracker API",
    description="AI-powered billiards referee support system",
    version="1.0.0",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory setup
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory storage (use database in production)
sessions = {}  # session_id: {video_path, status, collisions, created_at}
active_connections: List[WebSocket] = []


# ============= Models =============
class SessionResponse(BaseModel):
    session_id: str
    status: str
    message: str


class CollisionResponse(BaseModel):
    cueball: Dict
    ball: Dict
    frame_id: int


class SessionDetail(BaseModel):
    session_id: str
    status: str
    video_name: str
    collisions: List[CollisionResponse]
    created_at: str
    output_video_url: Optional[str] = None


# ============= WebSocket Manager =============
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


# ============= Background Tasks =============
async def process_video_task(session_id: str, video_path: str):
    """Background task to process video and detect collisions"""
    try:
        sessions[session_id]["status"] = "processing"
        await manager.broadcast(
            {
                "type": "status_update",
                "session_id": session_id,
                "status": "processing",
                "message": "Analyzing video...",
            }
        )

        # Get output paths
        output_dir = OUTPUT_DIR / session_id
        output_dir.mkdir(exist_ok=True)
        output_video_path = output_dir / f"output_{Path(video_path).name}"

        # Pre-checks for diagnostics
        # Use custom trained model for billiards
        model_path = "models/yolov8n-ball-v.1.0.0.pt"
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Process video and get collisions
        collisions = get_collisions_from_video(
            video_path=video_path,
            model_path=model_path,
            output_dir=str(output_dir),
            output_video_path=str(output_video_path),
            conf_threshold=0.1,
            merge_iou_threshold=0.7,
            create_output_video=True,
        )

        # Convert numpy types to Python native types for JSON serialization
        def convert_numpy_types(obj):
            """Recursively convert numpy types to Python native types"""
            import numpy as np

            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            return obj

        collisions = convert_numpy_types(collisions)

        # Update session
        sessions[session_id]["status"] = "completed"
        sessions[session_id]["collisions"] = collisions
        sessions[session_id]["output_video"] = str(output_video_path)

        # Broadcast completion
        await manager.broadcast(
            {
                "type": "processing_complete",
                "session_id": session_id,
                "status": "completed",
                "collisions_count": len(collisions),
                "message": f"Found {len(collisions)} collisions",
            }
        )

    except Exception as e:
        import traceback

        err_msg = f"{type(e).__name__}: {str(e)}"
        # Log full traceback to the server logs
        traceback.print_exc()
        sessions[session_id]["status"] = "error"
        sessions[session_id]["error"] = err_msg
        await manager.broadcast(
            {
                "type": "error",
                "session_id": session_id,
                "status": "error",
                "message": f"Error processing video: {err_msg}",
            }
        )


# ============= API Endpoints =============


@app.get("/")
async def root():
    return {"app": "SmartBilliardTracker API", "version": "1.0.0", "status": "running"}


@app.post("/api/sessions/upload", response_model=SessionResponse)
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a video file and create a new processing session
    """
    # Validate file type
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(
            status_code=400,
            detail="Invalid video format. Supported: mp4, avi, mov, mkv",
        )

    # Create session
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    video_path = UPLOAD_DIR / f"{session_id}_{file.filename}"

    # Save uploaded file
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Store session
    sessions[session_id] = {
        "video_path": str(video_path),
        "video_name": file.filename,
        "status": "uploaded",
        "collisions": [],
        "created_at": datetime.now().isoformat(),
    }

    # Start processing in background
    background_tasks.add_task(process_video_task, session_id, str(video_path))

    return SessionResponse(
        session_id=session_id,
        status="uploaded",
        message="Video uploaded successfully. Processing started.",
    )


@app.get("/api/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    """
    Get session details including collisions
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    output_video_url = None
    if session["status"] == "completed" and "output_video" in session:
        output_video_url = f"/api/sessions/{session_id}/video/output"

    return SessionDetail(
        session_id=session_id,
        status=session["status"],
        video_name=session["video_name"],
        collisions=[CollisionResponse(**c) for c in session.get("collisions", [])],
        created_at=session["created_at"],
        output_video_url=output_video_url,
    )


@app.get("/api/sessions")
async def list_sessions():
    """
    List all sessions
    """
    return {
        "sessions": [
            {
                "session_id": sid,
                "video_name": data["video_name"],
                "status": data["status"],
                "collisions_count": len(data.get("collisions", [])),
                "created_at": data["created_at"],
            }
            for sid, data in sessions.items()
        ]
    }


@app.get("/api/sessions/{session_id}/video/output")
async def get_output_video(session_id: str):
    """
    Download processed output video
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    if session["status"] != "completed" or "output_video" not in session:
        raise HTTPException(status_code=400, detail="Output video not ready")

    video_path = session["output_video"]
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Output video file not found")

    return FileResponse(
        video_path, media_type="video/mp4", filename=f"output_{session['video_name']}"
    )


@app.get("/api/sessions/{session_id}/collisions/export")
async def export_collisions(session_id: str, format: str = "json"):
    """
    Export collisions data in JSON or CSV format
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    collisions = session.get("collisions", [])

    if format == "json":
        return {"collisions": collisions}
    elif format == "csv":
        import io
        import csv

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["Frame", "Cueball_X", "Cueball_Y", "Ball_Name", "Ball_X", "Ball_Y"]
        )

        for c in collisions:
            writer.writerow(
                [
                    c["frame_id"],
                    c["cueball"]["x"],
                    c["cueball"]["y"],
                    c["ball"]["name"],
                    c["ball"]["x"],
                    c["ball"]["y"],
                ]
            )

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=collisions_{session_id}.csv"
            },
        )
    else:
        raise HTTPException(
            status_code=400, detail="Invalid format. Use 'json' or 'csv'"
        )


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and its associated files
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Delete video file
    if os.path.exists(session["video_path"]):
        os.remove(session["video_path"])

    # Delete output directory
    output_dir = OUTPUT_DIR / session_id
    if output_dir.exists():
        shutil.rmtree(output_dir)

    # Remove from sessions
    del sessions[session_id]

    return {"message": "Session deleted successfully"}


# ============= WebSocket Endpoint =============


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for real-time updates
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_json({"type": "heartbeat", "status": "ok"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============= Health Check =============


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(sessions),
        "active_connections": len(manager.active_connections),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
