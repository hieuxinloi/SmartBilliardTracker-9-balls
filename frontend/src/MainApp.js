import React, { useState } from "react";
import App from "./App";
import AppGame from "./AppGame";

function MainApp() {
  const [mode, setMode] = useState(null); // null, 'video', or 'game'

  if (mode === "video") {
    return (
      <div>
        <button
          onClick={() => setMode(null)}
          className="fixed top-4 right-4 z-50 bg-white hover:bg-gray-100 text-gray-800 px-4 py-2 rounded-lg shadow-lg border border-gray-300 transition-colors flex items-center gap-2"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            />
          </svg>
          Back to Menu
        </button>
        <App />
      </div>
    );
  }

  if (mode === "game") {
    return (
      <div>
        <button
          onClick={() => setMode(null)}
          className="fixed top-4 right-4 z-50 bg-white hover:bg-gray-100 text-gray-800 px-4 py-2 rounded-lg shadow-lg border border-gray-300 transition-colors flex items-center gap-2"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            />
          </svg>
          Back to Menu
        </button>
        <AppGame />
      </div>
    );
  }

  // Landing page with mode selection
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-purple-900">
      {/* Header */}
      <header className="bg-black bg-opacity-30 backdrop-blur-sm border-b border-white border-opacity-20">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <div className="text-5xl">🎱</div>
            <div>
              <h1 className="text-4xl font-bold text-white">
                SmartBilliardTracker
              </h1>
              <p className="text-blue-200 mt-1">
                AI-Powered Billiards Analysis & Referee System
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-white mb-4">
            Choose Your Mode
          </h2>
          <p className="text-blue-200 text-lg">
            Select how you want to use SmartBilliardTracker
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Video Processing Mode */}
          <div
            onClick={() => setMode("video")}
            className="bg-white bg-opacity-10 backdrop-blur-md rounded-2xl p-8 border-2 border-white border-opacity-20 hover:border-opacity-40 cursor-pointer transition-all duration-300 hover:transform hover:scale-105 hover:shadow-2xl group"
          >
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform">
                <svg
                  className="w-10 h-10 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">
                Video Processing
              </h3>
              <p className="text-blue-200 mb-6">
                Upload and analyze recorded billiards videos
              </p>

              <div className="space-y-3 text-left">
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">
                    Upload MP4, AVI, MOV, MKV files
                  </span>
                </div>
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">
                    Automatic ball detection & tracking
                  </span>
                </div>
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">
                    Collision detection & analysis
                  </span>
                </div>
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">
                    Export results (JSON/CSV)
                  </span>
                </div>
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">
                    Download annotated video
                  </span>
                </div>
              </div>

              <div className="mt-8">
                <div className="bg-blue-500 bg-opacity-20 text-blue-200 px-4 py-2 rounded-lg font-medium group-hover:bg-opacity-30 transition-colors">
                  Click to Start →
                </div>
              </div>
            </div>
          </div>

          {/* Live Game Mode */}
          <div
            onClick={() => setMode("game")}
            className="bg-white bg-opacity-10 backdrop-blur-md rounded-2xl p-8 border-2 border-white border-opacity-20 hover:border-opacity-40 cursor-pointer transition-all duration-300 hover:transform hover:scale-105 hover:shadow-2xl group"
          >
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-purple-400 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform">
                <svg
                  className="w-10 h-10 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">
                Live Game Mode
              </h3>
              <p className="text-blue-200 mb-6">
                Real-time AI referee for 9-ball billiards
              </p>

              <div className="space-y-3 text-left">
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">Real-time ball tracking</span>
                </div>
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">
                    Automatic turn management
                  </span>
                </div>
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">Foul detection & alerts</span>
                </div>
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">9-ball rule enforcement</span>
                </div>
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-blue-100">
                    Match statistics & history
                  </span>
                </div>
              </div>

              <div className="mt-8">
                <div className="bg-purple-500 bg-opacity-20 text-purple-200 px-4 py-2 rounded-lg font-medium group-hover:bg-opacity-30 transition-colors">
                  Click to Start →
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-16 bg-white bg-opacity-10 backdrop-blur-md rounded-2xl p-8 border border-white border-opacity-20">
          <h3 className="text-2xl font-bold text-white text-center mb-8">
            Powered by Advanced AI
          </h3>
          <div className="grid md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-4xl mb-3">🤖</div>
              <h4 className="text-white font-semibold mb-2">
                YOLOv8 Detection
              </h4>
              <p className="text-blue-200 text-sm">
                State-of-the-art object detection for accurate ball tracking
              </p>
            </div>
            <div>
              <div className="text-4xl mb-3">⚡</div>
              <h4 className="text-white font-semibold mb-2">
                Real-time Processing
              </h4>
              <p className="text-blue-200 text-sm">
                Low-latency analysis with instant feedback and alerts
              </p>
            </div>
            <div>
              <div className="text-4xl mb-3">📊</div>
              <h4 className="text-white font-semibold mb-2">
                Detailed Analytics
              </h4>
              <p className="text-blue-200 text-sm">
                Comprehensive statistics and exportable match data
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-4 py-8 text-center">
        <p className="text-blue-300 text-sm">
          SmartBilliardTracker v2.0 | AI-Powered Billiards Analysis & Referee
          System
        </p>
      </footer>
    </div>
  );
}

export default MainApp;
