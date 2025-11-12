import React from "react";

/**
 * FoulAlert Component
 * Animated red flash alert when a foul occurs
 */
const FoulAlert = ({ foulReason, playerName, onDismiss }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none animate-pulse-fast">
      {/* Red flash overlay */}
      <div className="absolute inset-0 bg-red-600 opacity-30 animate-flash"></div>

      {/* Alert box */}
      <div className="relative bg-red-600 text-white p-8 rounded-2xl shadow-2xl pointer-events-auto animate-shake max-w-lg mx-4">
        <div className="text-center">
          <div className="text-6xl mb-4">🚫</div>
          <h2 className="text-4xl font-bold mb-2">FOUL!</h2>
          <p className="text-xl mb-2">{playerName}</p>
          <p className="text-lg opacity-90">{foulReason}</p>

          {onDismiss && (
            <button
              onClick={onDismiss}
              className="mt-6 bg-white text-red-600 font-bold py-2 px-6 rounded-lg hover:bg-gray-100 transition-colors"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>

      <style jsx>{`
        @keyframes flash {
          0%,
          100% {
            opacity: 0;
          }
          50% {
            opacity: 0.4;
          }
        }

        @keyframes shake {
          0%,
          100% {
            transform: translateX(0);
          }
          10%,
          30%,
          50%,
          70%,
          90% {
            transform: translateX(-10px);
          }
          20%,
          40%,
          60%,
          80% {
            transform: translateX(10px);
          }
        }

        @keyframes pulse-fast {
          0%,
          100% {
            opacity: 1;
          }
          50% {
            opacity: 0.8;
          }
        }

        .animate-flash {
          animation: flash 0.5s ease-in-out 3;
        }

        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }

        .animate-pulse-fast {
          animation: pulse-fast 0.5s ease-in-out 3;
        }
      `}</style>
    </div>
  );
};

export default FoulAlert;
