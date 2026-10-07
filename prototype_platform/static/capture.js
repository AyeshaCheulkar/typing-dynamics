/* capture.js — the prototype's OWN keystroke logger + participant flow.
   Records keydown/keyup/paste with ms timestamps and caret position, in the exact
   event shape ../features.py expects. Independent of the Stage-1 logger.

   Flow: participant ID + typing context + choose a happy or sad moment -> write (page
   takes a warm or cool mood theme) -> short questions (focus, mood, mind-wandering, ...;
   plus perceived effort in research mode) -> report. */

(function () {
  "use strict";

  // --- Laptop/desktop-only check ------------------------------------------
  var isTouch = ("ontouchstart" in window) || navigator.maxTouchPoints > 0;
  var coarse = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
  if (isTouch || coarse) {
    document.getElementById("device-block").classList.remove("hidden");
  }

  var state = { code: "", taskId: "", difficulty: "", startedAt: 0, endedAt: 0, events: [] };
  var context = {};                       // typing skill + keyboard

  var panelStart = document.getElementById("panel-start");
  var panelWrite = document.getElementById("panel-write");
  var panelRate = document.getElementById("panel-rate");
  var editor = document.getElementById("editor");
  var wordcount = document.getElementById("wordcount");
  var finishBtn = document.getElementById("finish-btn");
  var startErr = document.getElementById("start-err");
  var LEVELS = window.LEVELS || [];

  function levelById(id) {
    for (var i = 0; i < LEVELS.length; i++) if (LEVELS[i].id === id) return LEVELS[i];
    return null;
  }
  function now() { return Date.now() - state.startedAt; }

  // generic segmented choice: stores the selected data-v under the group's data-key
  function wireSeg(seg, store, after) {
    seg.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        store[seg.dataset.key] = b.dataset.v;
        seg.querySelectorAll("button").forEach(function (x) {
          x.setAttribute("aria-checked", x === b ? "true" : "false");
        });
        if (after) after();
      });
    });
  }
  document.querySelectorAll("#panel-start .choice-seg").forEach(function (seg) {
    wireSeg(seg, context, function () { startErr.textContent = ""; });
  });

  // --- Start: choosing a moment begins writing directly --------------------
  document.querySelectorAll(".task-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var code = (document.getElementById("code").value || "").trim();
      if (!code) { startErr.textContent = "Please enter your participant ID first."; return; }
      if (!context.typing_skill || !context.keyboard) {
        startErr.textContent = "Please answer the two quick typing questions above."; return;
      }
      var lvl = levelById(btn.dataset.level);
      if (!lvl) return;
      state.code = code;
      state.taskId = lvl.variations[0].id;
      state.difficulty = lvl.difficulty;
      document.body.classList.remove("mood-happy", "mood-sad");
      document.body.classList.add("mood-" + lvl.id);         // warm or cool theme
      document.getElementById("level-label").textContent = lvl.title;
      document.getElementById("prompt-text").textContent = lvl.free_prompt;
      editor.placeholder = "Write about whatever comes to mind…";
      document.getElementById("finish-label").textContent = "Finish and answer a few questions";
      panelStart.classList.add("hidden");
      panelWrite.classList.remove("hidden");
      window.scrollTo(0, 0);
      state.events = [];
      state.startedAt = Date.now();
      editor.focus();
    });
  });

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

  // --- Saving --------------------------------------------------------------
  function postSession(extra) {
    var body = {
      participant_code: state.code, task_id: state.taskId, difficulty: state.difficulty,
      started_at: state.startedAt, ended_at: state.endedAt,
      final_text: editor.value, events: state.events,
      typing_skill: context.typing_skill, keyboard: context.keyboard
    };
    for (var k in extra) body[k] = extra[k];
    return fetch("/api/submit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json(); });
  }

  // --- Finish: participant mode saves and shows the report; research mode rates first
  finishBtn.addEventListener("click", function () {
    if (editor.value.trim().length < 20) {
      if (!confirm("That's quite short. Finish anyway?")) return;
    }
    state.endedAt = Date.now();
    panelWrite.classList.add("hidden");       // everyone answers the short questions next
    panelRate.classList.remove("hidden");
    window.scrollTo(0, 0);
  });

  // --- Short questions (everyone) + effort (research mode only), then submit --------------------------------------
  var submitBtn = document.getElementById("submit-btn");
  var ratings = {};
  var KEYS = ["mood", "focus", "stress", "relive", "arousal", "wander"];
  if (window.RESEARCH_MODE) KEYS.push("effort");     // perceived effort: research mode only
  function refreshSubmit() {
    submitBtn.disabled = !(KEYS.every(function (k) { return ratings[k]; }) && ratings.interrupted !== undefined);
  }
  wireSeg(document.getElementById("interrupted-seg"), ratings, refreshSubmit);
  document.querySelectorAll("#panel-rate .scale").forEach(function (scale) {
    scale.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        ratings[scale.dataset.key] = parseInt(b.dataset.v, 10);
        scale.querySelectorAll("button")
          .forEach(function (x) { x.classList.remove("sel"); });
        b.classList.add("sel");
        refreshSubmit();
      });
    });
  });

  submitBtn.addEventListener("click", function () {
    submitBtn.disabled = true;
    document.getElementById("submit-status").textContent = "Building your report…";
    postSession({
      self_rated_effort: ratings.effort, self_mood: ratings.mood,
      self_focus: ratings.focus, self_stress: ratings.stress,
      self_relive: ratings.relive, self_arousal: ratings.arousal,
      self_wander: ratings.wander, interrupted: ratings.interrupted
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
