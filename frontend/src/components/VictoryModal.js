import React, { useEffect, useState } from "react";

/**
 * VictoryModal Component
 * End-game celebration and match summary
 */
const VictoryModal = ({
  winner,
  players,
  onRestart,
  onClose,
  matchDuration,
}) => {
  const [confetti, setConfetti] = useState([]);

  // Generate confetti particles
  useEffect(() => {
    const particles = Array.from({ length: 50 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 2,
      duration: 3 + Math.random() * 2,
      color: ["#FFD700", "#FF0000", "#0000FF", "#00FF00", "#FF00FF"][
        Math.floor(Math.random() * 5)
      ],
    }));
    setConfetti(particles);
  }, []);

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 backdrop-blur-sm animate-fadeIn">
      {/* Confetti */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {confetti.map((particle) => (
          <div
            key={particle.id}
            className="absolute w-2 h-2 rounded-full animate-fall"
            style={{
              left: `${particle.left}%`,
              top: "-20px",
              backgroundColor: particle.color,
              animationDelay: `${particle.delay}s`,
              animationDuration: `${particle.duration}s`,
            }}
          />
        ))}
      </div>

      {/* Modal content */}
      <div className="relative bg-gradient-to-br from-gray-800 to-gray-900 rounded-2xl shadow-2xl p-8 max-w-2xl w-full mx-4 animate-scaleIn">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>

        {/* Trophy and winner announcement */}
        <div className="text-center mb-8">
          <div className="text-8xl mb-4 animate-bounce">🏆</div>
          <h1 className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-yellow-600 mb-2">
            Victory!
          </h1>
          <p className="text-3xl text-white font-bold">{winner.name}</p>
          <p className="text-gray-400 mt-2">has won the match!</p>
        </div>

        {/* Match statistics */}
        <div className="bg-black bg-opacity-40 rounded-lg p-6 mb-6">
          <h3 className="text-white text-lg font-bold mb-4 text-center">
            Match Summary
          </h3>

          <div className="grid grid-cols-2 gap-4">
            {players.map((player) => (
              <div
                key={player.id}
                className={`
                  p-4 rounded-lg transition-all
                  ${
                    player.name === winner.name
                      ? "bg-gradient-to-br from-yellow-500 to-yellow-600 ring-4 ring-yellow-400"
                      : "bg-gray-700"
                  }
                `}
              >
                <div className="text-center">
                  <div
                    className={`text-xl font-bold mb-2 ${
                      player.name === winner.name ? "text-black" : "text-white"
                    }`}
                  >
                    {player.name}
                    {player.name === winner.name && " 👑"}
                  </div>

                  <div
                    className={`grid grid-cols-2 gap-2 text-sm ${
                      player.name === winner.name
                        ? "text-black"
                        : "text-gray-300"
                    }`}
                  >
                    <div>
                      <div className="font-semibold">Potted</div>
                      <div className="text-2xl font-bold">
                        {player.potted_balls.length}
                      </div>
                    </div>
                    <div>
                      <div className="font-semibold">Fouls</div>
                      <div className="text-2xl font-bold">
                        {player.foul_count}
                      </div>
                    </div>
                  </div>

                  {/* Potted balls */}
                  <div className="mt-3 flex flex-wrap justify-center gap-1">
                    {player.potted_balls.map((ball) => (
                      <div
                        key={ball}
                        className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          ball === 9 ? "ring-2 ring-white" : ""
                        }`}
                        style={{
                          backgroundColor: ball === 9 ? "#FFD700" : "#666",
                          color: "#FFF",
                        }}
                      >
                        {ball}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Match duration */}
          {matchDuration && (
            <div className="mt-4 text-center text-gray-400">
              <span className="text-sm">Match Duration: </span>
              <span className="text-white font-bold">
                {formatDuration(matchDuration)}
              </span>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-4">
          <button
            onClick={onRestart}
            className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-bold py-4 px-6 rounded-lg transition-all transform hover:scale-105 shadow-lg"
          >
            🔄 New Game
          </button>
          <button
            onClick={onClose}
            className="flex-1 bg-gradient-to-r from-gray-600 to-gray-700 hover:from-gray-700 hover:to-gray-800 text-white font-bold py-4 px-6 rounded-lg transition-all transform hover:scale-105 shadow-lg"
          >
            📊 View Details
          </button>
        </div>

        {/* Congratulations message */}
        <p className="text-center text-gray-400 mt-6 italic">
          "Great game! {winner.name} showed excellent skill and strategy."
        </p>
      </div>

      <style jsx>{`
        @keyframes fall {
          0% {
            transform: translateY(0) rotate(0deg);
            opacity: 1;
          }
          100% {
            transform: translateY(100vh) rotate(360deg);
            opacity: 0;
          }
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes scaleIn {
          from {
            transform: scale(0.8);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }

        .animate-fall {
          animation: fall linear infinite;
        }

        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }

        .animate-scaleIn {
          animation: scaleIn 0.4s ease-out;
        }
      `}</style>
    </div>
  );
};

export default VictoryModal;
