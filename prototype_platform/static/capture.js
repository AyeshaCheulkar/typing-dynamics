/* capture.js — the prototype's OWN keystroke logger + participant flow.
   Records keydown/keyup/paste with ms timestamps and caret position, in the exact
   event shape ../features.py expects. Independent of the Stage-1 logger.

   Flow: participant ID + choice of a happy/sad moment -> neutral warm-up (baseline)
   in the neutral theme -> the chosen moment in its mood theme -> (research mode only)
   ratings -> report. The page theme is the data-mood attribute on #calm. */

(function () {
  "use strict";

  var root = document.getElementById("calm");

  // --- Laptop/desktop-only check ------------------------------------------
  var isTouch = ("ontouchstart" in window) || navigator.maxTouchPoints > 0;
  var coarse = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
  if (isTouch || coarse) {
    document.getElementById("device-block").classList.remove("hidden");
  }

  var state = {
    code: "", lvl: null, taskId: "", difficulty: "", prompt: "",
    startedAt: 0, endedAt: 0, events: [], phase: "", baselineId: null
  };

  var panelStart = document.getElementById("panel-start");
  var panelChoose = document.getElementById("panel-choose");
  var panelWrite = document.getElementById("panel-write");
  var panelRate = document.getElementById("panel-rate");
  var editor = document.getElementById("editor");
  var wordcount = document.getElementById("wordcount");
  var finishBtn = document.getElementById("finish-btn");
  var finishLabel = document.getElementById("finish-label");
  var codeInput = document.getElementById("code");
  var continueBtn = document.getElementById("baseline-btn");
  var LEVELS = window.LEVELS || [];

  function levelById(id) {
    for (var i = 0; i < LEVELS.length; i++) if (LEVELS[i].id === id) return LEVELS[i];
    return null;
  }
  function now() { return Date.now() - state.startedAt; }
  function show(panel) {
    [panelStart, panelChoose, panelWrite, panelRate].forEach(function (p) {
      p.classList.toggle("hidden", p !== panel);
    });
    window.scrollTo(0, 0);
  }

  // --- Step 1: participant ID + choose a happy / sad moment ----------------
  var cards = document.querySelectorAll(".mood-card");
  var context = {};                       // typing skill + keyboard (both modes)
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
  document.querySelectorAll(".cm-ctx .seg").forEach(function (seg) { wireSeg(seg, context, refreshContinue); });
  function refreshContinue() {
    continueBtn.disabled = !((codeInput.value || "").trim() && state.lvl &&
                             context.typing_skill && context.keyboard);
  }
  cards.forEach(function (card) {
    card.addEventListener("click", function () {
      state.lvl = levelById(card.dataset.level);
      cards.forEach(function (c) { c.setAttribute("aria-checked", c === card ? "true" : "false"); });
      refreshContinue();
    });
  });
  codeInput.addEventListener("input", refreshContinue);

  function beginWriting() {
    state.events = [];
    editor.value = "";
    wordcount.textContent = "0";
    show(panelWrite);
    state.startedAt = Date.now();
    editor.focus();
  }

  // --- Step 2: neutral BASELINE warm-up (neutral theme, same prompt for all) -
  continueBtn.addEventListener("click", function () {
    var code = (codeInput.value || "").trim();
    if (!code || !state.lvl) return;
    state.code = code;
    state.phase = "baseline";
    state.baselineId = null;
    var v = (window.BASELINE.variations || [])[0];
    state.taskId = v.id;
    state.difficulty = window.BASELINE.difficulty;
    root.dataset.mood = "neutral";
    document.getElementById("level-label").textContent = "Warm-up";
    document.getElementById("prompt-text").textContent = v.prompt;
    editor.placeholder = "Start writing here…";
    finishLabel.textContent = "Finish warm-up";
    beginWriting();
  });

  // --- Step 3: the chosen moment, in its mood theme, with no specific prompt -
  document.getElementById("moment-btn").addEventListener("click", function () {
    var lvl = state.lvl;
    state.phase = "moment";
    state.taskId = lvl.variations[0].id;
    state.difficulty = lvl.difficulty;
    root.dataset.mood = lvl.id;
    document.getElementById("level-label").textContent = lvl.title;
    document.getElementById("prompt-text").textContent = lvl.free_prompt;
    editor.placeholder = "Write about whatever comes to mind…";
    finishLabel.textContent = window.RESEARCH_MODE ? "Finish and rate how it felt" : "Finish and see my report";
    beginWriting();
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

  function failBack(msg) {
    finishBtn.disabled = false;
    alert(msg);
  }

  // --- Finish: warm-up -> hand-over; moment -> (ratings ->) report ----------
  finishBtn.addEventListener("click", function () {
    if (editor.value.trim().length < 20) {
      if (!confirm("That's quite short. Finish anyway?")) return;
    }
    state.endedAt = Date.now();
    finishBtn.disabled = true;

    if (state.phase === "baseline") {
      postSession({}).then(function (res) {
        finishBtn.disabled = false;
        if (!res.ok) { return failBack("Could not save the warm-up: " + (res.error || "error")); }
        state.baselineId = res.session_id;
        var lvl = state.lvl;
        root.dataset.mood = lvl.id;                 // the page takes on the chosen mood
        document.getElementById("ready-title").textContent = lvl.ready_title;
        document.getElementById("ready-text").textContent = lvl.ready_text;
        show(panelChoose);
      }).catch(function () { failBack("Network error. Please try again."); });
      return;
    }

    if (!window.RESEARCH_MODE) {                    // label-free participant mode
      postSession({ baseline_id: state.baselineId }).then(function (res) {
        if (res.ok) { window.location.href = res.report_url; }
        else { failBack("Could not save: " + (res.error || "error")); }
      }).catch(function () { failBack("Network error. Please try again."); });
      return;
    }
    finishBtn.disabled = false;
    show(panelRate);
  });

  // --- Research mode: ratings (effort, mood, focus, stress) + submit --------
  var submitBtn = document.getElementById("submit-btn");
  var ratings = {};
  var KEYS = ["effort", "mood", "focus", "stress", "relive", "arousal", "wander"];
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
      self_wander: ratings.wander, interrupted: ratings.interrupted,
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
