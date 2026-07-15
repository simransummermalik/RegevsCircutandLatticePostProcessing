import { GestureHandTracker } from "./hand-tracking.js";

const ICONS = {
  register: "x",
  hadamard: "H",
  workspace: "ψ",
  arithmetic: "×",
  qft: "F⁻¹",
  measure: "M"
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
const delay = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

const refs = {
  palette: $("#componentPalette"),
  pieceCount: $("#pieceCount"),
  modeHelp: $("#modeHelp"),
  prompt: $("#workspacePrompt"),
  modePill: $("#modePill"),
  formula: $("#arithmeticFormula"),
  superposition: $("#superpositionVisual"),
  board: $("#circuitBoard"),
  workspace: $("#circuitWorkspace"),
  cameraStage: $("#cameraStage"),
  video: $("#webcam"),
  handCanvas: $("#handCanvas"),
  cameraPlaceholder: $("#cameraPlaceholder"),
  cameraButton: $("#cameraButton"),
  cameraButtonLabel: $("#cameraButtonLabel"),
  cameraStatus: $("#cameraStatus"),
  trackingFps: $("#trackingFps"),
  pinchState: $("#pinchState"),
  handCursor: $("#handCursor"),
  progressFill: $("#progressFill"),
  qftLab: $("#qftLab"),
  phaseGates: $("#phaseGates"),
  sampleStream: $("#sampleStream"),
  pipeline: $("#latticePipeline"),
  postProcessing: $("#postProcessing"),
  factorReveal: $("#factorReveal"),
  dialog: $("#completionDialog"),
  runLatticeButton: $("#runLatticeButton"),
  dragGhost: $("#dragGhost"),
  toast: $("#toast"),
  guidedMode: $("#guidedMode"),
  challengeMode: $("#challengeMode"),
  autoplayButton: $("#autoplayButton"),
  fullscreenButton: $("#fullscreenButton"),
  resetButton: $("#resetButton"),
  componentKind: $("#componentKind"),
  explanationGlyph: $("#explanationGlyph"),
  explanationStage: $("#explanationStage"),
  explanationTitle: $("#explanationTitle"),
  formulaCard: $("#formulaCard"),
  whatText: $("#whatText"),
  roleText: $("#roleText"),
  builtText: $("#builtText"),
  codeLink: $("#codeLink"),
  codeSymbol: $("#codeSymbol"),
  cpRemoved: $("#cpRemoved"),
  cxRemoved: $("#cxRemoved"),
  certificateText: $("#certificateText"),
  observedText: $("#observedText"),
  evidenceScope: $("#evidenceScope")
};

const state = {
  data: null,
  components: new Map(),
  placed: new Set(),
  mode: "guided",
  selectedId: null,
  drag: null,
  qftPreset: "exact",
  completed: false,
  recoveryRunning: false,
  handTracker: null,
  cameraRunning: false,
  autoplayRun: 0,
  toastTimer: null,
  audioContext: null
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function currentComponentId() {
  if (!state.data) return null;
  return state.data.buildOrder.find((id) => !state.placed.has(id)) || null;
}

function componentFor(id) {
  return state.components.get(id);
}

function componentButton(id) {
  return refs.palette.querySelector('[data-component-id="' + id + '"]');
}

function slotFor(id) {
  return refs.board.querySelector('[data-accepts="' + id + '"]');
}

function renderPalette() {
  refs.palette.innerHTML = "";
  state.data.components.forEach((component, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "component-card kind-" + component.kind;
    button.dataset.componentId = component.id;
    button.setAttribute("aria-label", "Circuit component: " + component.label);
    button.innerHTML =
      '<span class="component-index">' + String(index + 1).padStart(2, "0") + "</span>" +
      '<span class="component-card-icon">' + escapeHtml(ICONS[component.kind] || "•") + "</span>" +
      '<span class="component-card-copy"><strong>' + escapeHtml(component.label) +
      "</strong><small>" + escapeHtml(component.stage) + "</small></span>" +
      '<span class="component-state">grab</span>';

    button.addEventListener("pointerdown", (event) => beginPointerDrag(event, component.id));
    button.addEventListener("mouseenter", () => showExplanation(component.id));
    button.addEventListener("focus", () => showExplanation(component.id));
    button.addEventListener("click", (event) => {
      if (event.detail === 0 && isComponentAvailable(component.id)) {
        selectComponent(component.id);
      }
    });
    refs.palette.append(button);
  });
  updateAvailability();
}

function renderPipeline() {
  refs.pipeline.innerHTML = "";
  state.data.latticePipeline.forEach((step, index) => {
    const item = document.createElement("article");
    item.className = "pipeline-step";
    item.dataset.pipelineIndex = String(index);
    item.innerHTML =
      '<span class="pipeline-number">' + String(index + 1).padStart(2, "0") + "</span>" +
      '<div><strong>' + escapeHtml(step.label) + "</strong><p>" + escapeHtml(step.detail) + "</p></div>" +
      '<span class="pipeline-check">✓</span>';
    refs.pipeline.append(item);
    if (index < state.data.latticePipeline.length - 1) {
      const arrow = document.createElement("span");
      arrow.className = "pipeline-arrow";
      arrow.textContent = "↓";
      refs.pipeline.append(arrow);
    }
  });
}

function isComponentAvailable(id) {
  if (state.placed.has(id)) return false;
  return state.mode === "challenge" || currentComponentId() === id;
}

function updateAvailability() {
  const currentId = currentComponentId();
  $$(".component-card", refs.palette).forEach((button) => {
    const id = button.dataset.componentId;
    const placed = state.placed.has(id);
    const enabled = isComponentAvailable(id);
    button.classList.toggle("placed", placed);
    button.classList.toggle("disabled", !enabled && !placed);
    button.classList.toggle("current-target", state.mode === "guided" && id === currentId);
    button.disabled = placed;
    button.setAttribute("aria-disabled", String(!enabled));
    $(".component-state", button).textContent = placed ? "placed" : enabled ? "grab" : "locked";
  });
  $$(".circuit-slot", refs.board).forEach((slot) => {
    slot.classList.toggle(
      "current-target",
      state.mode === "guided" && slot.dataset.accepts === currentId
    );
  });

  refs.pieceCount.textContent = state.placed.size + " / " + state.data.buildOrder.length;
  refs.progressFill.style.width = (100 * state.placed.size / state.data.buildOrder.length) + "%";
  refs.modePill.textContent =
    state.mode === "guided"
      ? "Guided " + String(Math.min(state.placed.size + 1, 12)).padStart(2, "0")
      : "Challenge";

  const next = componentFor(currentId);
  refs.prompt.textContent = next
    ? state.mode === "guided"
      ? "Place " + next.label
      : "Assemble the audited circuit"
    : "Quantum sampling architecture complete";
  updateStageProgress(next ? next.stage : "Lattice recovery");
}

function updateStageProgress(stage) {
  const stages = ["Exponent state", "Arithmetic", "Fourier sampling", "Measurement", "Lattice recovery"];
  const activeIndex = Math.max(0, stages.indexOf(stage));
  $$(".stage-labels span").forEach((label, index) => {
    label.classList.toggle("active", index === activeIndex);
    label.classList.toggle("passed", index < activeIndex);
  });
}

function showExplanation(id) {
  const component = componentFor(id);
  if (!component) return;
  refs.componentKind.textContent = component.kind;
  refs.explanationGlyph.textContent = component.shortLabel;
  refs.explanationStage.textContent = component.stage;
  refs.explanationTitle.textContent = component.label;
  refs.formulaCard.textContent = component.formula;
  refs.whatText.textContent = component.what;
  refs.roleText.textContent = component.role;
  refs.builtText.textContent = component.built;
  refs.codeLink.href = component.codeFile;
  refs.codeSymbol.textContent = component.codeSymbol;
  $(".explanation-panel").classList.remove("explanation-pulse");
  window.requestAnimationFrame(() => $(".explanation-panel").classList.add("explanation-pulse"));
}

function selectComponent(id) {
  if (!isComponentAvailable(id)) {
    explainUnavailable(id);
    return;
  }
  state.selectedId = id;
  $$(".component-card").forEach((button) => {
    button.classList.toggle("selected", button.dataset.componentId === id);
  });
  showExplanation(id);
  showToast(componentFor(id).label + " selected — click its circuit slot.", "info");
}

function beginPointerDrag(event, id) {
  if (event.button !== undefined && event.button !== 0) return;
  if (!isComponentAvailable(id)) {
    explainUnavailable(id);
    return;
  }
  event.preventDefault();
  state.drag = {
    id,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    moved: false,
    source: "pointer"
  };
  showExplanation(id);
  showDragGhost(id, event.clientX, event.clientY);
  window.addEventListener("pointermove", continuePointerDrag);
  window.addEventListener("pointerup", finishPointerDrag, { once: true });
  window.addEventListener("pointercancel", cancelPointerDrag, { once: true });
}

function continuePointerDrag(event) {
  if (!state.drag || state.drag.source !== "pointer" || event.pointerId !== state.drag.pointerId) return;
  const distance = Math.hypot(event.clientX - state.drag.startX, event.clientY - state.drag.startY);
  state.drag.moved = state.drag.moved || distance > 5;
  moveDragGhost(event.clientX, event.clientY);
  highlightNearestSlot(event.clientX, event.clientY);
}

function finishPointerDrag(event) {
  if (!state.drag || state.drag.source !== "pointer") return;
  const drag = state.drag;
  const point = { x: event.clientX, y: event.clientY };
  state.drag = null;
  window.removeEventListener("pointermove", continuePointerDrag);
  hideDragGhost();
  clearSnapTargets();
  const slot = nearestSlot(point.x, point.y);
  if (slot) {
    attemptPlace(drag.id, slot);
  } else if (!drag.moved) {
    selectComponent(drag.id);
  } else {
    showToast("Move closer to a circuit slot and release again.", "info");
  }
}

function cancelPointerDrag() {
  state.drag = null;
  window.removeEventListener("pointermove", continuePointerDrag);
  hideDragGhost();
  clearSnapTargets();
}

function showDragGhost(id, x, y) {
  const component = componentFor(id);
  refs.dragGhost.className = "drag-ghost visible kind-" + component.kind;
  refs.dragGhost.innerHTML =
    "<strong>" + escapeHtml(component.shortLabel) + "</strong><span>" + escapeHtml(component.label) + "</span>";
  moveDragGhost(x, y);
  componentButton(id)?.classList.add("dragging");
}

function moveDragGhost(x, y) {
  refs.dragGhost.style.transform = "translate3d(" + x + "px," + y + "px,0)";
}

function hideDragGhost() {
  refs.dragGhost.classList.remove("visible");
  $$(".component-card.dragging").forEach((button) => button.classList.remove("dragging"));
}

function nearestSlot(x, y) {
  let best = null;
  let bestDistance = 136;
  $$(".circuit-slot:not(.filled)", refs.board).forEach((slot) => {
    const rect = slot.getBoundingClientRect();
    const cx = Math.max(rect.left, Math.min(x, rect.right));
    const cy = Math.max(rect.top, Math.min(y, rect.bottom));
    const edgeDistance = Math.hypot(x - cx, y - cy);
    const centerDistance = Math.hypot(x - (rect.left + rect.width / 2), y - (rect.top + rect.height / 2));
    const score = edgeDistance === 0 ? centerDistance * 0.15 : edgeDistance;
    if (score < bestDistance) {
      bestDistance = score;
      best = slot;
    }
  });
  return best;
}

function highlightNearestSlot(x, y) {
  const closest = nearestSlot(x, y);
  $$(".circuit-slot", refs.board).forEach((slot) => {
    slot.classList.toggle("snap-target", slot === closest);
  });
}

function clearSnapTargets() {
  $$(".circuit-slot.snap-target", refs.board).forEach((slot) => slot.classList.remove("snap-target"));
}

function attemptPlace(id, slot) {
  if (!slot || state.placed.has(id)) return false;
  if (!isComponentAvailable(id)) {
    explainUnavailable(id);
    return false;
  }
  const expected = slot.dataset.accepts;
  if (expected !== id) {
    showExplanation(id);
    slot.classList.add("wrong-target");
    window.setTimeout(() => slot.classList.remove("wrong-target"), 550);
    showToast(educationalError(id, expected), "error");
    return false;
  }
  placeComponent(id);
  return true;
}

function placeComponent(id, options = {}) {
  const component = componentFor(id);
  const slot = slotFor(id);
  if (!component || !slot || state.placed.has(id)) return;

  state.placed.add(id);
  state.selectedId = null;
  slot.classList.add("filled");
  slot.innerHTML =
    '<span class="placed-piece kind-' + component.kind + '">' +
    '<span class="placed-glyph">' + escapeHtml(component.shortLabel) + "</span>" +
    '<span class="placed-label">' + escapeHtml(component.label) + "</span>" +
    "</span>";
  slot.setAttribute("aria-label", component.label + " placed");
  showExplanation(id);
  updateAvailability();
  updateSpecialVisuals();
  soundSuccess();
  if (!options.silent) showToast(component.label + " snapped into place.", "success");

  if (state.placed.size === state.data.buildOrder.length) {
    completeCircuit();
  }
}

function updateSpecialVisuals() {
  const hasHadamards = state.placed.has("h1") && state.placed.has("h2");
  refs.superposition.classList.toggle("active", hasHadamards);
  const hasArithmetic = state.placed.has("modexp1") && state.placed.has("modexp2");
  refs.formula.classList.toggle("active", hasArithmetic);
  const qftReady = state.placed.has("qft1") || state.placed.has("qft2");
  refs.qftLab.classList.toggle("ready", qftReady);
}

function educationalError(id, expected) {
  const moving = componentFor(id);
  const target = componentFor(expected);
  if (moving.kind === "qft" && !state.placed.has("modexp1")) {
    return "QFT comes after arithmetic: first encode the modular-product fibers.";
  }
  if (moving.kind === "measure" && (!state.placed.has("qft1") || !state.placed.has("qft2"))) {
    return "Measure after the inverse QFT has converted phase structure into sample coordinates.";
  }
  if (moving.kind === "arithmetic" && target?.kind === "qft") {
    return "This modular block acts on the shared result register, before Fourier sampling.";
  }
  return moving.label + " belongs in its matching " + (target?.label || "circuit") + " position.";
}

function explainUnavailable(id) {
  const current = componentFor(currentComponentId());
  if (state.mode === "guided" && current) {
    showToast("Guided order: place " + current.label + " next.", "info");
    showExplanation(current.id);
  }
}

function setMode(mode) {
  state.mode = mode;
  refs.guidedMode.classList.toggle("active", mode === "guided");
  refs.challengeMode.classList.toggle("active", mode === "challenge");
  refs.guidedMode.setAttribute("aria-pressed", String(mode === "guided"));
  refs.challengeMode.setAttribute("aria-pressed", String(mode === "challenge"));
  refs.modeHelp.textContent =
    mode === "guided"
      ? "Guided mode unlocks one verified component at a time."
      : "All unplaced pieces are active. Incorrect drops explain the dependency.";
  updateAvailability();
  showToast(mode === "guided" ? "Guided build enabled." : "Challenge mode enabled.", "info");
}

function renderPhaseGates() {
  refs.phaseGates.innerHTML = "";
  for (let register = 1; register <= 2; register += 1) {
    for (let separation = 1; separation <= 4; separation += 1) {
      const pairCount = 5 - separation;
      for (let pair = 0; pair < pairCount; pair += 1) {
        const dot = document.createElement("span");
        dot.className = "phase-dot";
        dot.dataset.separation = String(separation);
        dot.title = "x" + register + " controlled phase · qubit separation " + separation;
        refs.phaseGates.append(dot);
      }
    }
  }
  updateQftPreset("exact", { announce: false });
}

function updateQftPreset(name, options = {}) {
  const preset = state.data.qftPresets[name];
  if (!preset) return;
  state.qftPreset = name;
  $$(".qft-option").forEach((button) => {
    const active = button.dataset.preset === name;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  $$(".phase-dot", refs.phaseGates).forEach((dot) => {
    dot.classList.toggle("omitted", Number(dot.dataset.separation) > preset.cutoff);
  });
  refs.cpRemoved.textContent = String(preset.controlledPhasesRemoved);
  refs.cxRemoved.textContent = String(preset.qftOnlyCxRemoved);
  refs.certificateText.textContent = preset.certificate;
  refs.observedText.textContent = preset.observed;
  refs.evidenceScope.textContent =
    preset.scope + " QFT-only depth saved: " + preset.qftOnlyDepthRemoved + ".";
  refs.qftLab.dataset.preset = name;
  ["qft1", "qft2"].forEach((id) => {
    const slot = slotFor(id);
    const label = $(".placed-label", slot);
    if (label) label.textContent = name === "exact" ? "Exact inverse QFT" : preset.label;
  });
  if (options.announce !== false) {
    showToast(
      preset.label + ": " + preset.controlledPhasesRemoved + " phases and " +
      preset.qftOnlyCxRemoved + " QFT-only CX removed.",
      "info"
    );
  }
}

function completeCircuit() {
  if (state.completed) return;
  state.completed = true;
  refs.workspace.classList.add("circuit-complete");
  refs.cameraStage.classList.add("circuit-complete");
  updateStageProgress("Lattice recovery");
  window.setTimeout(() => {
    if (state.autoplayRun && document.body.classList.contains("presenting")) return;
    if (typeof refs.dialog.showModal === "function") refs.dialog.showModal();
    else refs.dialog.setAttribute("open", "");
  }, 850);
}

async function runRecovery(options = {}) {
  if (state.recoveryRunning) return;
  state.recoveryRunning = true;
  if (state.qftPreset !== state.data.successfulReplay.preset) {
    updateQftPreset(state.data.successfulReplay.preset, { announce: false });
    showToast("Switching to the pinned omit-one-layer replay used by this animation.", "info");
  }
  if (refs.dialog.open) refs.dialog.close();
  refs.postProcessing.classList.add("running");
  refs.factorReveal.classList.remove("revealed");
  refs.sampleStream.innerHTML =
    '<span class="stream-label">Fixed replay · model A · omit 1 · seed 2026091301</span>';
  $$(".pipeline-step").forEach((step) => step.classList.remove("active", "complete"));

  if (!options.noScroll) {
    refs.postProcessing.scrollIntoView({ behavior: "smooth", block: "center" });
    await delay(450);
  }

  for (let index = 0; index < state.data.successfulReplay.samples.length; index += 1) {
    const sample = state.data.successfulReplay.samples[index];
    const card = document.createElement("span");
    card.className = "sample-card";
    card.innerHTML =
      "<strong>(" + sample[0] + ", " + sample[1] + ")</strong><small>execution " + (index + 1) + "</small>";
    refs.sampleStream.append(card);
    window.requestAnimationFrame(() => card.classList.add("visible"));
    await delay(options.fast ? 100 : 230);
  }

  const steps = $$(".pipeline-step", refs.pipeline);
  for (let index = 0; index < steps.length; index += 1) {
    if (index > 0) steps[index - 1].classList.add("complete");
    steps[index].classList.add("active");
    await delay(options.fast ? 270 : 700);
    steps[index].classList.add("complete");
  }
  refs.factorReveal.classList.add("revealed");
  refs.postProcessing.classList.add("recovered");
  showToast("Fixed replay recovered z=(3,−1), β=21, and factors 5 × 11.", "success");
  soundSuccess(true);
  state.recoveryRunning = false;
}

function showToast(message, type = "info") {
  window.clearTimeout(state.toastTimer);
  refs.toast.textContent = message;
  refs.toast.className = "toast visible " + type;
  state.toastTimer = window.setTimeout(() => {
    refs.toast.classList.remove("visible");
  }, 3200);
}

function soundSuccess(final = false) {
  try {
    state.audioContext = state.audioContext || new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = state.audioContext.createOscillator();
    const gain = state.audioContext.createGain();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(final ? 440 : 520, state.audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(
      final ? 880 : 680,
      state.audioContext.currentTime + (final ? 0.24 : 0.09)
    );
    gain.gain.setValueAtTime(0.0001, state.audioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.07, state.audioContext.currentTime + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, state.audioContext.currentTime + (final ? 0.3 : 0.13));
    oscillator.connect(gain).connect(state.audioContext.destination);
    oscillator.start();
    oscillator.stop(state.audioContext.currentTime + (final ? 0.31 : 0.14));
  } catch {
    // Sound is decorative; browser autoplay policies may suppress it.
  }
}

async function presentationAutoplay() {
  const runId = ++state.autoplayRun;
  resetDemo({ preserveRun: true, silent: true });
  document.body.classList.add("presenting");
  refs.autoplayButton.disabled = true;
  setMode("guided");
  showToast("Presentation autoplay: building the verified architecture.", "info");
  await delay(450);
  for (const id of state.data.buildOrder) {
    if (runId !== state.autoplayRun) return;
    if (id === "qft1") updateQftPreset("omit1", { announce: true });
    showExplanation(id);
    slotFor(id)?.classList.add("snap-target");
    await delay(220);
    slotFor(id)?.classList.remove("snap-target");
    placeComponent(id, { silent: true });
    await delay(310);
  }
  if (refs.dialog.open) refs.dialog.close();
  await delay(450);
  await runRecovery({ fast: true });
  document.body.classList.remove("presenting");
  refs.autoplayButton.disabled = false;
}

function resetDemo(options = {}) {
  if (!options.preserveRun) state.autoplayRun += 1;
  state.placed.clear();
  state.selectedId = null;
  state.completed = false;
  state.recoveryRunning = false;
  refs.workspace.classList.remove("circuit-complete");
  refs.cameraStage.classList.remove("circuit-complete");
  refs.postProcessing.classList.remove("running", "recovered");
  refs.factorReveal.classList.remove("revealed");
  refs.sampleStream.innerHTML = "";
  if (refs.dialog.open) refs.dialog.close();
  $$(".pipeline-step").forEach((step) => step.classList.remove("active", "complete"));
  state.data.components.forEach((component) => {
    const slot = slotFor(component.id);
    slot.classList.remove("filled", "snap-target", "wrong-target");
    const fallback = {
      x1: "register",
      x2: "register",
      h1: "prepare",
      h2: "prepare",
      result: "|y⟩ result",
      aux: "|aux⟩ work",
      modexp1: "arithmetic a₁",
      modexp2: "arithmetic a₂",
      qft1: "Fourier",
      qft2: "Fourier",
      measure1: "read",
      measure2: "read"
    };
    slot.innerHTML = "<span>" + fallback[component.id] + "</span>";
    slot.setAttribute("aria-label", "Slot for " + component.label);
  });
  updateQftPreset("exact", { announce: false });
  updateSpecialVisuals();
  updateAvailability();
  showExplanation(state.data.buildOrder[0]);
  if (!options.silent) showToast("Circuit reset.", "info");
}

async function toggleCamera() {
  if (state.cameraRunning) {
    await state.handTracker?.stop();
    state.cameraRunning = false;
    refs.cameraButton.classList.remove("active");
    refs.cameraStage.classList.remove("camera-active", "hand-active");
    refs.cameraPlaceholder.hidden = false;
    refs.cameraButtonLabel.textContent = "Start hand tracking";
    refs.cameraStatus.textContent = "Camera optional · mouse ready";
    refs.trackingFps.textContent = "— fps";
    refs.pinchState.textContent = "open hand";
    refs.handCursor.classList.remove("visible", "pinching");
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    showToast("Camera access needs localhost or HTTPS. Mouse and touch still work.", "error");
    return;
  }
  refs.cameraButton.disabled = true;
  refs.cameraButtonLabel.textContent = "Loading hand model…";
  refs.cameraStatus.textContent = "Requesting camera permission";

  try {
    state.handTracker = state.handTracker || new GestureHandTracker({
      video: refs.video,
      canvas: refs.handCanvas,
      interactionElement: $(".demo-shell"),
      onPointer: handleHandPointer,
      onPinchStart: beginHandDrag,
      onPinchMove: continueHandDrag,
      onPinchEnd: finishHandDrag,
      onStatus: handleHandStatus
    });
    await state.handTracker.start();
    state.cameraRunning = true;
    refs.cameraButton.classList.add("active");
    refs.cameraStage.classList.add("camera-active");
    refs.cameraPlaceholder.hidden = true;
    refs.cameraButtonLabel.textContent = "Stop hand tracking";
    refs.cameraStatus.textContent = "Camera live · show one hand";
    showToast("Hand tracking ready. Pinch a component, then release over its slot.", "success");
  } catch (error) {
    refs.cameraStatus.textContent = "Hand tracking unavailable · mouse ready";
    refs.cameraButtonLabel.textContent = "Retry hand tracking";
    showToast(error.message || "Could not start hand tracking. Mouse and touch still work.", "error");
  } finally {
    refs.cameraButton.disabled = false;
  }
}

function handleHandStatus(status) {
  if (status.message) refs.cameraStatus.textContent = status.message;
  if (Number.isFinite(status.fps)) refs.trackingFps.textContent = Math.round(status.fps) + " fps";
  refs.cameraStage.classList.toggle("hand-active", Boolean(status.handVisible));
  if (!status.handVisible) refs.handCursor.classList.remove("visible");
}

function handleHandPointer(pointer) {
  refs.handCursor.classList.add("visible");
  refs.handCursor.classList.toggle("pinching", pointer.isPinching);
  refs.handCursor.style.transform = "translate3d(" + pointer.x + "px," + pointer.y + "px,0)";
  refs.handCursor.style.setProperty("--pinch-progress", String(pointer.pinchProgress));
  refs.pinchState.textContent = pointer.isPinching
    ? "pinch closed"
    : pointer.pinchProgress > 0
      ? "hold pinch " + Math.round(pointer.pinchProgress * 100) + "%"
      : "open hand";
  if (state.drag?.source === "hand") {
    moveDragGhost(pointer.x, pointer.y);
    highlightNearestSlot(pointer.x, pointer.y);
  }
}

function closestAvailableComponent(x, y) {
  let result = null;
  let distance = 92;
  $$(".component-card", refs.palette).forEach((button) => {
    const id = button.dataset.componentId;
    if (!isComponentAvailable(id)) return;
    const rect = button.getBoundingClientRect();
    const cx = Math.max(rect.left, Math.min(x, rect.right));
    const cy = Math.max(rect.top, Math.min(y, rect.bottom));
    const d = Math.hypot(x - cx, y - cy);
    if (d < distance) {
      distance = d;
      result = id;
    }
  });
  return result;
}

function beginHandDrag(pointer) {
  const id =
    closestAvailableComponent(pointer.x, pointer.y) ||
    (state.mode === "guided" ? currentComponentId() : null);
  if (!id) {
    showToast("Pinch closer to an unlocked component card.", "info");
    return;
  }
  state.drag = { id, source: "hand" };
  showExplanation(id);
  showDragGhost(id, pointer.x, pointer.y);
}

function continueHandDrag(pointer) {
  if (!state.drag || state.drag.source !== "hand") return;
  moveDragGhost(pointer.x, pointer.y);
  highlightNearestSlot(pointer.x, pointer.y);
}

function finishHandDrag(pointer) {
  if (!state.drag || state.drag.source !== "hand") return;
  const id = state.drag.id;
  state.drag = null;
  hideDragGhost();
  clearSnapTargets();
  const slot = nearestSlot(pointer.x, pointer.y);
  if (slot) attemptPlace(id, slot);
  else showToast("Release closer to a circuit slot.", "info");
}

function bindEvents() {
  refs.guidedMode.addEventListener("click", () => setMode("guided"));
  refs.challengeMode.addEventListener("click", () => setMode("challenge"));
  refs.resetButton.addEventListener("click", () => resetDemo());
  refs.cameraButton.addEventListener("click", toggleCamera);
  refs.autoplayButton.addEventListener("click", presentationAutoplay);
  refs.runLatticeButton.addEventListener("click", () => runRecovery());
  refs.fullscreenButton.addEventListener("click", async () => {
    try {
      if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
      else await document.exitFullscreen();
    } catch {
      showToast("Fullscreen is unavailable in this browser.", "error");
    }
  });
  document.addEventListener("fullscreenchange", () => {
    refs.fullscreenButton.textContent = document.fullscreenElement ? "×" : "⛶";
    refs.fullscreenButton.title = document.fullscreenElement ? "Exit fullscreen" : "Enter fullscreen";
  });
  $$(".qft-option").forEach((button) => {
    button.addEventListener("click", () => updateQftPreset(button.dataset.preset));
  });
  $$(".circuit-slot", refs.board).forEach((slot) => {
    slot.addEventListener("click", () => {
      if (state.selectedId) attemptPlace(state.selectedId, slot);
      else {
        const id = slot.dataset.accepts;
        if (!state.placed.has(id)) showExplanation(id);
      }
    });
    slot.addEventListener("mouseenter", () => {
      const id = slot.dataset.accepts;
      if (!state.placed.has(id)) showExplanation(id);
    });
  });
  window.addEventListener("beforeunload", () => state.handTracker?.stop());
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.drag) cancelPointerDrag();
  });
}

async function init() {
  try {
    const response = await fetch("./demo-data.json");
    if (!response.ok) throw new Error("Could not load demo-data.json");
    state.data = await response.json();
    state.components = new Map(state.data.components.map((component) => [component.id, component]));
    renderPalette();
    renderPipeline();
    renderPhaseGates();
    bindEvents();
    resetDemo({ silent: true });
  } catch (error) {
    refs.prompt.textContent = "Demo data could not load";
    refs.palette.innerHTML =
      '<div class="load-error"><strong>Start the local server first.</strong>' +
      "<span>Run: python3 serve_demo.py</span></div>";
    showToast(error.message, "error");
  }
}

init();
