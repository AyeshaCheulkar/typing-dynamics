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
    startedAt: 0, endedAt: 0, events: [], phase: "", baselineId: null
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

  var panelChoose = document.getElementById("panel-choose");
  var shuffleBtn0 = document.getElementById("shuffle-btn");
  var finishLabel = document.getElementById("finish-label");

  function beginWriting() {
    state.events = [];
    editor.value = "";
    wordcount.textContent = "0";
    panelStart.classList.add("hidden");
    panelChoose.classList.add("hidden");
    panelWrite.classList.remove("hidden");
    state.startedAt = Date.now();
    editor.focus();
  }

  // --- Step 1: neutral BASELINE passage (same person, same prompt) --------
  document.getElementById("baseline-btn").addEventListener("click", function () {
    var code = (document.getElementById("code").value || "").trim();
    if (!code) { alert("Please enter a participant code first."); return; }
    state.code = code;
    state.phase = "baseline";
    state.baselineId = null;
    var v = (window.BASELINE.variations || [])[0];
    state.taskId = v.id;
    state.difficulty = window.BASELINE.difficulty;
    state.prompt = v.prompt;
    state.pool = [];
    document.getElementById("level-label").textContent = "Baseline passage · Step 1 of 2";
    document.getElementById("prompt-text").textContent = v.prompt;
    shuffleBtn0.classList.add("hidden");
    finishLabel.textContent = "Finish baseline →";
    beginWriting();
  });

  // --- Step 2: choose happy / sad moment, then a random prompt ------------
  document.querySelectorAll(".task-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var lvl = levelById(btn.dataset.level);
      if (!lvl) return;
      state.phase = "moment";
      state.difficulty = btn.dataset.difficulty;
      state.pool = lvl.variations;
      document.getElementById("level-label").textContent =
        lvl.title + " · Step 2 of 2";
      applyVariation(randomIndex(-1));   // random prompt to start
      shuffleBtn0.classList.remove("hidden");
      finishLabel.textContent = window.RESEARCH_MODE ? "Finish & rate how it felt →" : "Finish & see my report →";
      beginWriting();
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
  function postSession(extra) {
    var body = {
      participant_code: state.code, task_id: state.taskId, difficulty: state.difficulty,
      started_at: state.startedAt, ended_at: state.endedAt,
      final_text: editor.value, events: state.events
    };
    for (var k in extra) body[k] = extra[k];
    return fetch("/api/submit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json(); });
  }

  document.getElementById("finish-btn").addEventListener("click", function () {
    if (editor.value.trim().length < 20) {
      if (!confirm("That's quite short. Finish anyway?")) return;
    }
    state.endedAt = Date.now();
    if (state.phase === "baseline") {
      var btn = document.getElementById("finish-btn");
      btn.disabled = true;
      postSession({}).then(function (res) {
        btn.disabled = false;
        if (res.ok) {
          state.baselineId = res.session_id;
          panelWrite.classList.add("hidden");
          panelChoose.classList.remove("hidden");
        } else { alert("Could not save the baseline: " + (res.error || "error")); }
      }).catch(function () { btn.disabled = false; alert("Network error."); });
      return;
    }
    panelWrite.classList.add("hidden");
    if (!window.RESEARCH_MODE) {              // label-free participant mode: no ratings
      document.getElementById("finish-btn").disabled = true;
      postSession({ baseline_id: state.baselineId }).then(function (res) {
        if (res.ok) { window.location.href = res.report_url; }
        else { alert("Could not save: " + (res.error || "error")); panelWrite.classList.remove("hidden"); document.getElementById("finish-btn").disabled = false; }
      }).catch(function () { alert("Network error."); panelWrite.classList.remove("hidden"); document.getElementById("finish-btn").disabled = false; });
      return;
    }
    panelRate.classList.remove("hidden");
  });

  // --- Step 3: ratings (effort, mood, focus, stress) + submit --------------
  var submitBtn = document.getElementById("submit-btn");
  var ratings = {};
  var KEYS = ["effort", "mood", "focus", "stress"];
  document.querySelectorAll("#panel-rate .scale").forEach(function (scale) {
    scale.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        ratings[scale.dataset.key] = parseInt(b.dataset.v, 10);
        scale.querySelectorAll("button")
          .forEach(function (x) { x.classList.remove("sel"); });
        b.classList.add("sel");
        submitBtn.disabled = !KEYS.every(function (k) { return ratings[k]; });
      });
    });
  });

  submitBtn.addEventListener("click", function () {
    submitBtn.disabled = true;
    document.getElementById("submit-status").textContent = "Building your report…";
    postSession({
      self_rated_effort: ratings.effort, self_mood: ratings.mood,
      self_focus: ratings.focus, self_stress: ratings.stress,
      baseline_id: state.baselineId
    }).then(function (res) {
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
