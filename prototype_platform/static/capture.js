/* capture.js — the prototype's OWN keystroke logger + participant flow.
   Records keydown/keyup/paste with ms timestamps and caret position, in the exact
   event shape ../features.py expects. Independent of the Stage-1 logger. */

(function () {
  "use strict";

  // --- Laptop/desktop-only check ------------------------------------------
  var isTouch = ("ontouchstart" in window) || navigator.maxTouchPoints > 0;
  var coarse = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
  if (isTouch || coarse) {
    document.getElementById("device-block").classList.remove("hidden");
  }

  var state = {
    code: "", taskId: "", difficulty: "", prompt: "",
    startedAt: 0, endedAt: 0, events: [], rating: null
  };

  var panelStart = document.getElementById("panel-start");
  var panelWrite = document.getElementById("panel-write");
  var panelRate = document.getElementById("panel-rate");
  var editor = document.getElementById("editor");
  var wordcount = document.getElementById("wordcount");

  // --- Task pools (from the server) + random / shuffle selection ----------
  var LEVELS = window.LEVELS || [];
  state.pool = [];        // variations for the chosen level
  state.varIndex = -1;    // index of the current variation

  function levelById(id) {
    for (var i = 0; i < LEVELS.length; i++) if (LEVELS[i].id === id) return LEVELS[i];
    return null;
  }
  function applyVariation(idx) {
    state.varIndex = idx;
    var v = state.pool[idx];
    state.taskId = v.id;
    state.prompt = v.prompt;
    document.getElementById("prompt-text").textContent = v.prompt;
  }
  function randomIndex(exclude) {
    if (state.pool.length <= 1) return 0;
    var i;
    do { i = Math.floor(Math.random() * state.pool.length); } while (i === exclude);
    return i;
  }

  // --- Step 1 -> 2: choose level, then a random prompt --------------------
  document.querySelectorAll(".task-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var code = (document.getElementById("code").value || "").trim();
      if (!code) { alert("Please enter a participant code first."); return; }
      var lvl = levelById(btn.dataset.level);
      if (!lvl) return;
      state.code = code;
      state.difficulty = btn.dataset.difficulty;
      state.pool = lvl.variations;
      document.getElementById("level-label").textContent =
        lvl.title + " · " + lvl.difficulty;
      applyVariation(randomIndex(-1));   // random prompt to start
      panelStart.classList.add("hidden");
      panelWrite.classList.remove("hidden");
      state.startedAt = Date.now();
      editor.focus();
    });
  });

  // Shuffle to a different prompt in the same level.
  var shuffleBtn = document.getElementById("shuffle-btn");
  if (shuffleBtn) shuffleBtn.addEventListener("click", function () {
    if (!state.pool.length) return;
    applyVariation(randomIndex(state.varIndex));
    if (editor.value.trim().length) {
      // if they had started, don't wipe silently — just refocus the editor
    }
    editor.focus();
  });

  function now() { return Date.now() - state.startedAt; }

  // --- Keystroke capture ---------------------------------------------------
  editor.addEventListener("keydown", function (e) {
    state.events.push({ type: "keydown", key: e.key, t: now(),
                        caret: editor.selectionStart, caretEnd: editor.selectionEnd });
  });
  editor.addEventListener("keyup", function (e) {
    state.events.push({ type: "keyup", key: e.key, t: now(),
                        caret: editor.selectionStart, caretEnd: editor.selectionEnd });
  });
  // Block paste to keep the typing record genuine; log the attempt.
  editor.addEventListener("paste", function (e) {
    e.preventDefault();
    state.events.push({ type: "paste", key: "blocked", t: now(),
                        caret: editor.selectionStart, caretEnd: editor.selectionEnd });
  });
  editor.addEventListener("input", function () {
    var w = editor.value.trim() ? editor.value.trim().split(/\s+/).length : 0;
    wordcount.textContent = w;
  });

  // --- Step 2 -> 3: finish -------------------------------------------------
  document.getElementById("finish-btn").addEventListener("click", function () {
    if (editor.value.trim().length < 20) {
      if (!confirm("That's quite short. Finish anyway?")) return;
    }
    state.endedAt = Date.now();
    panelWrite.classList.add("hidden");
    panelRate.classList.remove("hidden");
  });

  // --- Step 3: rating + submit --------------------------------------------
  var submitBtn = document.getElementById("submit-btn");
  document.querySelectorAll("#effort-scale button").forEach(function (b) {
    b.addEventListener("click", function () {
      state.rating = parseInt(b.dataset.v, 10);
      document.querySelectorAll("#effort-scale button")
        .forEach(function (x) { x.classList.remove("sel"); });
      b.classList.add("sel");
      submitBtn.disabled = false;
    });
  });

  submitBtn.addEventListener("click", function () {
    submitBtn.disabled = true;
    document.getElementById("submit-status").textContent = "Building your report…";
    fetch("/api/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        participant_code: state.code,
        task_id: state.taskId,
        difficulty: state.difficulty,
        started_at: state.startedAt,
        ended_at: state.endedAt,
        final_text: editor.value,
        self_rated_effort: state.rating,
        events: state.events
      })
    }).then(function (r) { return r.json(); }).then(function (res) {
      if (res.ok) { window.location.href = res.report_url; }
      else {
        document.getElementById("submit-status").textContent =
          "Error: " + (res.error || "could not save.");
        submitBtn.disabled = false;
      }
    }).catch(function () {
      document.getElementById("submit-status").textContent = "Network error.";
      submitBtn.disabled = false;
    });
  });
})();
