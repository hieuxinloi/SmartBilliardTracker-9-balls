import React, { useRef, useEffect, useState } from "react";

/**
 * GameBoard Component
 * Displays video/camera stream with real-time ball detection overlays
 */
const GameBoard = ({
  videoSource,
  streamUrl,
  balls,
  collisions,
  frameIdx,
  isLive,
  useCamera,
}) => {
  const canvasRef = useRef(null);
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 1280, height: 720 });
  const [videoDimensions, setVideoDimensions] = useState({
    width: 1280,
    height: 720,
  });
  const [scale, setScale] = useState({ x: 1, y: 1, offsetX: 0, offsetY: 0 });

  const ballColors = {
    cueball: "#FFFFFF",
    bi1: "#FFD700",
    bi2: "#0000FF",
    bi3: "#FF0000",
    bi4: "#800080",
    bi5: "#FFA500",
    bi6: "#008000",
    bi7: "#8B0000",
    bi8: "#000000",
    bi9: "#FFD700",
  };

  // Update canvas dimensions and calculate scale when video loads
  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const container = containerRef.current;

    if (!video || !canvas || !container) return;

    const updateDimensions = () => {
      // Get actual video dimensions (use defaults for live mode with uploaded video)
      let videoWidth = 1280;
      let videoHeight = 720;

      if (video.videoWidth && video.videoWidth > 0) {
        videoWidth = video.videoWidth;
        videoHeight = video.videoHeight;
      }

      setVideoDimensions({ width: videoWidth, height: videoHeight });

      // Get container dimensions
      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;

      // Calculate how the video fits in the container (object-contain behavior)
      const videoAspect = videoWidth / videoHeight;
      const containerAspect = containerWidth / containerHeight;

      let displayWidth, displayHeight, offsetX, offsetY;

      if (containerAspect > videoAspect) {
        // Container is wider - video height fills, width is centered
        displayHeight = containerHeight;
        displayWidth = displayHeight * videoAspect;
        offsetX = (containerWidth - displayWidth) / 2;
        offsetY = 0;
      } else {
        // Container is taller - video width fills, height is centered
        displayWidth = containerWidth;
        displayHeight = displayWidth / videoAspect;
        offsetX = 0;
        offsetY = (containerHeight - displayHeight) / 2;
      }

      // Set canvas to match container
      canvas.width = containerWidth;
      canvas.height = containerHeight;
      setDimensions({ width: containerWidth, height: containerHeight });

      // Calculate scale from video coordinates to display coordinates
      const scaleX = displayWidth / videoWidth;
      const scaleY = displayHeight / videoHeight;

      setScale({ x: scaleX, y: scaleY, offsetX, offsetY });
    };

    // Update on video metadata loaded
    video.addEventListener("loadedmetadata", updateDimensions);

    // Update on window resize
    window.addEventListener("resize", updateDimensions);

    // Initial update
    setTimeout(updateDimensions, 100);

    return () => {
      video.removeEventListener("loadedmetadata", updateDimensions);
      window.removeEventListener("resize", updateDimensions);
    };
  }, [videoSource, useCamera]);

  // Draw detection overlays with proper scaling
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // If no balls detected, just clear and return
    if (!balls || balls.length === 0) return;

    // Helper function to transform coordinates from video space to display space
    const transform = (x, y) => ({
      x: x * scale.x + scale.offsetX,
      y: y * scale.y + scale.offsetY,
    });

    const transformRadius = (r) => r * Math.min(scale.x, scale.y);

    // Draw each detected ball
    balls.forEach((ball) => {
      const { x, y, r, name, conf } = ball;

      // Transform coordinates
      const pos = transform(x, y);
      const radius = transformRadius(r);

      // Draw circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
      ctx.strokeStyle = ballColors[name] || "#00FF00";
      ctx.lineWidth = 3;
      ctx.stroke();

      // Draw center dot
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 3, 0, 2 * Math.PI);
      ctx.fillStyle = ballColors[name] || "#00FF00";
      ctx.fill();

      // Draw label
      ctx.font = "bold 16px Arial";
      ctx.fillStyle = ballColors[name] || "#00FF00";
      ctx.strokeStyle = "#000000";
      ctx.lineWidth = 3;
      ctx.strokeText(name, pos.x - 20, pos.y - radius - 10);
      ctx.fillText(name, pos.x - 20, pos.y - radius - 10);

      // Draw confidence
      ctx.font = "12px Arial";
      ctx.fillStyle = "#FFFFFF";
      ctx.strokeStyle = "#000000";
      ctx.lineWidth = 2;
      const confText = `${(conf * 100).toFixed(0)}%`;
      ctx.strokeText(confText, pos.x - 15, pos.y + radius + 20);
      ctx.fillText(confText, pos.x - 15, pos.y + radius + 20);
    });

    // Draw collision indicators
    if (collisions && collisions.length > 0) {
      collisions.forEach((collision) => {
        const { cueball, ball } = collision;

        const cuePos = transform(cueball.x, cueball.y);
        const ballPos = transform(ball.x, ball.y);
        const ballRadius = transformRadius(ball.r);

        // Draw line between cueball and hit ball
        ctx.beginPath();
        ctx.moveTo(cuePos.x, cuePos.y);
        ctx.lineTo(ballPos.x, ballPos.y);
        ctx.strokeStyle = "#FFFF00";
        ctx.lineWidth = 4;
        ctx.setLineDash([10, 5]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Highlight hit ball
        ctx.beginPath();
        ctx.arc(ballPos.x, ballPos.y, ballRadius + 5, 0, 2 * Math.PI);
        ctx.strokeStyle = "#FF0000";
        ctx.lineWidth = 5;
        ctx.stroke();
      });
    }
  }, [balls, collisions, ballColors, scale]);

  // Camera preview (client-side) when useCamera is true
  useEffect(() => {
    let stream;
    const setupCamera = async () => {
      if (!useCamera || !videoRef.current) return;
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          console.warn("getUserMedia not supported in this browser");
          return;
        }
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      } catch (e) {
        console.error("Camera access error:", e);
      }
    };

    setupCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [useCamera]);

  // Ensure video plays when source changes (but NOT when using MJPEG stream)
  useEffect(() => {
    const video = videoRef.current;
    if (!video || useCamera) return;

    // Don't play video if we're using MJPEG stream
    if (isLive && streamUrl) {
      console.log("[GameBoard] Skipping video play - using MJPEG stream");
      return;
    }

    const handleVideoLoad = async () => {
      try {
        await video.play();
        console.log("[GameBoard] Video playing");
      } catch (e) {
        console.error("[GameBoard] Video play error:", e);
      }
    };

    if (videoSource) {
      video.addEventListener("loadeddata", handleVideoLoad);
      // Try to play immediately if already loaded
      if (video.readyState >= 3) {
        handleVideoLoad();
      }
    }

    return () => {
      video.removeEventListener("loadeddata", handleVideoLoad);
    };
  }, [videoSource, useCamera, isLive, streamUrl]);

  return (
    <div
      className="relative w-full bg-gray-900 rounded-lg overflow-hidden shadow-2xl"
      style={{ minHeight: "520px" }}
    >
      {/* Video/Canvas Container */}
      <div
        ref={containerRef}
        className="relative w-full h-full min-h-[400px] xl:min-h-[600px] 2xl:min-h-[700px]"
      >
        {/* Video element or MJPEG stream */}
        {useCamera ? (
          // Camera preview (client-side stream)
          <video
            ref={videoRef}
            className="absolute top-0 left-0 w-full h-full object-contain"
            autoPlay={true}
            muted
            playsInline
          />
        ) : isLive && streamUrl ? (
          // Live mode: use server-side MJPEG stream for smooth visualization
          // Hide video element completely when using MJPEG stream
          <>
            <img
              src={streamUrl}
              alt="Live stream"
              className="absolute top-0 left-0 w-full h-full object-contain bg-black"
              onError={(e) =>
                console.error("[GameBoard] MJPEG stream error:", e)
              }
              onLoad={() => console.log("[GameBoard] MJPEG stream loaded")}
            />
            {/* Hidden video ref for dimension calculations only - don't load src */}
            <video ref={videoRef} className="hidden" muted playsInline />
          </>
        ) : videoSource ? (
          // Show uploaded video (will play in frontend while backend processes separately)
          <video
            ref={videoRef}
            className="absolute top-0 left-0 w-full h-full object-contain bg-black"
            src={videoSource}
            autoPlay={true}
            loop={isLive ? false : true}
            muted
            playsInline
            controls={false}
            preload="auto"
            onError={(e) => console.error("[GameBoard] Video error:", e)}
            onPlay={() => console.log("[GameBoard] Video started playing")}
            onPause={() => console.log("[GameBoard] Video paused")}
            onLoadedMetadata={() =>
              console.log("[GameBoard] Video metadata loaded")
            }
          />
        ) : (
          // No video source - show background with message
          <>
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
              <div className="text-gray-500 text-lg">
                🎱 {isLive ? "AI Detection Active" : "No Video Source"}
              </div>
            </div>
            <video ref={videoRef} className="hidden" muted playsInline />
          </>
        )}
        {/* Canvas overlay for detections - skip overlays when using server MJPEG */}
        {!isLive || !streamUrl ? (
          <canvas
            ref={canvasRef}
            width={dimensions.width}
            height={dimensions.height}
            className="absolute top-0 left-0 w-full h-full pointer-events-none"
            style={{
              mixBlendMode: "normal",
              background: "transparent",
            }}
          />
        ) : null}
        {/* Status indicators */}
        <div className="absolute top-4 left-4 flex gap-2">
          {isLive && (
            <div className="bg-red-600 text-white px-3 py-1 rounded-full text-sm font-bold flex items-center gap-2 animate-pulse">
              <div className="w-2 h-2 bg-white rounded-full"></div>
              LIVE
            </div>
          )}

          {balls && balls.length > 0 && (
            <div className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-bold">
              {balls.length} balls detected
            </div>
          )}
        </div>
        {/* Frame counter */}
        {frameIdx !== undefined && (
          <div className="absolute bottom-4 right-4 bg-black bg-opacity-60 text-white px-3 py-1 rounded">
            Frame: {frameIdx}
          </div>
        )}
      </div>

      {/* Info bar */}
      <div className="bg-gray-800 p-4">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-gray-400 text-sm">Detected Balls</div>
            <div className="text-white text-xl font-bold">
              {balls?.length || 0}
            </div>
          </div>
          <div>
            <div className="text-gray-400 text-sm">Collisions</div>
            <div className="text-white text-xl font-bold">
              {collisions?.length || 0}
            </div>
          </div>
          <div>
            <div className="text-gray-400 text-sm">Status</div>
            <div className="text-green-400 text-xl font-bold">
              {isLive ? "Active" : "Ready"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GameBoard;
