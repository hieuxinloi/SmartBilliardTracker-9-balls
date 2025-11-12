import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useDropzone } from "react-dropzone";
import "./App.css";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";
const WS_URL = process.env.REACT_APP_WS_URL || "ws://localhost:8000/ws";

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [ws, setWs] = useState(null);
  const [notifications, setNotifications] = useState([]);

  // WebSocket connection
  useEffect(() => {
    const websocket = new WebSocket(WS_URL);

    websocket.onopen = () => {
      console.log("WebSocket connected");
      setWs(websocket);
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    websocket.onclose = () => {
      console.log("WebSocket disconnected");
      // Reconnect after 3 seconds
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    };

    return () => {
      websocket.close();
    };
  }, []);

  const handleWebSocketMessage = (message) => {
    console.log("WebSocket message:", message);

    if (
      message.type === "status_update" ||
      message.type === "processing_complete"
    ) {
      // Refresh sessions list
      fetchSessions();

      // Show notification
      addNotification(
        message.message,
        message.type === "error" ? "error" : "success"
      );

      // If current session is updated, refresh it
      if (currentSession && currentSession.session_id === message.session_id) {
        fetchSessionDetails(message.session_id);
      }
    }
  };

  const addNotification = (message, type = "info") => {
    const id = Date.now();
    setNotifications((prev) => [...prev, { id, message, type }]);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    }, 5000);
  };

  // Fetch all sessions
  const fetchSessions = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/sessions`);
      setSessions(response.data.sessions);
    } catch (error) {
      console.error("Error fetching sessions:", error);
    }
  };

  // Fetch session details
  const fetchSessionDetails = async (sessionId) => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/sessions/${sessionId}`
      );
      setCurrentSession(response.data);
    } catch (error) {
      console.error("Error fetching session details:", error);
      addNotification("Failed to load session details", "error");
    }
  };

  // Load sessions on mount
  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  // File upload handler
  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/sessions/upload`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      addNotification(
        "Video uploaded successfully! Processing started...",
        "success"
      );
      await fetchSessions();
      await fetchSessionDetails(response.data.session_id);
    } catch (error) {
      console.error("Error uploading file:", error);
      addNotification("Failed to upload video", "error");
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "video/*": [".mp4", ".avi", ".mov", ".mkv"],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  // Export collisions
  const exportCollisions = async (format) => {
    if (!currentSession) return;

    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/sessions/${currentSession.session_id}/collisions/export?format=${format}`,
        { responseType: format === "csv" ? "blob" : "json" }
      );

      if (format === "csv") {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute(
          "download",
          `collisions_${currentSession.session_id}.csv`
        );
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        const dataStr = JSON.stringify(response.data, null, 2);
        const dataBlob = new Blob([dataStr], { type: "application/json" });
        const url = window.URL.createObjectURL(dataBlob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute(
          "download",
          `collisions_${currentSession.session_id}.json`
        );
        document.body.appendChild(link);
        link.click();
        link.remove();
      }

      addNotification(
        `Collisions exported as ${format.toUpperCase()}`,
        "success"
      );
    } catch (error) {
      console.error("Error exporting collisions:", error);
      addNotification("Failed to export collisions", "error");
    }
  };

  // Download output video
  const downloadVideo = () => {
    if (!currentSession || !currentSession.output_video_url) return;

    const link = document.createElement("a");
    link.href = `${API_BASE_URL}${currentSession.output_video_url}`;
    link.download = `output_${currentSession.video_name}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "completed":
        return "text-green-600 bg-green-100";
      case "processing":
        return "text-blue-600 bg-blue-100";
      case "uploaded":
        return "text-yellow-600 bg-yellow-100";
      case "error":
        return "text-red-600 bg-red-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold">🎱 SmartBilliardTracker</h1>
          <p className="text-blue-100 mt-1">
            AI-Powered Referee Support System
          </p>
        </div>
      </header>

      {/* Notifications */}
      <div className="fixed top-20 right-4 z-50 space-y-2">
        {notifications.map((notif) => (
          <div
            key={notif.id}
            className={`px-6 py-4 rounded-lg shadow-lg ${
              notif.type === "error"
                ? "bg-red-500"
                : notif.type === "success"
                ? "bg-green-500"
                : "bg-blue-500"
            } text-white animate-slide-in`}
          >
            {notif.message}
          </div>
        ))}
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Upload & Sessions */}
          <div className="lg:col-span-1 space-y-6">
            {/* Upload Section */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-800">
                Upload Video
              </h2>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${
                  isDragActive
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-300 hover:border-blue-400"
                } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                <input {...getInputProps()} />
                {uploading ? (
                  <div className="flex flex-col items-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                    <p className="text-gray-600">Uploading...</p>
                  </div>
                ) : (
                  <div>
                    <svg
                      className="mx-auto h-12 w-12 text-gray-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                    <p className="mt-2 text-sm text-gray-600">
                      {isDragActive
                        ? "Drop video here..."
                        : "Drag & drop video or click to browse"}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      MP4, AVI, MOV, MKV
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Sessions List */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-800">
                Recent Sessions
              </h2>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {sessions.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">
                    No sessions yet
                  </p>
                ) : (
                  sessions.map((session) => (
                    <div
                      key={session.session_id}
                      onClick={() => fetchSessionDetails(session.session_id)}
                      className={`p-3 rounded cursor-pointer transition-all ${
                        currentSession?.session_id === session.session_id
                          ? "bg-blue-50 border-2 border-blue-500"
                          : "border border-gray-200 hover:border-blue-300"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {session.video_name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(session.created_at).toLocaleString()}
                          </p>
                        </div>
                        <span
                          className={`ml-2 px-2 py-1 text-xs rounded-full ${getStatusColor(
                            session.status
                          )}`}
                        >
                          {session.status}
                        </span>
                      </div>
                      {session.collisions_count > 0 && (
                        <p className="text-xs text-blue-600 mt-1">
                          {session.collisions_count} collision
                          {session.collisions_count !== 1 ? "s" : ""}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Right Panel - Session Details */}
          <div className="lg:col-span-2">
            {currentSession ? (
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-semibold text-gray-800">
                      {currentSession.video_name}
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                      Session ID: {currentSession.session_id}
                    </p>
                  </div>
                  <span
                    className={`px-4 py-2 rounded-full text-sm font-medium ${getStatusColor(
                      currentSession.status
                    )}`}
                  >
                    {currentSession.status}
                  </span>
                </div>

                {/* Actions */}
                {currentSession.status === "completed" && (
                  <div className="flex gap-3 mb-6">
                    <button
                      onClick={downloadVideo}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                    >
                      📥 Download Video
                    </button>
                    <button
                      onClick={() => exportCollisions("json")}
                      className="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
                    >
                      📄 Export JSON
                    </button>
                    <button
                      onClick={() => exportCollisions("csv")}
                      className="flex-1 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
                    >
                      📊 Export CSV
                    </button>
                  </div>
                )}

                {/* Processing status */}
                {currentSession.status === "processing" && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                    <div className="flex items-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
                      <div>
                        <p className="font-medium text-blue-900">
                          Processing video...
                        </p>
                        <p className="text-sm text-blue-700">
                          Detecting balls and analyzing collisions
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Collisions */}
                {currentSession.collisions &&
                currentSession.collisions.length > 0 ? (
                  <div>
                    <h3 className="text-lg font-semibold mb-4 text-gray-800">
                      Collisions Detected ({currentSession.collisions.length})
                    </h3>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {currentSession.collisions.map((collision, idx) => (
                        <div
                          key={idx}
                          className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <p className="font-medium text-gray-900">
                                Frame {collision.frame_id}
                              </p>
                              <div className="mt-2 space-y-1 text-sm">
                                <p className="text-gray-600">
                                  <span className="font-medium">Cueball:</span>{" "}
                                  ({collision.cueball.x.toFixed(1)},{" "}
                                  {collision.cueball.y.toFixed(1)})
                                </p>
                                <p className="text-gray-600">
                                  <span className="font-medium">
                                    Hit {collision.ball.name}:
                                  </span>{" "}
                                  ({collision.ball.x.toFixed(1)},{" "}
                                  {collision.ball.y.toFixed(1)})
                                </p>
                              </div>
                            </div>
                            <div className="ml-4 text-right">
                              <span className="inline-block px-3 py-1 bg-red-100 text-red-800 text-xs rounded-full">
                                {collision.ball.name}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : currentSession.status === "completed" ? (
                  <div className="text-center py-8 text-gray-500">
                    <p>No collisions detected in this video</p>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-md p-12 text-center">
                <svg
                  className="mx-auto h-16 w-16 text-gray-400 mb-4"
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
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No Session Selected
                </h3>
                <p className="text-gray-500">
                  Upload a video or select a session to view details
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
