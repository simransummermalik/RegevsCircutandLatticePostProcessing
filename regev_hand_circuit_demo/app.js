import { GestureHandTracker } from "./hand-tracking.js";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

const refs = {
  video: $("#webcam"),
  canvas: $("#handCanvas"),
  cameraButton: $("#cameraButton"),
  cameraButtonLabel: $("#cameraButtonLabel"),
  cameraStatus: $("#cameraStatus"),
  resetButton: $("#resetButton"),
  prompt: $("#workspacePrompt"),
  count: $("#pieceCount"),
  board: $("#circuitBoard"),
  dock: $("#componentDock"),
  handCursor: $("#handCursor"),
  dragGhost: $("#dragGhost"),
  toast: $("#toast"),
  dialog: $("#completionDialog"),
  buildAgain: $("#buildAgainButton")
};

const state = {
  data: null,
  components: new Map(),
  placed: new Set(),
  selected: false,
  drag: null,
  tracker: null,
  cameraRunning: false,
  toastTimer: 0
};

function currentId() {
  return state.data?.buildOrder.find((id) => !state.placed.has(id)) || null;
}

function currentComponent() {
  return state.components.get(currentId());
}

function targetSlot() {
  const id = currentId();
  return id ? refs.board.querySelector('[data-accepts="' + id + '"]') : null;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function render() {
  const component = currentComponent();
  refs.count.textContent = state.placed.size + " / " + state.data.buildOrder.length;
  refs.prompt.textContent = component ? "Place " + component.label : "Complete";
  document.body.classList.toggle("complete", !component);

  $$(".slot", refs.board).forEach((slot) => {
    slot.classList.toggle("current", slot === targetSlot());
  });

  refs.dock.innerHTML = "";
  if (!component) return;

  const button = document.createElement("button");
  button.type = "button";
  button.className = "current-block" + (state.selected ? " selected" : "");
  button.dataset.componentId = component.id;
  button.innerHTML =
    "<strong>" + escapeHtml(component.shortLabel) + "</strong>" +
    "<span>" + escapeHtml(component.label) + "</span>";
  button.addEventListener("pointerdown", (event) => beginPointerDrag(event, component.id));
  button.addEventListener("click", (event) => {
    if (event.detail === 0) selectCurrentBlock();
  });
  refs.dock.append(button);
}

function selectCurrentBlock() {
  if (!currentId()) return;
  state.selected = true;
  render();
  showToast("Now click the outlined slot.");
}

function beginPointerDrag(event, id) {
  if (event.button !== undefined && event.button !== 0) return;
  event.preventDefault();
  state.drag = {
    id,
    source: "pointer",
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    moved: false
  };
  showGhost(id, event.clientX, event.clientY);
  window.addEventListener("pointermove", movePointerDrag);
  window.addEventListener("pointerup", endPointerDrag, { once: true });
  window.addEventListener("pointercancel", cancelDrag, { once: true });
}

function movePointerDrag(event) {
  if (!state.drag || state.drag.source !== "pointer") return;
  if (event.pointerId !== state.drag.pointerId) return;
  state.drag.moved =
    state.drag.moved ||
    Math.hypot(event.clientX - state.drag.startX, event.clientY - state.drag.startY) > 5;
  moveGhost(event.clientX, event.clientY);
  highlightTarget(event.clientX, event.clientY);
}

function endPointerDrag(event) {
  if (!state.drag || state.drag.source !== "pointer") return;
  const drag = state.drag;
  state.drag = null;
  window.removeEventListener("pointermove", movePointerDrag);
  hideGhost();
  clearTargetHighlight();

  if (isNearTarget(event.clientX, event.clientY)) {
    placeBlock(drag.id);
  } else if (!drag.moved) {
    selectCurrentBlock();
  } else {
    showToast("Drop it on the outlined slot.");
  }
}

function cancelDrag() {
  state.drag = null;
  window.removeEventListener("pointermove", movePointerDrag);
  hideGhost();
  clearTargetHighlight();
}

function isNearTarget(x, y) {
  const slot = targetSlot();
  if (!slot) return false;
  const rect = slot.getBoundingClientRect();
  const nearestX = Math.max(rect.left, Math.min(x, rect.right));
  const nearestY = Math.max(rect.top, Math.min(y, rect.bottom));
  return Math.hypot(x - nearestX, y - nearestY) < 150;
}

function highlightTarget(x, y) {
  targetSlot()?.classList.toggle("near", isNearTarget(x, y));
}

function clearTargetHighlight() {
  targetSlot()?.classList.remove("near");
}

function showGhost(id, x, y) {
  const component = state.components.get(id);
  refs.dragGhost.innerHTML =
    "<strong>" + escapeHtml(component.shortLabel) + "</strong>" +
    "<span>" + escapeHtml(component.label) + "</span>";
  refs.dragGhost.classList.add("visible");
  moveGhost(x, y);
}

function moveGhost(x, y) {
  refs.dragGhost.style.left = x + "px";
  refs.dragGhost.style.top = y + "px";
}

function hideGhost() {
  refs.dragGhost.classList.remove("visible");
}

function placeBlock(id) {
  if (id !== currentId()) return;
  const component = state.components.get(id);
  const slot = targetSlot();
  state.placed.add(id);
  state.selected = false;
  slot.classList.remove("current", "near");
  slot.classList.add("filled");
  slot.innerHTML =
    '<span class="placed-block"><strong>' +
    escapeHtml(component.shortLabel) +
    "</strong><small>" +
    escapeHtml(component.label) +
    "</small></span>";
  slot.setAttribute("aria-label", component.label + " placed");
  render();

  if (!currentId()) {
    window.setTimeout(showCompletion, 450);
  }
}

function showCompletion() {
  if (currentId()) return;
  if (typeof refs.dialog.showModal === "function") refs.dialog.showModal();
  else refs.dialog.setAttribute("open", "");
}

function reset() {
  state.placed.clear();
  state.selected = false;
  cancelDrag();
  if (refs.dialog.open) refs.dialog.close();
  $$(".slot", refs.board).forEach((slot) => {
    slot.classList.remove("filled", "current", "near");
    slot.innerHTML = "<span>" + slot.dataset.placeholder + "</span>";
    slot.setAttribute("aria-label", "Slot for " + slot.dataset.accepts);
  });
  render();
}

async function toggleCamera() {
  if (state.cameraRunning) {
    await state.tracker?.stop();
    state.cameraRunning = false;
    document.body.classList.remove("camera-on");
    refs.cameraButton.classList.remove("active");
    refs.cameraButtonLabel.textContent = "Start camera";
    refs.cameraStatus.textContent = "Camera off · mouse works too";
    refs.handCursor.classList.remove("visible", "pinching");
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    showToast("Camera access needs localhost or HTTPS.");
    return;
  }

  refs.cameraButton.disabled = true;
  refs.cameraButtonLabel.textContent = "Loading…";
  refs.cameraStatus.textContent = "Starting camera";

  try {
    state.tracker = state.tracker || new GestureHandTracker({
      video: refs.video,
      canvas: refs.canvas,
      interactionElement: refs.video,
      onPointer: updateHandPointer,
      onPinchStart: beginHandDrag,
      onPinchMove: moveHandDrag,
      onPinchEnd: endHandDrag,
      onStatus: updateHandStatus
    });
    await state.tracker.start();
    state.cameraRunning = true;
    document.body.classList.add("camera-on");
    refs.cameraButton.classList.add("active");
    refs.cameraButtonLabel.textContent = "Stop camera";
    refs.cameraStatus.textContent = "Show one hand";
  } catch (error) {
    refs.cameraButtonLabel.textContent = "Retry camera";
    refs.cameraStatus.textContent = "Mouse works without the camera";
    showToast(error.message || "Camera could not start.");
  } finally {
    refs.cameraButton.disabled = false;
  }
}

function updateHandStatus(status) {
  if (!state.cameraRunning) return;
  refs.cameraStatus.textContent = status.handVisible ? "Hand found" : "Show one hand";
  if (!status.handVisible) refs.handCursor.classList.remove("visible");
}

function updateHandPointer(pointer) {
  refs.handCursor.classList.add("visible");
  refs.handCursor.classList.toggle("pinching", pointer.isPinching);
  refs.handCursor.style.left = pointer.x + "px";
  refs.handCursor.style.top = pointer.y + "px";
  refs.handCursor.style.setProperty("--pinch-progress", String(pointer.pinchProgress));
  if (state.drag?.source === "hand") {
    moveGhost(pointer.x, pointer.y);
    highlightTarget(pointer.x, pointer.y);
  }
}

function beginHandDrag(pointer) {
  const id = currentId();
  if (!id) return;
  state.drag = { id, source: "hand" };
  showGhost(id, pointer.x, pointer.y);
}

function moveHandDrag(pointer) {
  if (!state.drag || state.drag.source !== "hand") return;
  moveGhost(pointer.x, pointer.y);
  highlightTarget(pointer.x, pointer.y);
}

function endHandDrag(pointer) {
  if (!state.drag || state.drag.source !== "hand") return;
  const id = state.drag.id;
  state.drag = null;
  hideGhost();
  clearTargetHighlight();
  if (isNearTarget(pointer.x, pointer.y)) placeBlock(id);
  else showToast("Release over the outlined slot.");
}

function showToast(message) {
  window.clearTimeout(state.toastTimer);
  refs.toast.textContent = message;
  refs.toast.classList.add("visible");
  state.toastTimer = window.setTimeout(() => refs.toast.classList.remove("visible"), 2200);
}

function bindEvents() {
  refs.cameraButton.addEventListener("click", toggleCamera);
  refs.resetButton.addEventListener("click", reset);
  refs.buildAgain.addEventListener("click", reset);

  $$(".slot", refs.board).forEach((slot) => {
    slot.dataset.placeholder = $("span", slot).textContent;
    slot.addEventListener("click", () => {
      if (slot === targetSlot()) placeBlock(currentId());
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.drag) cancelDrag();
  });
  window.addEventListener("beforeunload", () => state.tracker?.stop());
}

async function init() {
  try {
    const response = await fetch("./demo-data.json");
    if (!response.ok) throw new Error("Demo data could not load.");
    state.data = await response.json();
    state.components = new Map(
      state.data.components.map((component) => [component.id, component])
    );
    bindEvents();
    render();
  } catch {
    refs.prompt.textContent = "Run the local server, then refresh.";
    refs.dock.innerHTML = "";
  }
}

init();
