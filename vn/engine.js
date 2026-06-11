/*
  The Cabin: First Night — visual novel engine (POC).

  Runs an authored, braided scene graph (see story.js). Hidden state
  (fear / attention / anchor) is mutated by choices and surfaced
  through atmosphere and sound — never as a meter. The Lyer is never named in
  player-facing text; it is presence and attention only.

  AI hook (deliberately empty in this POC): the design doc calls for an
  "AI-disturbed surface" — authored plot, authored scenes, authored
  choices, AI only allowed to disturb wording at high fear. The seam is
  `disturb(text, state)` below; right now it returns text unchanged.
*/

(function () {
  "use strict";

  // --- Hidden state --------------------------------------------------
  const START_STATE = { fear: 0, attention: 0, anchor: 100, flags: {} };
  let state = structuredClone(START_STATE);

  const ENDING_ATTENTION = STORY.endingAttention || 30; // at or above: the cabin has noticed her
  const FEAR_SCALE = 45;
  const ATTENTION_SCALE = 50;

  const clamp = (n) => Math.max(0, Math.min(100, n));
  const clampUnit = (n) => Math.max(0, Math.min(1, n));

  function applyEffects(effects) {
    if (!effects) return;
    for (const key of ["fear", "attention", "anchor"]) {
      if (key in effects) state[key] = clamp(state[key] + effects[key]);
    }
  }

  // Authored surface only, for now. This is where a fear-scaled AI pass
  // would later be allowed to perturb wording — and nothing else.
  function disturb(text /*, state */) { return text; }

  // --- Elements ------------------------------------------------------
  const stage = document.getElementById("stage");
  const plateLayer = document.getElementById("plate-layer");
  const dialogue = document.getElementById("dialogue");
  const textEl = document.getElementById("text");
  const choicesEl = document.getElementById("choices");
  const continueHint = document.getElementById("continue-hint");
  const card = document.getElementById("center-card");
  const debugEl = document.getElementById("debug");
  const muteToggle = document.getElementById("mute-toggle");

  let revealTimers = [];
  let advance = null;    // pending continue handler
  let revealing = false; // true while paragraphs are still fading in
  let current = null;    // current scene id
  let debugOn = new URLSearchParams(location.search).has("debug");
  const reduceMotionQuery = globalThis.matchMedia
    ? globalThis.matchMedia("(prefers-reduced-motion: reduce)")
    : null;

  function prefersReducedMotion() {
    return !!(reduceMotionQuery && reduceMotionQuery.matches);
  }

  // --- Sound ---------------------------------------------------------
  let audioCtx = null;
  let masterGain = null;
  let roomToneGain = null;
  let muted = false;

  function ensureAudio() {
    if (audioCtx) return audioCtx;
    const AudioContext = globalThis.AudioContext || globalThis.webkitAudioContext;
    if (!AudioContext) return null;

    audioCtx = new AudioContext();
    const noise = audioCtx.createBuffer(1, audioCtx.sampleRate * 3, audioCtx.sampleRate);
    const samples = noise.getChannelData(0);
    let last = 0;
    for (let i = 0; i < samples.length; i++) {
      last = last * 0.985 + (Math.random() * 2 - 1) * 0.015;
      samples[i] = last;
    }

    const source = audioCtx.createBufferSource();
    const filter = audioCtx.createBiquadFilter();
    masterGain = audioCtx.createGain();
    roomToneGain = audioCtx.createGain();
    source.buffer = noise;
    source.loop = true;
    filter.type = "lowpass";
    filter.frequency.value = 360;
    masterGain.gain.value = muted ? 0 : 1;
    roomToneGain.gain.value = 0;
    source.connect(filter).connect(roomToneGain).connect(masterGain).connect(audioCtx.destination);
    source.start();
    return audioCtx;
  }

  function unlockAudio() {
    const ctx = ensureAudio();
    if (ctx && ctx.state === "suspended") void ctx.resume();
    updateAudio();
  }

  function updateAudio() {
    if (!audioCtx || !roomToneGain) return;
    const visualFear = clampUnit(state.fear / FEAR_SCALE);
    const target = muted ? 0 : 0.012 + visualFear * 0.055;
    roomToneGain.gain.cancelScheduledValues(audioCtx.currentTime);
    roomToneGain.gain.linearRampToValueAtTime(target, audioCtx.currentTime + 1.4);
  }

  function triggerScrape() {
    const ctx = ensureAudio();
    if (!ctx || muted) return;

    const duration = 1.15;
    const scrape = ctx.createBuffer(1, Math.floor(ctx.sampleRate * duration), ctx.sampleRate);
    const samples = scrape.getChannelData(0);
    for (let i = 0; i < samples.length; i++) {
      const t = i / samples.length;
      const grit = Math.random() * 2 - 1;
      samples[i] = grit * Math.sin(t * Math.PI) * (1 - t * 0.35);
    }

    const source = ctx.createBufferSource();
    const filter = ctx.createBiquadFilter();
    const gain = ctx.createGain();
    source.buffer = scrape;
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(210, ctx.currentTime);
    filter.frequency.linearRampToValueAtTime(95, ctx.currentTime + duration);
    filter.Q.value = 1.2;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.08);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
    source.connect(filter).connect(gain).connect(masterGain);
    source.start();
  }

  function playSceneCue(cue) {
    if (cue === "scrape") triggerScrape();
  }

  function setMuted(next) {
    muted = next;
    muteToggle.classList.toggle("muted", muted);
    muteToggle.setAttribute("aria-pressed", String(muted));
    muteToggle.textContent = muted ? "Sound" : "Silence";
    if (audioCtx && masterGain) {
      masterGain.gain.cancelScheduledValues(audioCtx.currentTime);
      masterGain.gain.setValueAtTime(muted ? 0 : 1, audioCtx.currentTime);
    }
    updateAudio();
  }

  function toggleMuted() {
    setMuted(!muted);
  }

  // --- Atmosphere ----------------------------------------------------
  function updateAtmosphere(scene = STORY.scenes[current]) {
    const atmosphere = resolve(scene && scene.atmosphere) || {};
    const visualFear = clampUnit(state.fear / FEAR_SCALE);
    const visualAttention = clampUnit(state.attention / ATTENTION_SCALE);

    stage.style.setProperty("--fear", visualFear.toFixed(3));
    stage.style.setProperty("--attention", visualAttention.toFixed(3));
    stage.style.setProperty("--scene-cold", clampUnit(atmosphere.cold || 0).toFixed(3));
    stage.style.setProperty("--scene-warm", clampUnit(atmosphere.warm || 0).toFixed(3));
    stage.style.setProperty("--scene-fog", clampUnit(atmosphere.fog || 0).toFixed(3));
    updateAudio();
    renderDebug();
  }

  function renderDebug() {
    debugEl.classList.toggle("hidden", !debugOn);
    if (!debugOn) return;
    const flags = Object.keys(state.flags).filter((k) => state.flags[k]);
    debugEl.textContent =
      `scene      ${current}\n` +
      `fear       ${state.fear}  (visual ${stage.style.getPropertyValue("--fear")}, scale ${FEAR_SCALE})\n` +
      `attention  ${state.attention}  (visual ${stage.style.getPropertyValue("--attention")}, ending >= ${ENDING_ATTENTION})\n` +
      `baseline   cold ${stage.style.getPropertyValue("--scene-cold")}  warm ${stage.style.getPropertyValue("--scene-warm")}  fog ${stage.style.getPropertyValue("--scene-fog")}\n` +
      `anchor     ${state.anchor}\n` +
      `flags      ${flags.join(", ") || "—"}`;
  }

  // --- SVG plate helpers ---------------------------------------------
  function svg(inner) {
    return `<svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">${inner}</svg>`;
  }

  // A forest mass: filled to the bottom, ragged along its top edge.
  // Layer several at different topY / fill for depth.
  function treeline(fill, topY, amp, segments, opacity) {
    let pts = "0,900";
    const step = 1600 / segments;
    for (let i = 0; i <= segments; i++) {
      const x = i * step;
      const y = topY + Math.sin(i * 1.7) * amp - ((i * 37) % (amp || 1));
      pts += ` ${x.toFixed(0)},${Math.max(0, y).toFixed(0)}`;
    }
    pts += " 1600,900";
    return `<polygon points="${pts}" fill="${fill}" opacity="${opacity == null ? 1 : opacity}"/>`;
  }

  // A single pale birch trunk rooted near (x, 900), leaning by `lean`
  // (positive leans right). `h` is height in canvas units.
  function birch(x, h, lean, ticks) {
    const topY = 900 - h;
    const topX = x + lean * h * 0.18;
    let out =
      `<polygon points="${x - 9},900 ${x + 9},900 ${topX + 5},${topY} ${topX - 5},${topY}" ` +
      `fill="#3a403f" opacity="0.42"/>`;
    // Birch bark: short, irregular dark dashes — not evenly spaced rungs.
    const n = ticks || 5;
    for (let i = 1; i <= n; i++) {
      const jitter = ((i * 53) % 11) / 11;            // 0..1 pseudo-random
      const ty = 900 - (h * (i + jitter * 0.6)) / (n + 1);
      const tx = x + lean * (900 - ty) * 0.18 + (jitter - 0.5) * 8;
      const w = 5 + jitter * 6;
      out += `<rect x="${tx - w / 2}" y="${ty}" width="${w}" height="2.5" fill="#0c0f0e" opacity="0.6"/>`;
    }
    return out;
  }

  // Each plate returns inline SVG. Gradients carry the mood; sparse
  // silhouettes carry the place. A scene's `image` (story.js) overrides it.
  const PLATES = {
    drive_dusk: () => svg(`
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#05070a"/>
          <stop offset="0.55" stop-color="#0a0f13"/>
          <stop offset="0.82" stop-color="#121a1a"/>
          <stop offset="1" stop-color="#0a0e0e"/>
        </linearGradient>
        <radialGradient id="win" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stop-color="#8a6635"/>
          <stop offset="1" stop-color="transparent"/>
        </radialGradient>
      </defs>
      <rect width="1600" height="900" fill="url(#sky)"/>
      ${treeline("#070c0e", 470, 34, 26, 0.92)}
      <!-- cabin, distant and small, faint warm window -->
      <ellipse cx="800" cy="520" rx="64" ry="40" fill="url(#win)" opacity="0.5"/>
      <rect x="762" y="494" width="76" height="56" fill="#0b0d0c"/>
      <polygon points="754,494 800,468 846,494" fill="#080a09"/>
      <rect x="792" y="514" width="13" height="16" fill="#9a7440" opacity="0.9"/>
      <!-- gravel drive receding toward the cabin -->
      <polygon points="650,900 950,900 834,552 774,552" fill="#111514" opacity="0.85"/>
      <!-- near birches, leaning in to frame -->
      ${birch(150, 540, 0.7, 6)}
      ${birch(1460, 470, -0.9, 6)}
      ${birch(330, 360, 0.5, 5)}
      ${treeline("#03060a", 720, 22, 8, 0.9)}
    `),

    cabin_interior_dark: () => svg(`
      <defs>
        <radialGradient id="winlt" cx="0.5" cy="0.5" r="0.6">
          <stop offset="0" stop-color="#1d2730"/>
          <stop offset="1" stop-color="transparent"/>
        </radialGradient>
      </defs>
      <rect width="1600" height="900" fill="#050606"/>
      <!-- cold light through the little window, upper right -->
      <ellipse cx="1180" cy="300" rx="300" ry="240" fill="url(#winlt)" opacity="0.7"/>
      <rect x="1090" y="190" width="170" height="210" fill="#0c1419" opacity="0.9"/>
      <rect x="1172" y="190" width="6" height="210" fill="#1a2730"/>
      <rect x="1090" y="292" width="170" height="6" fill="#1a2730"/>
      <!-- table + sink as faint shapes -->
      <rect x="540" y="560" width="360" height="28" fill="#0a0c0c"/>
      <rect x="600" y="586" width="22" height="150" fill="#080a0a"/>
      <rect x="818" y="586" width="22" height="150" fill="#080a0a"/>
      <rect x="120" y="540" width="220" height="70" fill="#090b0b"/>
    `),

    cabin_interior_stove: () => svg(`
      <defs>
        <radialGradient id="fire" cx="0.5" cy="0.6" r="0.6">
          <stop offset="0" stop-color="#b9772f"/>
          <stop offset="0.4" stop-color="#6b3f17"/>
          <stop offset="1" stop-color="transparent"/>
        </radialGradient>
        <radialGradient id="winblk" cx="0.5" cy="0.5" r="0.6">
          <stop offset="0" stop-color="#0a1116"/>
          <stop offset="1" stop-color="transparent"/>
        </radialGradient>
      </defs>
      <rect width="1600" height="900" fill="#070504"/>
      <!-- firelight, low and warm, lower left -->
      <ellipse class="fire-glow" cx="430" cy="650" rx="540" ry="450" fill="url(#fire)" opacity="0.7"/>
      <!-- stove body -->
      <rect x="330" y="600" width="200" height="230" rx="8" fill="#100b07"/>
      <ellipse cx="430" cy="700" rx="58" ry="34" fill="#c8812f" opacity="0.9"/>
      <!-- black-mirror window, upper right -->
      <ellipse cx="1200" cy="300" rx="260" ry="200" fill="url(#winblk)" opacity="0.8"/>
      <rect x="1100" y="200" width="180" height="200" fill="#05080a"/>
      <rect x="1188" y="200" width="6" height="200" fill="#161f24"/>
      <!-- long shadow thrown away from the fire -->
      <polygon points="540,820 980,900 1180,900 720,720" fill="#000" opacity="0.4"/>
    `),

    window_night: () => svg(`
      <defs>
        <linearGradient id="out" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#0a1016"/>
          <stop offset="1" stop-color="#070b0c"/>
        </linearGradient>
      </defs>
      <rect width="1600" height="900" fill="#040506"/>
      <rect x="260" y="120" width="1080" height="700" fill="url(#out)"/>
      ${treeline("#060b0d", 560, 30, 22, 0.95)}
      ${birch(520, 360, 0.3, 7)}
      ${birch(980, 380, -0.3, 7)}
      <!-- wall masks around the window so the forest stays inside it -->
      <rect x="0" y="0" width="1600" height="120" fill="#06080a"/>
      <rect x="0" y="820" width="1600" height="80" fill="#06080a"/>
      <rect x="0" y="0" width="260" height="900" fill="#06080a"/>
      <rect x="1340" y="0" width="260" height="900" fill="#06080a"/>
      <!-- frame -->
      <rect x="260" y="120" width="1080" height="700" fill="none" stroke="#0c0f0f" stroke-width="40"/>
      <rect x="794" y="120" width="12" height="700" fill="#0c0f0f"/>
      <rect x="260" y="464" width="1080" height="12" fill="#0c0f0f"/>
    `),

    consequence_quiet: () => svg(`
      <defs>
        <linearGradient id="dawn" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#0c1013"/>
          <stop offset="0.7" stop-color="#161c1f"/>
          <stop offset="1" stop-color="#0c1011"/>
        </linearGradient>
      </defs>
      <rect width="1600" height="900" fill="url(#dawn)"/>
      <!-- grey morning at the window, no warmth -->
      <rect x="1080" y="170" width="190" height="240" fill="#2a343a" opacity="0.55"/>
      <rect x="1170" y="170" width="6" height="240" fill="#3a464c"/>
      <rect x="1080" y="282" width="190" height="6" fill="#3a464c"/>
      <rect x="540" y="560" width="360" height="28" fill="#0c0f0f"/>
      <rect x="320" y="600" width="200" height="230" rx="8" fill="#0c0d0d"/>
    `),

    consequence_wrong: () => svg(`
      <defs>
        <linearGradient id="wrong" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#04060a"/>
          <stop offset="1" stop-color="#070a09"/>
        </linearGradient>
      </defs>
      <rect width="1600" height="900" fill="url(#wrong)"/>
      <!-- the forest pressed up against the frame, far too close -->
      ${treeline("#03050a", 300, 48, 22, 0.96)}
      ${birch(140, 720, 1.4, 5)}
      ${birch(1480, 700, -1.4, 5)}
      <!-- window that should not open onto this -->
      <rect x="1060" y="150" width="210" height="280" fill="#070d0e"/>
      ${birch(1120, 250, 1.0, 4)}
      <rect x="1060" y="150" width="210" height="280" fill="none" stroke="#0a0e0e" stroke-width="28"/>
    `),
  };

  function setBackground(bg) {
    const plate = document.createElement("div");
    plate.className = "plate";
    const type = bg && bg.type;
    if (type) {
      plate.dataset.type = type;
      plate.classList.add(`plate-${type}`);
    }
    if (type && PLATES[type]) plate.innerHTML = PLATES[type](bg);
    if (bg && bg.image) {
      // Try the named asset; swap it in if it loads, else keep the plate.
      const probe = new Image();
      probe.onload = () => {
        plate.innerHTML = "";
        plate.style.backgroundImage = `url("${bg.image}")`;
      };
      probe.src = bg.image;
    }
    plateLayer.appendChild(plate);
    void plate.offsetWidth; // force reflow so the crossfade fires
    plate.classList.add("show");

    const plates = plateLayer.querySelectorAll(".plate");
    if (plates.length > 1) {
      for (let i = 0; i < plates.length - 1; i++) {
        const old = plates[i];
        old.classList.remove("show");
        setTimeout(() => old.remove(), 2000);
      }
    }
  }

  // --- Scene running -------------------------------------------------
  const resolve = (v) => (typeof v === "function" ? v(state) : v);
  const clearTimers = () => { revealTimers.forEach(clearTimeout); revealTimers = []; };

  function runScene(id) {
    const scene = STORY.scenes[id];
    if (!scene) { console.error("Unknown scene:", id); return; }
    current = id;

    clearTimers();
    advance = null;
    revealing = false;
    choicesEl.innerHTML = "";
    continueHint.classList.add("hidden");

    setBackground(resolve(scene.bg));
    updateAtmosphere(scene);
    playSceneCue(resolve(scene.sound));

    if (scene.kind === "title") return showTitle(scene);
    if (scene.kind === "ending") return showEnding(scene);

    card.classList.add("hidden");
    dialogue.classList.remove("hidden");

    const paragraphs = resolve(scene.text) || [];
    textEl.innerHTML = "";
    const nodes = paragraphs.map((p) => {
      const el = document.createElement("p");
      el.innerHTML = disturb(p, state);
      textEl.appendChild(el);
      return el;
    });

    if (prefersReducedMotion()) {
      nodes.forEach((el) => el.classList.add("in"));
      showInteractions(scene);
      return;
    }

    revealing = true;
    let t = 350;
    nodes.forEach((el, i) => {
      revealTimers.push(setTimeout(() => el.classList.add("in"), t));
      t += i === 0 ? 900 : 1150;
    });
    revealTimers.push(setTimeout(() => { revealing = false; showInteractions(scene); }, t + 250));
  }

  function showAllNow(scene) {
    clearTimers();
    revealing = false;
    textEl.querySelectorAll("p").forEach((p) => p.classList.add("in"));
    showInteractions(scene);
  }

  function showInteractions(scene) {
    if (scene.choices) {
      const choices = scene.choices.filter((c) => (c.show ? c.show(state) : true));
      choices.forEach((c, i) => {
        const btn = document.createElement("button");
        btn.className = "choice";
        btn.innerHTML = disturb(c.label, state);
        btn.addEventListener("click", () => {
          applyEffects(c.effects);
          if (c.set) Object.assign(state.flags, c.set);
          runScene(resolve(c.goto));
        });
        choicesEl.appendChild(btn);
        if (prefersReducedMotion()) {
          btn.classList.add("in");
        } else {
          revealTimers.push(setTimeout(() => btn.classList.add("in"), 200 + i * 220));
        }
      });
    } else if (scene.next) {
      continueHint.classList.remove("hidden");
      advance = () => runScene(resolve(scene.next));
    }
  }

  // --- Title and endings --------------------------------------------
  function showTitle(scene) {
    dialogue.classList.add("hidden");
    card.className = "";
    card.innerHTML =
      `<div class="kicker">A short visual novel in the same world</div>` +
      `<h1>${scene.titleText}</h1>` +
      `<h2>${scene.subtitle}</h2>` +
      `<div class="blurb">${scene.blurb}</div>` +
      `<button class="enter">Begin</button>`;
    void card.offsetWidth;
    card.classList.add("in");
    card.querySelector(".enter").addEventListener("click", () => {
      state = structuredClone(START_STATE);
      unlockAudio();
      runScene(scene.begin);
    });
  }

  function showEnding(scene) {
    dialogue.classList.add("hidden");
    const title = resolve(scene.title);
    const lines = resolve(scene.text) || [];
    card.className = "";
    card.innerHTML =
      `<div class="kicker">${title}</div>` +
      `<div class="blurb" style="max-width:34rem;margin-top:2.2rem">${lines.join("\n\n")}</div>` +
      `<button class="enter">Again</button>`;
    void card.offsetWidth;
    card.classList.add("in");
    card.querySelector(".enter").addEventListener("click", () => {
      state = structuredClone(START_STATE);
      runScene(STORY.start);
    });
  }

  // --- Input ---------------------------------------------------------
  function handleAdvance() {
    if (revealing) { showAllNow(STORY.scenes[current]); return; }
    if (advance) { const go = advance; advance = null; go(); }
  }

  document.addEventListener("click", (ev) => {
    if (
      ev.target.closest &&
      (ev.target.closest(".choice") || ev.target.closest(".enter") || ev.target.closest("#mute-toggle"))
    ) return;
    handleAdvance();
  });
  document.addEventListener("keydown", (ev) => {
    if (
      ev.target.closest &&
      (ev.target.closest(".choice") || ev.target.closest(".enter") || ev.target.closest("#mute-toggle"))
    ) return;
    if (ev.key === "d" || ev.key === "D") { debugOn = !debugOn; renderDebug(); return; }
    if (ev.key === "m" || ev.key === "M") { toggleMuted(); return; }
    if (ev.key === " " || ev.key === "Enter") { ev.preventDefault(); handleAdvance(); }
  });
  muteToggle.addEventListener("click", toggleMuted);

  // --- Boot ----------------------------------------------------------
  setMuted(false);
  runScene(STORY.start);
})();
