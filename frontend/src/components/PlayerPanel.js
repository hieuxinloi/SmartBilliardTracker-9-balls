import React from "react";

/**
 * PlayerPanel Component
 * Displays player information, current turn, fouls, and potted balls
 */
const PlayerPanel = ({ player, isCurrentTurn, lowestBall }) => {
  const ballColors = {
    1: "#FFD700", // Yellow
    2: "#0000FF", // Blue
    3: "#FF0000", // Red
    4: "#800080", // Purple
    5: "#FFA500", // Orange
    6: "#008000", // Green
    7: "#8B0000", // Maroon
    8: "#000000", // Black
    9: "#FFD700", // Yellow/Gold
  };

  return (
    <div
      className={`
        p-6 rounded-lg shadow-lg transition-all duration-300
        ${
          isCurrentTurn
            ? "bg-gradient-to-br from-blue-500 to-blue-600 ring-4 ring-yellow-400 scale-105"
            : "bg-gradient-to-br from-gray-700 to-gray-800 opacity-75"
        }
      `}
    >
      {/* Player Name */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          {player.name}
          {isCurrentTurn && (
            <span className="animate-pulse text-yellow-300">🎱</span>
          )}
        </h2>
        {isCurrentTurn && (
          <span className="bg-yellow-400 text-gray-900 px-3 py-1 rounded-full text-sm font-bold">
            TURN
          </span>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-white bg-opacity-10 p-3 rounded">
          <div className="text-gray-300 text-sm">Potted</div>
          <div className="text-2xl font-bold text-white">
            {player.potted_balls.length}
          </div>
        </div>
        <div className="bg-white bg-opacity-10 p-3 rounded">
          <div className="text-gray-300 text-sm">Fouls</div>
          <div className="text-2xl font-bold text-red-400">
            {player.foul_count}
          </div>
        </div>
      </div>

      {/* Potted Balls Bar */}
      <div className="bg-white bg-opacity-10 p-4 rounded-lg">
        <div className="text-gray-300 text-sm mb-2">Potted Balls</div>
        <div className="flex flex-wrap gap-2">
          {player.potted_balls.length === 0 ? (
            <span className="text-gray-400 text-sm italic">None yet</span>
          ) : (
            player.potted_balls.map((ball) => (
              <div
                key={ball}
                className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-white shadow-lg"
                style={{
                  backgroundColor: ballColors[ball] || "#666",
                  border: ball === 9 ? "3px solid gold" : "2px solid white",
                }}
              >
                {ball}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Next Target */}
      {isCurrentTurn && (
        <div className="mt-4 bg-yellow-400 bg-opacity-20 p-3 rounded-lg border-2 border-yellow-400">
          <div className="text-yellow-300 text-sm font-semibold">
            Target Ball
          </div>
          <div className="text-3xl font-bold text-white">{lowestBall}</div>
        </div>
      )}
    </div>
  );
};

export default PlayerPanel;
