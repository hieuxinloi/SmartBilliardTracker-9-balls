from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Detection:
    name: str
    x: float
    y: float
    r: float
    conf: float

@dataclass
class Track:
    id: int
    name: str
    x: float
    y: float
    r: float
    conf: float
    last_seen: float

@dataclass
class FramePacket:
    frame_id: int
    timestamp: float
    frame: any  # numpy image
    detections: List[Detection] = None
    tracks: List[Track] = None
    analysis: Optional[Dict] = None
    events: Optional[List[Dict]] = None