import React from "react";

/**
 * BallBar Component
 * Visual display of all balls still on the table
 */
const BallBar = ({ ballsOnTable, lowestBall }) => {
  const allBalls = [1, 2, 3, 4, 5, 6, 7, 8, 9];

  const ballColors = {
    1: { bg: "#FFD700", text: "#000" }, // Yellow
    2: { bg: "#0000FF", text: "#FFF" }, // Blue
    3: { bg: "#FF0000", text: "#FFF" }, // Red
    4: { bg: "#800080", text: "#FFF" }, // Purple
    5: { bg: "#FFA500", text: "#000" }, // Orange
    6: { bg: "#008000", text: "#FFF" }, // Green
    7: { bg: "#8B0000", text: "#FFF" }, // Maroon
    8: { bg: "#000000", text: "#FFF" }, // Black
    9: { bg: "#FFD700", text: "#000", special: true }, // Gold/9-ball
  };

  return (
    <div className="bg-gradient-to-r from-gray-800 to-gray-900 p-6 rounded-lg shadow-lg">
      <h3 className="text-white text-lg font-bold mb-4 flex items-center gap-2">
        <span>🎱</span>
        <span>Balls on Table</span>
        <span className="text-gray-400 text-sm">({ballsOnTable.length}/9)</span>
      </h3>

      <div className="grid grid-cols-9 gap-3">
        {allBalls.map((ball) => {
          const isOnTable = ballsOnTable.includes(ball);
          const isLowest = ball === lowestBall;
          const color = ballColors[ball];

          return (
            <div
              key={ball}
              className={`
                relative w-14 h-14 rounded-full flex items-center justify-center
                font-bold text-xl shadow-lg transition-all duration-300
                ${
                  isOnTable
                    ? "scale-100 opacity-100"
                    : "scale-75 opacity-30 grayscale"
                }
                ${
                  isLowest && isOnTable
                    ? "ring-4 ring-yellow-400 ring-offset-2 ring-offset-gray-800 animate-pulse"
                    : ""
                }
                ${color.special ? "ring-2 ring-gold" : ""}
              `}
              style={{
                backgroundColor: color.bg,
                color: color.text,
              }}
              title={
                !isOnTable ? "Potted" : isLowest ? "Target Ball" : "On Table"
              }
            >
              {ball}

              {/* Lowest ball indicator */}
              {isLowest && isOnTable && (
                <div className="absolute -top-2 -right-2 bg-yellow-400 text-black text-xs px-2 py-0.5 rounded-full font-bold">
                  TARGET
                </div>
              )}

              {/* Potted overlay */}
              {!isOnTable && (
                <div className="absolute inset-0 bg-black bg-opacity-60 rounded-full flex items-center justify-center">
                  <span className="text-red-400 text-2xl">✗</span>
                </div>
              )}

              {/* 9-ball special indicator */}
              {ball === 9 && isOnTable && (
                <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 bg-gold text-black text-xs px-2 py-0.5 rounded-full font-bold whitespace-nowrap">
                  WIN
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-700 flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-white"></div>
          <span className="text-gray-400">On Table</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-gray-600"></div>
          <span className="text-gray-400">Potted</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
          <span className="text-gray-400">Target</span>
        </div>
      </div>
    </div>
  );
};

export default BallBar;
