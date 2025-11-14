"""
Custom Error Types for Smart Billiards AI Referee System
Provides specific error classes for better error handling and debugging
"""


class GameError(Exception):
    """Base exception for all game-related errors"""

    def __init__(self, message: str, context: dict = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)

    def to_dict(self):
        """Convert error to dictionary for JSON serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
        }


class DetectionError(GameError):
    """Error during ball detection with YOLO model"""

    pass


class CollisionError(GameError):
    """Error during collision detection"""

    pass


class StateError(GameError):
    """Error with game state management"""

    pass


class ValidationError(GameError):
    """Error validating game rules or input"""

    pass


class ConnectionError(GameError):
    """Error with WebSocket or network connection"""

    pass


class VideoProcessingError(GameError):
    """Error processing video frames"""

    pass


class PocketDetectionError(GameError):
    """Error detecting potted balls"""

    pass


class DatabaseError(GameError):
    """Error with database operations"""

    pass


class ConfigurationError(GameError):
    """Error with configuration or settings"""

    pass
