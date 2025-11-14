"""
Game Manager for 9-Ball Billiards AI Referee System
Tracks game state, player turns, fouls, and potted balls
"""

import asyncio
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import copy


class GameState(Enum):
    """Game states"""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    ENDED = "ended"


class BallState(Enum):
    """Ball tracking states"""

    ON_TABLE = "on_table"
    MISSING = "missing"  # Temporarily not detected (may be occluded)
    POTTED = "potted"  # Confirmed potted after threshold


class BallTracker:
    """
    Tracks individual ball state with confirmation threshold
    Prevents false positives from occlusion or detection failures
    """

    MISSING_THRESHOLD = 10  # Frames before confirming potted
    OCCLUSION_THRESHOLD = 3  # Short absence likely means occluded

    def __init__(self):
        # ball_num -> {state, missing_frames, last_seen_frame, last_position}
        self.ball_states: Dict[int, Dict] = {}
        self.current_frame = 0

        # Initialize all balls as on table
        for ball_num in range(1, 10):  # Balls 1-9
            self.ball_states[ball_num] = {
                "state": BallState.ON_TABLE,
                "missing_frames": 0,
                "last_seen_frame": 0,
                "last_position": None,
            }

    def update(self, frame_idx: int, detected_balls: List[int]) -> Dict:
        """
        Update ball states based on current detections

        NEW BEHAVIOR: Balls show as potted immediately when they disappear (MISSING state),
        but can be reverted if they reappear within threshold frames.

        Args:
            frame_idx: Current frame number
            detected_balls: List of ball numbers detected in this frame

        Returns:
            Dict with newly_missing (tentatively potted), newly_potted (confirmed), and reappeared
        """
        self.current_frame = frame_idx
        detected_set = set(detected_balls)
        newly_missing = []  # Just disappeared (show as potted in UI)
        newly_potted = []  # Confirmed potted after threshold
        reappeared = []  # Reappeared (was occluded)

        for ball_num in range(1, 10):
            state_info = self.ball_states[ball_num]
            current_state = state_info["state"]

            if ball_num in detected_set:
                # Ball is visible
                state_info["last_seen_frame"] = frame_idx

                if current_state in [BallState.MISSING, BallState.POTTED]:
                    # Ball reappeared after being marked as missing/potted
                    reappear_frames = state_info["missing_frames"]
                    print(
                        f"[BallTracker] Ball {ball_num} REAPPEARED after {reappear_frames} frames (was occluded, not potted)"
                    )
                    state_info["state"] = BallState.ON_TABLE
                    state_info["missing_frames"] = 0
                    reappeared.append(ball_num)
                else:
                    # Normal - ball stays on table
                    state_info["missing_frames"] = 0

            else:
                # Ball not detected
                if current_state == BallState.ON_TABLE:
                    # Only mark as MISSING if ball was actually seen before
                    # This prevents false positives when ball 1 is never detected from start
                    if state_info["last_seen_frame"] > 0:
                        # Ball just went missing - show as potted immediately in UI
                        state_info["state"] = BallState.MISSING
                        state_info["missing_frames"] = 1
                        print(
                            f"[BallTracker] Ball {ball_num} went MISSING (tentatively potted in UI)"
                        )
                        newly_missing.append(ball_num)
                    else:
                        # Ball never seen - likely not in the video yet, don't mark as missing
                        # Just silently track that it hasn't been seen
                        pass

                elif current_state == BallState.MISSING:
                    # Still missing, increment counter
                    state_info["missing_frames"] += 1

                    # Check if threshold reached for permanent confirmation
                    if state_info["missing_frames"] >= self.MISSING_THRESHOLD:
                        print(
                            f"[BallTracker] Ball {ball_num} CONFIRMED POTTED (missing {state_info['missing_frames']} frames)"
                        )
                        state_info["state"] = BallState.POTTED
                        newly_potted.append(ball_num)

                # If already POTTED, stays POTTED

        return {
            "newly_missing": newly_missing,  # Show as potted in UI immediately
            "newly_potted": newly_potted,  # Confirmed potted (process game logic)
            "reappeared": reappeared,  # Revert potted status in UI
        }

    def get_ball_state(self, ball_num: int) -> BallState:
        """Get current state of a ball"""
        return self.ball_states[ball_num]["state"]

    def is_potted(self, ball_num: int) -> bool:
        """Check if ball is confirmed potted"""
        return self.ball_states[ball_num]["state"] == BallState.POTTED

    def is_on_table(self, ball_num: int) -> bool:
        """Check if ball is on table (only ON_TABLE state, not MISSING)"""
        return self.ball_states[ball_num]["state"] == BallState.ON_TABLE

    def should_show_as_potted(self, ball_num: int) -> bool:
        """Check if ball should be displayed as potted in status bar (MISSING or POTTED)"""
        state = self.ball_states[ball_num]["state"]
        return state in [BallState.MISSING, BallState.POTTED]

    def get_missing_frames(self, ball_num: int) -> int:
        """Get number of frames ball has been missing"""
        return self.ball_states[ball_num]["missing_frames"]

    def reset(self):
        """Reset all balls to on table"""
        for ball_num in range(1, 10):
            self.ball_states[ball_num] = {
                "state": BallState.ON_TABLE,
                "missing_frames": 0,
                "last_seen_frame": 0,
                "last_position": None,
            }


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
        # State locking for thread safety
        self.state_lock = asyncio.Lock()

        # State snapshots for turn reversion
        self.state_snapshots: List[Dict] = []  # Keep last 5 snapshots
        self.max_snapshots: int = 5
        self.current_snapshot: Optional[Dict] = None

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
        # Whether cue ball has made first legal/illegal contact this turn
        self.first_contact: bool = False

        # Ball tracking with confirmation (prevents occlusion false positives)
        self.ball_tracker = BallTracker()

        # Movement detection improvements
        self.movement_history: List[Dict] = []  # Buffer of last 10 frames
        self.max_movement_history: int = 10
        self.movement_threshold: float = 2.0  # pixels
        self.stable_frames_required: int = 5
        self.debounce_counter: int = 0

        # Cueball scratch tracking
        self.cueball_missing_frames: int = 0
        self.cueball_scratched: bool = False

        # Break shot grace period (10 seconds to avoid false fouls)
        self.break_grace_period: float = 10.0  # seconds
        self.game_start_timestamp: Optional[datetime] = None

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
        self.game_start_timestamp = datetime.now()  # Track for break grace period

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
        self.first_contact = False
        self.ball_tracker.reset()
        self.cueball_missing_frames = 0
        self.cueball_scratched = False

        self._add_event(
            "game_start",
            {
                "player1": player1_name,
                "player2": player2_name,
                "starting_player": starting_player,
            },
        )

        return self.get_game_state()

    def is_in_break_grace_period(self) -> bool:
        """
        Check if we're within the break shot grace period (first 10 seconds)
        During this time, hit-first-ball rule is not enforced
        
        Returns:
            True if within grace period, False otherwise
        """
        if not self.game_start_timestamp:
            return False
        
        elapsed = (datetime.now() - self.game_start_timestamp).total_seconds()
        return elapsed < self.break_grace_period

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
            self.first_contact = True

            # Check if we're in break grace period (first 10 seconds)
            in_grace_period = self.is_in_break_grace_period()
            
            # Check if hit the lowest ball first (skip validation during grace period)
            if in_grace_period:
                is_valid_hit = True  # Always valid during break shot
                print(f"[GameManager] Break grace period active - hit validation skipped")
            else:
                is_valid_hit = ball_num == self.lowest_ball

            event = {
                "event": "first_hit",
                "ball": ball_num,
                "ball_name": ball_name,
                "valid": is_valid_hit,
                "lowest_ball": self.lowest_ball,
                "player": self.players[self.current_player_idx].name,
                "message": f"{self.players[self.current_player_idx].name} hit ball {ball_num}",
                "in_grace_period": in_grace_period,
            }

            if not is_valid_hit:
                event["foul_reason"] = f"Must hit ball {self.lowest_ball} first"

            self._add_event("collision", event)
            return event

        return {"event": "subsequent_hit", "ball": ball_num, "ball_name": ball_name}

    def update_ball_tracking(
        self, frame_idx: int, detected_balls: List[int], cueball_detected: bool = True
    ) -> List[Dict]:
        """
        Update ball tracker with current detections

        Args:
            frame_idx: Current frame number
            detected_balls: List of ball numbers (1-9) detected in frame
            cueball_detected: Whether cueball is detected in frame

        Returns:
            List of events (potted, reappeared, scratch)
        """
        events = []
        result = self.ball_tracker.update(frame_idx, detected_balls)

        # Handle newly missing balls (show as tentatively potted in UI)
        for ball_num in result["newly_missing"]:
            event = {
                "event": "ball_missing",
                "ball": ball_num,
                "ball_name": f"bi{ball_num}",
                "tentative": True,
                "message": f"Ball {ball_num} disappeared (tentatively potted)",
            }
            events.append(event)

        # Handle newly confirmed potted balls (process game logic)
        for ball_num in result["newly_potted"]:
            event = self.process_potted_ball(f"bi{ball_num}")
            if event.get("event") == "potted":
                events.append(event)

        # Handle reappeared balls (were occluded, not actually potted)
        for ball_num in result["reappeared"]:
            event = self.process_ball_reappearance(ball_num)
            events.append(event)

        # Check cueball scratch
        scratch_event = self.check_cueball_scratch(cueball_detected)
        if scratch_event:
            events.append(scratch_event)

        return events

    def check_cueball_scratch(self, cueball_detected: bool) -> Optional[Dict]:
        """
        Check if cueball has been scratched (potted)

        Args:
            cueball_detected: Whether cueball is visible in current frame

        Returns:
            Scratch event dict if cueball scratched, None otherwise
        """
        if cueball_detected:
            self.cueball_missing_frames = 0
            self.cueball_scratched = False
            return None

        # Cueball not detected
        self.cueball_missing_frames += 1

        # Check threshold
        if self.cueball_missing_frames >= 10 and not self.cueball_scratched:
            self.cueball_scratched = True
            print(
                f"[GameManager] CUEBALL SCRATCHED (missing {self.cueball_missing_frames} frames)"
            )

            event = {
                "event": "cueball_scratch",
                "player": self.players[self.current_player_idx].name,
                "message": f"Cueball scratched by {self.players[self.current_player_idx].name}",
                "foul_reason": "Cueball scratched (potted)",
            }

            # Process as foul
            foul_event = self.process_foul("Cueball scratched")
            event.update(foul_event)

            return event

        return None

    def process_ball_reappearance(self, ball_num: int) -> Dict:
        """
        Handle ball reappearing after being marked as potted
        This means it was occluded, not actually potted

        Args:
            ball_num: Ball number that reappeared

        Returns:
            Event dict
        """
        # Add ball back to table
        self.balls_on_table.add(ball_num)

        # Remove from players' potted lists
        for player in self.players:
            if ball_num in player.potted_balls:
                player.potted_balls.remove(ball_num)
                print(
                    f"[GameManager] Removed ball {ball_num} from {player.name}'s potted balls (reappeared)"
                )

        # Remove from last_potted_balls if present
        if ball_num in self.last_potted_balls:
            self.last_potted_balls.remove(ball_num)

        # Update lowest ball
        self._update_lowest_ball()

        event = {
            "event": "ball_reappeared",
            "ball": ball_num,
            "ball_name": f"bi{ball_num}",
            "message": f"Ball {ball_num} reappeared (was occluded, not potted)",
            "balls_on_table": sorted(list(self.balls_on_table)),
            "lowest_ball": self.lowest_ball,
        }

        self._add_event("ball_reappeared", event)
        return event

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

        # Handle pre-contact disappearances: treat as pre-potted (no score, no foul)
        if not self.first_contact:
            # Remove from table and update lowest, but do not score or foul
            self.balls_on_table.remove(ball_num)
            self._update_lowest_ball()
            event = {
                "event": "potted",
                "pre_contact": True,
                "counted": False,
                "valid": False,
                "ball": ball_num,
                "ball_name": ball_name,
                "player": self.players[self.current_player_idx].name,
                "message": f"{self.players[self.current_player_idx].name} pre-potted ball {ball_num} (no score)",
            }
            # Track for this turn but not scoring
            self.last_potted_balls.append(ball_num)
            self._add_event("potted", event)
            return event

        # 9-ball rule post-contact: Any ball can be potted IF you hit the lowest ball first
        # Valid if player hit the lowest ball first on initial contact
        is_valid = self.last_hit_ball == self.lowest_ball

        # Add to potted balls for this turn
        self.last_potted_balls.append(ball_num)

        # Always remove from table when potted (can be restored on foul)
        self.balls_on_table.remove(ball_num)

        event = {
            "event": "potted",
            "ball": ball_num,
            "ball_name": ball_name,
            "valid": is_valid,
            "player": self.players[self.current_player_idx].name,
            "message": f"{self.players[self.current_player_idx].name} potted ball {ball_num}",
        }

        if is_valid:
            # Add to player's score (any legally potted ball counts)
            self.players[self.current_player_idx].potted_balls.append(ball_num)

            # Check for game end (9-ball potted legally = WIN)
            if ball_num == 9:
                # 9-ball WIN condition: must be last ball OR player hit 9 first
                is_nine_win = (len(self.balls_on_table) == 0) or (
                    self.last_hit_ball == 9
                )

                if is_nine_win:
                    # Legal 9-ball win
                    self._end_game(self.current_player_idx)
                    event["game_end"] = True
                    event["winner"] = self.players[self.current_player_idx].name
                    event["message"] = (
                        f"🏆 {self.players[self.current_player_idx].name} wins by sinking the 9-ball!"
                    )
                else:
                    # 9-ball potted early by combination - return to table as foul
                    print(
                        f"[GameManager] 9-ball potted early by combination (hit {self.last_hit_ball} first)"
                    )
                    self.balls_on_table.add(9)  # Return 9-ball to table
                    self.players[self.current_player_idx].potted_balls.remove(9)
                    event["valid"] = False
                    event["early_nine"] = True
                    event["foul_reason"] = (
                        f"9-ball potted by combination (hit ball {self.last_hit_ball} first)"
                    )
                    event["message"] = (
                        f"9-ball returned to table - potted by combination"
                    )
                    self._update_lowest_ball()
            else:
                # Update lowest ball on table
                self._update_lowest_ball()
        else:
            # Set foul reason based on what went wrong
            event["foul_reason"] = (
                f"Did not hit ball {self.lowest_ball} first (hit ball {self.last_hit_ball})"
            )

        self._add_event("potted", event)
        return event

    def process_foul(self, reason: str) -> Dict:
        """
        Process a foul - reverts game state to snapshot before turn

        Args:
            reason: Description of the foul

        Returns:
            Event dict with foul info
        """
        current_player = self.players[self.current_player_idx]
        reverted_balls = self.last_potted_balls.copy()

        # Increment foul count before reversion
        current_player.foul_count += 1

        # Revert to snapshot if available (more reliable than manual reversion)
        if self.current_snapshot:
            # Save foul count and revert
            foul_count = current_player.foul_count
            self.revert_to_snapshot()
            # Restore foul count after reversion
            self.players[self.current_player_idx].foul_count = foul_count
        else:
            # Fallback to manual reversion if no snapshot
            for ball in self.last_potted_balls:
                self.balls_on_table.add(ball)
                if ball in current_player.potted_balls:
                    current_player.potted_balls.remove(ball)

        event = {
            "event": "foul",
            "player": current_player.name,
            "reason": reason,
            "reverted_balls": reverted_balls,
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
        """Reset state for new turn and create snapshot"""
        self.last_hit_ball = None
        self.last_potted_balls = []
        self.last_movement_time = None
        self.balls_moving = False
        self.first_contact = False

        # Create snapshot at start of new turn for potential reversion
        self.create_turn_snapshot()

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

    def create_turn_snapshot(self) -> Dict:
        """
        Create a complete snapshot of current game state before turn starts

        Returns:
            Snapshot dictionary with all game state
        """
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "turn_number": len(self.state_snapshots) + 1,
            "balls_on_table": self.balls_on_table.copy(),
            "lowest_ball": self.lowest_ball,
            "current_player_idx": self.current_player_idx,
            "last_hit_ball": self.last_hit_ball,
            "last_potted_balls": self.last_potted_balls.copy(),
            "first_contact": self.first_contact,
            "player1_potted": (
                self.players[0].potted_balls.copy() if self.players else []
            ),
            "player2_potted": (
                self.players[1].potted_balls.copy() if len(self.players) > 1 else []
            ),
            "player1_fouls": self.players[0].foul_count if self.players else 0,
            "player2_fouls": self.players[1].foul_count if len(self.players) > 1 else 0,
        }

        # Add to snapshots list
        self.state_snapshots.append(snapshot)

        # Keep only last N snapshots
        if len(self.state_snapshots) > self.max_snapshots:
            self.state_snapshots.pop(0)

        self.current_snapshot = copy.deepcopy(snapshot)
        return snapshot

    def revert_to_snapshot(self, snapshot: Optional[Dict] = None):
        """
        Restore game state from a snapshot

        Args:
            snapshot: Specific snapshot to restore, or None to use current_snapshot
        """
        if snapshot is None:
            snapshot = self.current_snapshot

        if not snapshot:
            print("[GameManager] No snapshot available for reversion")
            return

        # Restore state
        self.balls_on_table = snapshot["balls_on_table"].copy()
        self.lowest_ball = snapshot["lowest_ball"]
        self.current_player_idx = snapshot["current_player_idx"]
        self.last_hit_ball = snapshot["last_hit_ball"]
        self.last_potted_balls = snapshot["last_potted_balls"].copy()
        self.first_contact = snapshot["first_contact"]

        # Restore player states
        if self.players:
            self.players[0].potted_balls = snapshot["player1_potted"].copy()
            self.players[0].foul_count = snapshot["player1_fouls"]
            if len(self.players) > 1:
                self.players[1].potted_balls = snapshot["player2_potted"].copy()
                self.players[1].foul_count = snapshot["player2_fouls"]

        print(
            f"[GameManager] Reverted to snapshot from turn {snapshot.get('turn_number', 'unknown')}"
        )

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
            "first_contact": self.first_contact,
            "in_grace_period": self.is_in_break_grace_period(),
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
        self.first_contact = False
        self.state_snapshots = []
        self.current_snapshot = None
        self.movement_history = []
        self.debounce_counter = 0
        self.ball_tracker.reset()
        self.cueball_missing_frames = 0
        self.cueball_scratched = False
        self.game_start_timestamp = None
