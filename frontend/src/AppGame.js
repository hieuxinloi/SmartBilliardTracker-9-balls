import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import useWebSocket from "./hooks/useWebSocket";
import GameBoard from "./components/GameBoard";
import PlayerPanel from "./components/PlayerPanel";
import BallBar from "./components/BallBar";
import VictoryModal from "./components/VictoryModal";
import FoulAlert from "./components/FoulAlert";
import "./App.css";

const API_BASE = process.env.REACT_APP_GAME_API_URL || "http://localhost:8001";
const WS_URL =
  process.env.REACT_APP_GAME_WS_URL || "ws://localhost:8001/ws/game";

function App() {
  // Game setup state
  const [gamePhase, setGamePhase] = useState("setup"); // 'setup', 'playing', 'ended'
  const [player1Name, setPlayer1Name] = useState("Player 1");
  const [player2Name, setPlayer2Name] = useState("Player 2");
  const [startingPlayer, setStartingPlayer] = useState(0);
  const [useCamera, setUseCamera] = useState(false);
  const [videoFile, setVideoFile] = useState(null);

  // Game state
  const [gameState, setGameState] = useState(null);
  const [detectionBalls, setDetectionBalls] = useState([]);
  const [currentCollisions, setCurrentCollisions] = useState([]);
  const [frameIdx, setFrameIdx] = useState(0);

  // UI state
  const [showFoul, setShowFoul] = useState(false);
  const [foulData, setFoulData] = useState(null);
  const [showVictory, setShowVictory] = useState(false);
  const [winner, setWinner] = useState(null);
  const [matchDuration, setMatchDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // WebSocket connection
  const { isConnected, gameState: wsGameState, on, off } = useWebSocket(WS_URL);

  // Update game state from WebSocket
  useEffect(() => {
    if (wsGameState) {
      setGameState(wsGameState);
    }
  }, [wsGameState]);

  // Setup WebSocket event handlers
  useEffect(() => {
    // Frame updates
    on("frame_update", (data) => {
      if (data.balls) {
        setDetectionBalls(data.balls);
      }
      if (data.frame_idx) {
        setFrameIdx(data.frame_idx);
      }
      if (data.game_state) {
        setGameState(data.game_state);
      }
    });

    // Collision detection
    on("collision", (data) => {
      console.log("[Collision]", data);
      if (data.cueball && data.ball) {
        setCurrentCollisions([data]);
        // Clear collision after 2 seconds
        setTimeout(() => setCurrentCollisions([]), 2000);
      }
    });

    on("first_hit", (data) => {
      console.log("[First Hit]", data);
      // Show foul if invalid hit
      if (!data.valid) {
        setFoulData({
          reason: data.foul_reason,
          player: data.player,
        });
        setShowFoul(true);
        setTimeout(() => setShowFoul(false), 3000);
      }
    });

    // Foul events
    on("foul", (data) => {
      console.log("[Foul]", data);
      setFoulData({
        reason: data.reason,
        player: data.player,
      });
      setShowFoul(true);
      setTimeout(() => setShowFoul(false), 3000);
    });

    // Turn change
    on("turn_change", (data) => {
      console.log("[Turn Change]", data);
      // Could add turn change animation here
    });

    // Ball missing (tentatively potted - show in UI immediately)
    on("ball_missing", (data) => {
      console.log("[Ball Missing - Tentatively Potted]", data);
      console.log(`Ball ${data.ball} disappeared - showing as potted in status bar`);
      // Game state will be updated automatically via frame_update
    });

    // Ball reappearance (was occluded, not potted)
    on("ball_reappeared", (data) => {
      console.log("[Ball Reappeared]", data);
      console.log(`Ball ${data.ball} was occluded, not actually potted - reverting status`);
      // Game state will be updated automatically via frame_update
    });

    // Cueball scratch
    on("cueball_scratch", (data) => {
      console.log("[Cueball Scratch]", data);
      setFoulData({
        reason: "Cueball scratched (potted)",
        player: data.player,
      });
      setShowFoul(true);
      setTimeout(() => setShowFoul(false), 3000);
    });

    // Game end
    on("game_end", (data) => {
      console.log("[Game End]", data);
      const winningPlayer = gameState?.players.find(
        (p) => p.name === data.winner
      );
      setWinner(winningPlayer);
      setMatchDuration(data.duration || 0);
      setShowVictory(true);
      setGamePhase("ended");
    });

    // Detection start/stop
    on("detection_start", (data) => {
      console.log("[Detection Started]", data);
      setGamePhase("playing");
    });

    on("detection_stop", (data) => {
      console.log("[Detection Stopped]", data);
    });

    // Errors
    on("error", (data) => {
      console.error("[Error]", data);
      setError(data.message);
    });

    return () => {
      off("frame_update");
      off("collision");
      off("first_hit");
      off("foul");
      off("turn_change");
      off("ball_missing");
      off("ball_reappeared");
      off("cueball_scratch");
      off("game_end");
      off("detection_start");
      off("detection_stop");
      off("error");
    };
  }, [on, off, gameState]);

  // Start game
  const handleStartGame = async () => {
    if (!player1Name || !player2Name) {
      setError("Please enter both player names");
      return;
    }

    if (!useCamera && !videoFile) {
      setError("Please select a video file or enable camera");
      return;
    }

    setIsLoading(true);
    setError(null);

    // Reset previous UI state before starting a new game
    setDetectionBalls([]);
    setCurrentCollisions([]);
    setFrameIdx(0);
    setShowFoul(false);
    setFoulData(null);
    setShowVictory(false);
    setWinner(null);
    setGameState(null);

    try {
      let videoPath = null;

      // Upload video if file selected (upload to game API)
      if (videoFile && !useCamera) {
        const formData = new FormData();
        formData.append("file", videoFile);

        const uploadResponse = await axios.post(
          `${API_BASE}/api/game/upload`,
          formData,
          { headers: { "Content-Type": "multipart/form-data" } }
        );

        if (!uploadResponse.data?.video_path) {
          throw new Error("Upload failed: server did not return video_path");
        }
        videoPath = uploadResponse.data.video_path;
      }

      // Start game
      const response = await axios.post(`${API_BASE}/api/game/start`, {
        player1_name: player1Name,
        player2_name: player2Name,
        starting_player: startingPlayer,
        use_camera: useCamera,
        video_path: videoPath,
      });

      console.log("[Game Started]", response.data);
      setGameState(response.data.game_state);
      setGamePhase("playing");
    } catch (err) {
      console.error("[Start Game Error]", err);
      const msg =
        err.response?.data?.detail || err.message || "Failed to start game";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  // Stop game
  const handleStopGame = async () => {
    try {
      await axios.post(`${API_BASE}/api/game/stop`, {
        reason: "user_stop",
      });
    } catch (err) {
      console.error("[Stop Game Error]", err);
    } finally {
      // Always reset UI state even if backend call fails
      setGamePhase("setup");
      setDetectionBalls([]);
      setCurrentCollisions([]);
      setFrameIdx(0);
      setGameState(null);
      setShowFoul(false);
      setFoulData(null);
    }
  };

  // Restart game
  const handleRestartGame = async () => {
    try {
      await axios.post(`${API_BASE}/api/game/restart`);
    } catch (err) {
      console.error("[Restart Game Error]", err);
    } finally {
      // Always reset UI state even if backend call fails
      setGamePhase("setup");
      setShowVictory(false);
      setWinner(null);
      setDetectionBalls([]);
      setCurrentCollisions([]);
      setGameState(null);
      setFrameIdx(0);
      setShowFoul(false);
      setFoulData(null);
      setError(null);
    }
  };

  // Render setup screen
  if (gamePhase === "setup") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
        <div className="max-w-2xl w-full bg-gray-800 rounded-2xl shadow-2xl p-8">
          <h1 className="text-5xl font-bold text-center mb-2 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-600">
            🎱 AI Billiards Referee
          </h1>
          <p className="text-center text-gray-400 mb-8">
            9-Ball Smart Tracking System
          </p>

          {/* Connection status */}
          <div className="mb-6 flex items-center justify-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                isConnected ? "bg-green-500" : "bg-red-500"
              } animate-pulse`}
            ></div>
            <span className="text-gray-300 text-sm">
              {isConnected ? "Connected to server" : "Connecting..."}
            </span>
          </div>

          {error && (
            <div className="mb-6 bg-red-600 bg-opacity-20 border border-red-600 text-red-400 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {/* Player setup */}
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-gray-300 mb-2">Player 1 Name</label>
              <input
                type="text"
                value={player1Name}
                onChange={(e) => setPlayer1Name(e.target.value)}
                className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter player 1 name"
              />
            </div>

            <div>
              <label className="block text-gray-300 mb-2">Player 2 Name</label>
              <input
                type="text"
                value={player2Name}
                onChange={(e) => setPlayer2Name(e.target.value)}
                className="w-full bg-gray-700 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter player 2 name"
              />
            </div>

            <div>
              <label className="block text-gray-300 mb-2">
                Starting Player
              </label>
              <div className="flex gap-4">
                <button
                  onClick={() => setStartingPlayer(0)}
                  className={`flex-1 py-3 rounded-lg font-bold transition-all ${
                    startingPlayer === 0
                      ? "bg-blue-600 text-white ring-2 ring-blue-400"
                      : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }`}
                >
                  {player1Name}
                </button>
                <button
                  onClick={() => setStartingPlayer(1)}
                  className={`flex-1 py-3 rounded-lg font-bold transition-all ${
                    startingPlayer === 1
                      ? "bg-blue-600 text-white ring-2 ring-blue-400"
                      : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }`}
                >
                  {player2Name}
                </button>
              </div>
            </div>
          </div>

          {/* Video source selection */}
          <div className="mb-6">
            <label className="block text-gray-300 mb-2">Video Source</label>
            <div className="flex gap-4 mb-4">
              <button
                onClick={() => setUseCamera(false)}
                className={`flex-1 py-3 rounded-lg font-bold transition-all ${
                  !useCamera
                    ? "bg-purple-600 text-white ring-2 ring-purple-400"
                    : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                }`}
              >
                📹 Upload Video
              </button>
              <button
                onClick={() => setUseCamera(true)}
                className={`flex-1 py-3 rounded-lg font-bold transition-all ${
                  useCamera
                    ? "bg-purple-600 text-white ring-2 ring-purple-400"
                    : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                }`}
              >
                📷 Use Camera
              </button>
            </div>

            {!useCamera && (
              <div>
                <input
                  type="file"
                  accept="video/*"
                  onChange={(e) => setVideoFile(e.target.files[0])}
                  className="hidden"
                  id="video-upload"
                />
                <label
                  htmlFor="video-upload"
                  className="block w-full bg-gray-700 hover:bg-gray-600 text-white text-center px-4 py-8 rounded-lg cursor-pointer transition-colors border-2 border-dashed border-gray-600"
                >
                  {videoFile ? (
                    <div>
                      <div className="text-green-400 text-4xl mb-2">✓</div>
                      <div className="font-bold">{videoFile.name}</div>
                      <div className="text-sm text-gray-400 mt-1">
                        {(videoFile.size / 1024 / 1024).toFixed(2)} MB
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="text-4xl mb-2">📁</div>
                      <div>Click to select video file</div>
                      <div className="text-sm text-gray-400 mt-1">
                        MP4, AVI, MOV, MKV
                      </div>
                    </div>
                  )}
                </label>
              </div>
            )}
          </div>

          {/* Start button */}
          <button
            onClick={handleStartGame}
            disabled={isLoading || !isConnected}
            className="w-full bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 disabled:from-gray-600 disabled:to-gray-700 text-white font-bold py-4 px-6 rounded-lg transition-all transform hover:scale-105 disabled:scale-100 shadow-lg text-xl"
          >
            {isLoading ? "🔄 Starting Game..." : "🎮 Start Game"}
          </button>
        </div>
      </div>
    );
  }

  // Render game screen
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 p-4">
      {/* Header */}
      <div className="max-w-screen-2xl mx-auto mb-4 px-2 sm:px-4">
        <div className="flex items-center justify-between bg-gray-800 rounded-lg p-4 shadow-lg">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span>🎱</span>
            <span>AI Billiards Referee</span>
          </h1>

          <div className="flex items-center gap-4">
            <div
              className={`px-3 py-1 rounded-full text-sm font-bold ${
                isConnected ? "bg-green-600" : "bg-red-600"
              }`}
            >
              {isConnected ? "● Live" : "● Disconnected"}
            </div>

            <button
              onClick={handleStopGame}
              className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
            >
              ⏹ Stop Game
            </button>
          </div>
        </div>
      </div>

      {/* Main game layout */}
      <div className="max-w-screen-2xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-4 px-2 sm:px-4">
        {/* Left column - Player 1 */}
        <div className="lg:col-span-3">
          {gameState?.players[0] && (
            <PlayerPanel
              player={gameState.players[0]}
              isCurrentTurn={gameState.players[0].is_current}
              lowestBall={gameState.lowest_ball}
            />
          )}
        </div>

        {/* Center column - Game board and ball bar */}
        <div className="lg:col-span-6 space-y-4">
          <GameBoard
            videoSource={
              useCamera
                ? null
                : videoFile
                ? URL.createObjectURL(videoFile)
                : null
            }
            streamUrl={`${API_BASE}/api/game/stream`}
            balls={detectionBalls}
            collisions={currentCollisions}
            frameIdx={frameIdx}
            isLive={gamePhase === "playing"}
            useCamera={useCamera}
          />

          {gameState && (
            <BallBar
              ballsOnTable={gameState.balls_on_table || []}
              lowestBall={gameState.lowest_ball || 1}
            />
          )}
        </div>

        {/* Right column - Player 2 */}
        <div className="lg:col-span-3">
          {gameState?.players[1] && (
            <PlayerPanel
              player={gameState.players[1]}
              isCurrentTurn={gameState.players[1].is_current}
              lowestBall={gameState.lowest_ball}
            />
          )}
        </div>
      </div>

      {/* Foul alert overlay */}
      {showFoul && foulData && (
        <FoulAlert
          foulReason={foulData.reason}
          playerName={foulData.player}
          onDismiss={() => setShowFoul(false)}
        />
      )}

      {/* Victory modal */}
      {showVictory && winner && gameState && (
        <VictoryModal
          winner={winner}
          players={gameState.players}
          matchDuration={matchDuration}
          onRestart={handleRestartGame}
          onClose={() => setShowVictory(false)}
        />
      )}
    </div>
  );
}
export default App;
