const MEDIAPIPE_MODULE =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/vision_bundle.mjs";
const MEDIAPIPE_WASM =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm";
const HAND_MODEL =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, (a.z || 0) - (b.z || 0));

export class GestureHandTracker {
  constructor(options) {
    this.video = options.video;
    this.canvas = options.canvas;
    this.interactionElement = options.interactionElement || options.video;
    this.onPointer = options.onPointer || (() => {});
    this.onPinchStart = options.onPinchStart || (() => {});
    this.onPinchMove = options.onPinchMove || (() => {});
    this.onPinchEnd = options.onPinchEnd || (() => {});
    this.onStatus = options.onStatus || (() => {});
    this.handLandmarker = null;
    this.DrawingUtils = null;
    this.HandLandmarker = null;
    this.drawing = null;
    this.stream = null;
    this.frameRequest = 0;
    this.running = false;
    this.lastVideoTime = -1;
    this.lastDetectionAt = 0;
    this.smoothed = null;
    this.pinching = false;
    this.closeStartedAt = 0;
    this.openStartedAt = 0;
    this.lastVisibleAt = 0;
    this.frames = 0;
    this.fpsWindowStarted = 0;
    this.fps = 0;
  }

  async start() {
    if (this.running) return;
    this.onStatus({ message: "Loading pinned MediaPipe model…" });
    const vision = await import(MEDIAPIPE_MODULE);
    this.DrawingUtils = vision.DrawingUtils;
    this.HandLandmarker = vision.HandLandmarker;
    const files = await vision.FilesetResolver.forVisionTasks(MEDIAPIPE_WASM);

    const options = {
      baseOptions: {
        modelAssetPath: HAND_MODEL,
        delegate: "GPU"
      },
      runningMode: "VIDEO",
      numHands: 1,
      minHandDetectionConfidence: 0.55,
      minHandPresenceConfidence: 0.5,
      minTrackingConfidence: 0.5
    };

    try {
      this.handLandmarker = await vision.HandLandmarker.createFromOptions(files, options);
    } catch {
      options.baseOptions.delegate = "CPU";
      this.handLandmarker = await vision.HandLandmarker.createFromOptions(files, options);
    }

    this.onStatus({ message: "Waiting for camera permission…" });
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: "user",
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    });
    this.video.srcObject = this.stream;
    await this.video.play();
    await this.waitForVideoDimensions();
    this.syncCanvasSize();
    this.drawing = new this.DrawingUtils(this.canvas.getContext("2d"));
    this.running = true;
    this.lastVideoTime = -1;
    this.fpsWindowStarted = performance.now();
    this.frameRequest = requestAnimationFrame((time) => this.loop(time));
  }

  waitForVideoDimensions() {
    if (this.video.videoWidth && this.video.videoHeight) return Promise.resolve();
    return new Promise((resolve) => {
      this.video.addEventListener("loadeddata", resolve, { once: true });
    });
  }

  syncCanvasSize() {
    if (
      this.canvas.width !== this.video.videoWidth ||
      this.canvas.height !== this.video.videoHeight
    ) {
      this.canvas.width = this.video.videoWidth;
      this.canvas.height = this.video.videoHeight;
    }
  }

  loop(timestamp) {
    if (!this.running) return;
    this.frameRequest = requestAnimationFrame((time) => this.loop(time));
    if (this.video.readyState < 2 || this.video.currentTime === this.lastVideoTime) return;

    this.lastVideoTime = this.video.currentTime;
    this.syncCanvasSize();
    let result;
    try {
      result = this.handLandmarker.detectForVideo(this.video, timestamp);
    } catch {
      this.onStatus({ message: "Frame skipped · mouse still available" });
      return;
    }
    this.frames += 1;
    const elapsed = timestamp - this.fpsWindowStarted;
    if (elapsed >= 600) {
      this.fps = (this.frames * 1000) / elapsed;
      this.frames = 0;
      this.fpsWindowStarted = timestamp;
    }
    this.processResult(result, timestamp);
  }

  processResult(result, timestamp) {
    const context = this.canvas.getContext("2d");
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    const landmarks = result.landmarks?.[0];
    if (!landmarks) {
      if (this.pinching && timestamp - this.lastVisibleAt > 140) {
        const pointer = this.pointerPayload(this.smoothed, 0, false);
        this.pinching = false;
        this.onPinchEnd(pointer);
      }
      this.closeStartedAt = 0;
      this.openStartedAt = 0;
      this.onStatus({ fps: this.fps, handVisible: false, message: "Camera live · show one hand" });
      return;
    }

    this.lastVisibleAt = timestamp;
    this.drawing.drawConnectors(landmarks, this.HandLandmarker.HAND_CONNECTIONS, {
      color: "#4deeea",
      lineWidth: 3
    });
    this.drawing.drawLandmarks(landmarks, {
      color: "#b8ff6a",
      fillColor: "#07111f",
      lineWidth: 2,
      radius: 4
    });

    const indexTip = landmarks[8];
    const thumbTip = landmarks[4];
    const palmScale = Math.max(distance(landmarks[0], landmarks[9]), 0.045);
    const pinchRatio = distance(indexTip, thumbTip) / palmScale;
    const alpha = 0.34;
    this.smoothed = this.smoothed
      ? {
          x: this.smoothed.x + alpha * (indexTip.x - this.smoothed.x),
          y: this.smoothed.y + alpha * (indexTip.y - this.smoothed.y)
        }
      : { x: indexTip.x, y: indexTip.y };

    let progress = 0;
    if (!this.pinching) {
      if (pinchRatio < 0.35) {
        if (!this.closeStartedAt) this.closeStartedAt = timestamp;
        progress = Math.min(1, (timestamp - this.closeStartedAt) / 180);
        if (progress >= 1) {
          this.pinching = true;
          this.openStartedAt = 0;
          this.onPinchStart(this.pointerPayload(this.smoothed, 1, true));
        }
      } else {
        this.closeStartedAt = 0;
      }
    } else if (pinchRatio > 0.52) {
      if (!this.openStartedAt) this.openStartedAt = timestamp;
      if (timestamp - this.openStartedAt >= 90) {
        this.pinching = false;
        this.closeStartedAt = 0;
        this.openStartedAt = 0;
        this.onPinchEnd(this.pointerPayload(this.smoothed, 0, false));
      }
    } else {
      this.openStartedAt = 0;
    }

    const pointer = this.pointerPayload(
      this.smoothed,
      this.pinching ? 1 : progress,
      this.pinching
    );
    this.onPointer(pointer);
    if (this.pinching) this.onPinchMove(pointer);
    this.onStatus({ fps: this.fps, handVisible: true, message: "Hand found · pinch to grab" });
  }

  pointerPayload(point, pinchProgress, isPinching) {
    const rect = this.interactionElement.getBoundingClientRect();
    const safePoint = point || { x: 0.5, y: 0.5 };
    return {
      x: rect.left + (1 - safePoint.x) * rect.width,
      y: rect.top + safePoint.y * rect.height,
      pinchProgress,
      isPinching
    };
  }

  async stop() {
    this.running = false;
    cancelAnimationFrame(this.frameRequest);
    this.frameRequest = 0;
    if (this.pinching) {
      this.pinching = false;
      this.onPinchEnd(this.pointerPayload(this.smoothed, 0, false));
    }
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    this.video.srcObject = null;
    const context = this.canvas.getContext("2d");
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (this.handLandmarker) {
      this.handLandmarker.close();
      this.handLandmarker = null;
    }
    this.onStatus({ handVisible: false, message: "Camera optional · mouse ready" });
  }
}
