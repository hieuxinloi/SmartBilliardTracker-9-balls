"""
Game Manager for 9-Ball Billiards AI Referee System
Tracks game state, player turns, fouls, and potted balls
"""

import asyncio
from typing import List, Dict, Optional, Set
from datetime import datetime
from enum import Enum
import json
from pathlib import Path


class GameState(Enum):
    """Game states"""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    ENDED = "ended"


class Player:
    """Player information"""

    def __init__(self, name: str, player_id: int):
        self.name = name
        self.id = player_id
        self.potted_balls: List[int] = []
        self.foul_count: int = 0
        self.is_current: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "potted_balls": self.potted_balls,
            "foul_count": self.foul_count,
            "is_current": self.is_current,
        }


class GameManager:
    """
    Manages the 9-ball billiards game logic

    Game Rules:
    - Two players alternate turns
    - Must hit the lowest numbered ball first
    - Fouls result in turn change and ball reversion
    - Game ends when 9-ball is legally potted
    - If no ball is potted after movement stops, turn changes
    """

    def __init__(self):
        self.state = GameState.IDLE
        self.players: List[Player] = []
        self.current_player_idx: int = 0
        self.balls_on_table: Set[int] = set(range(1, 10))  # Balls 1-9
        self.lowest_ball: int = 1
        self.last_hit_ball: Optional[int] = None
        self.last_potted_balls: List[int] = []
        self.match_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.events: List[Dict] = []
        self.movement_timeout: float = 3.0  # seconds without movement = turn change
        self.last_movement_time: Optional[datetime] = None
        self.balls_moving: bool = False

    def start_game(
        self, player1_name: str, player2_name: str, starting_player: int = 0
    ):
        """
        Initialize a new game

        Args:
            player1_name: Name of player 1
            player2_name: Name of player 2
            starting_player: Index of starting player (0 or 1)
        """
        self.state = GameState.PLAYING
        self.match_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now()

        # Initialize players
        self.players = [Player(player1_name, 0), Player(player2_name, 1)]
        self.current_player_idx = starting_player
        self.players[self.current_player_idx].is_current = True

        # Reset game state
        self.balls_on_table = set(range(1, 10))
        self.lowest_ball = 1
        self.last_hit_ball = None
        self.last_potted_balls = []
        self.events = []

        self._add_event(
            "game_start",
            {
                "player1": player1_name,
                "player2": player2_name,
                "starting_player": starting_player,
            },
        )

        return self.get_game_state()

    def process_collision(self, ball_name: str) -> Dict:
        """
        Process a collision between cueball and another ball

        Args:
            ball_name: Name of the ball hit (e.g., "bi1", "bi2", etc.)

        Returns:
            Event dict with collision info
        """
        # Extract ball number from name (bi1 -> 1, bi9 -> 9)
        try:
            ball_num = int(ball_name.replace("bi", ""))
        except (ValueError, AttributeError):
            return {"event": "invalid_collision", "ball": ball_name}

        # Check if this is the first hit in the turn
        if self.last_hit_ball is None:
            self.last_hit_ball = ball_num

            # Check if hit the lowest ball first
            is_valid_hit = ball_num == self.lowest_ball

            event = {
                "event": "first_hit",
                "ball": ball_num,
                "ball_name": ball_name,
                "valid": is_valid_hit,
                "lowest_ball": self.lowest_ball,
                "player": self.players[self.current_player_idx].name,
                "message": f"{self.players[self.current_player_idx].name} hit ball {ball_num}",
            }

            if not is_valid_hit:
                event["foul_reason"] = f"Must hit ball {self.lowest_ball} first"

            self._add_event("collision", event)
            return event

        return {"event": "subsequent_hit", "ball": ball_num, "ball_name": ball_name}

    def process_potted_ball(self, ball_name: str) -> Dict:
        """
        Process a ball being potted

        Args:
            ball_name: Name of the potted ball

        Returns:
            Event dict with potted ball info
        """
        try:
            ball_num = int(ball_name.replace("bi", ""))
        except (ValueError, AttributeError):
            return {"event": "invalid_pot", "ball": ball_name}

        if ball_num not in self.balls_on_table:
            return {"event": "already_potted", "ball": ball_num}

        # Check if this is a valid pot
        is_valid = self.last_hit_ball == self.lowest_ball

        # Add to potted balls for this turn
        self.last_potted_balls.append(ball_num)

        event = {
            "event": "potted",
            "ball": ball_num,
            "ball_name": ball_name,
            "valid": is_valid,
            "player": self.players[self.current_player_idx].name,
            "message": f"{self.players[self.current_player_idx].name} potted ball {ball_num}",
        }

        if is_valid:
            # Remove from table and add to player's score
            self.balls_on_table.remove(ball_num)
            self.players[self.current_player_idx].potted_balls.append(ball_num)

            # Check for game end (9-ball potted legally)
            if ball_num == 9:
                self._end_game(self.current_player_idx)
                event["game_end"] = True
                event["winner"] = self.players[self.current_player_idx].name
            else:
                # Update lowest ball
                self._update_lowest_ball()
        else:
            event["foul_reason"] = f"Did not hit ball {self.lowest_ball} first"

        self._add_event("potted", event)
        return event

    def process_foul(self, reason: str) -> Dict:
        """
        Process a foul

        Args:
            reason: Description of the foul

        Returns:
            Event dict with foul info
        """
        current_player = self.players[self.current_player_idx]
        current_player.foul_count += 1

        # Revert potted balls from this turn
        for ball in self.last_potted_balls:
            self.balls_on_table.add(ball)
            if ball in current_player.potted_balls:
                current_player.potted_balls.remove(ball)

        event = {
            "event": "foul",
            "player": current_player.name,
            "reason": reason,
            "reverted_balls": self.last_potted_balls.copy(),
            "message": f"Foul by {current_player.name}: {reason}",
        }

        self._add_event("foul", event)

        # Switch turn after foul
        self._switch_turn()

        return event

    def check_movement_timeout(self) -> Optional[Dict]:
        """
        Check if movement has stopped for too long and switch turn

        Returns:
            Turn change event if timeout occurred, None otherwise
        """
        if not self.balls_moving and self.last_movement_time:
            time_since_movement = (
                datetime.now() - self.last_movement_time
            ).total_seconds()

            if time_since_movement > self.movement_timeout:
                # No ball potted, switch turn
                if not self.last_potted_balls:
                    return self._switch_turn()
                else:
                    # Balls were potted, finalize turn
                    return self.finalize_turn()

        return None

    def update_movement(self, is_moving: bool):
        """Update ball movement status"""
        self.balls_moving = is_moving
        if is_moving:
            self.last_movement_time = datetime.now()

    def finalize_turn(self) -> Dict:
        """
        Finalize the current turn and switch to next player if needed

        Returns:
            Event dict with turn finalization info
        """
        current_player = self.players[self.current_player_idx]

        # Check if valid hit was made
        if self.last_hit_ball != self.lowest_ball:
            return self.process_foul(f"Did not hit ball {self.lowest_ball} first")

        # If balls were potted legally, player continues
        if self.last_potted_balls and all(
            ball in current_player.potted_balls for ball in self.last_potted_balls
        ):
            event = {
                "event": "turn_continue",
                "player": current_player.name,
                "potted": self.last_potted_balls,
                "message": f"{current_player.name} continues",
            }
            self._reset_turn_state()
            return event

        # Otherwise, switch turn
        return self._switch_turn()

    def _switch_turn(self) -> Dict:
        """Switch to the other player"""
        self.players[self.current_player_idx].is_current = False
        self.current_player_idx = 1 - self.current_player_idx
        self.players[self.current_player_idx].is_current = True

        self._reset_turn_state()

        event = {
            "event": "turn_change",
            "player": self.players[self.current_player_idx].name,
            "message": f"Turn: {self.players[self.current_player_idx].name}",
        }

        self._add_event("turn_change", event)
        return event

    def _reset_turn_state(self):
        """Reset state for new turn"""
        self.last_hit_ball = None
        self.last_potted_balls = []
        self.last_movement_time = None
        self.balls_moving = False

    def _update_lowest_ball(self):
        """Update the lowest ball on table"""
        if self.balls_on_table:
            self.lowest_ball = min(self.balls_on_table)

    def _end_game(self, winner_idx: int):
        """End the game with a winner"""
        self.state = GameState.ENDED
        winner = self.players[winner_idx]

        event = {
            "event": "game_end",
            "winner": winner.name,
            "winner_id": winner.id,
            "player1_score": len(self.players[0].potted_balls),
            "player2_score": len(self.players[1].potted_balls),
            "player1_fouls": self.players[0].foul_count,
            "player2_fouls": self.players[1].foul_count,
            "duration": (
                (datetime.now() - self.start_time).total_seconds()
                if self.start_time
                else 0
            ),
            "message": f"🏆 {winner.name} wins!",
        }

        self._add_event("game_end", event)
        self._save_match_history(event)

    def _add_event(self, event_type: str, data: Dict):
        """Add an event to the history"""
        event = {"timestamp": datetime.now().isoformat(), "type": event_type, **data}
        self.events.append(event)

    def _save_match_history(self, result: Dict):
        """Save match history to file"""
        history_dir = Path("backend/data")
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / "matches.json"

        match_data = {
            "match_id": self.match_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": datetime.now().isoformat(),
            "players": [p.to_dict() for p in self.players],
            "result": result,
            "events": self.events,
        }

        # Load existing history
        history = []
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
            except:
                pass

        # Append new match
        history.append(match_data)

        # Save
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)

    def get_game_state(self) -> Dict:
        """Get current game state"""
        return {
            "state": self.state.value,
            "match_id": self.match_id,
            "players": [p.to_dict() for p in self.players],
            "current_player": (
                self.players[self.current_player_idx].name if self.players else None
            ),
            "balls_on_table": sorted(list(self.balls_on_table)),
            "lowest_ball": self.lowest_ball,
            "last_hit_ball": self.last_hit_ball,
            "balls_moving": self.balls_moving,
        }

    def reset_game(self):
        """Reset to initial state"""
        self.state = GameState.IDLE
        self.players = []
        self.current_player_idx = 0
        self.balls_on_table = set(range(1, 10))
        self.lowest_ball = 1
        self.last_hit_ball = None
        self.last_potted_balls = []
        self.match_id = None
        self.start_time = None
        self.events = []
        self.last_movement_time = None
        self.balls_moving = False
