/*
 * logger.js — keystroke capture for the Typing Dynamics platform (Stage 1).
 *
 * Design notes:
 *  - Timing uses performance.now(): a high-resolution monotonic clock that is
 *    NOT affected by the user changing their system time. We store each event
 *    as milliseconds since the session started (t0).
 *  - We capture keydown AND keyup so Stage 2 can compute both inter-key timing
 *    (flight time) and per-key hold time (dwell time).
 *  - We capture caret position (selectionStart) so Stage 2 can distinguish
 *    appending at the end from editing in the middle (revision behaviour).
 *  - We capture paste events as an integrity flag; pasted text has no typing
 *    dynamics and would pollute the data.
 */

(function () {
    "use strict";

    // ---- Element references -------------------------------------------------
    const startScreen = document.getElementById("start-screen");
    const writeScreen = document.getElementById("write-screen");
    const rateScreen  = document.getElementById("rate-screen");
    const doneScreen  = document.getElementById("done-screen");

    const participantInput = document.getElementById("participant-id");
    const levelCards  = document.getElementById("level-cards");
    const shuffleBtn  = document.getElementById("shuffle-btn");
    const previewPrompt = document.getElementById("preview-prompt");
    const previewImage  = document.getElementById("preview-image");
    const startBtn    = document.getElementById("start-btn");
    const startError  = document.getElementById("start-error");

    const taskPrompt  = document.getElementById("task-prompt");
    const taskImage   = document.getElementById("task-image");
    const editor      = document.getElementById("editor");
    const pasteWarning = document.getElementById("paste-warning");
    const liveStats   = document.getElementById("live-stats");
    const finishBtn   = document.getElementById("finish-btn");

    const ratingBox   = document.getElementById("rating");
    const submitBtn   = document.getElementById("submit-btn");
    const submitStatus = document.getElementById("submit-status");
    const anotherBtn  = document.getElementById("another-btn");

    // ---- Task pool (levels + prompt variations), injected by the server -----
    const LEVELS = JSON.parse(document.getElementById("levels-data").textContent);
    const LEVELS_BY_ID = Object.fromEntries(LEVELS.map(l => [l.id, l]));

    // ---- Session state ------------------------------------------------------
    let session = null;              // holds everything captured for the current task
    let selectedLevelId = LEVELS[0].id;
    let currentVariation = null;     // the variation currently previewed / assigned

    function show(screen) {
        [startScreen, writeScreen, rateScreen, doneScreen]
            .forEach(s => (s.hidden = s !== screen));
    }

    function wordCount(text) {
        const t = text.trim();
        return t ? t.split(/\s+/).length : 0;
    }

    // ---- Prompt selection & preview ----------------------------------------
    // Pick a random variation from the given level. Avoid repeating the current
    // one (unless the pool has only one) so "Shuffle" always feels like it did
    // something.
    function pickVariation(levelId) {
        const pool = LEVELS_BY_ID[levelId].variations;
        if (pool.length === 1) return pool[0];
        let v;
        do { v = pool[Math.floor(Math.random() * pool.length)]; }
        while (currentVariation && v.id === currentVariation.id);
        return v;
    }

    function renderPreview() {
        previewPrompt.textContent = currentVariation.prompt;
        if (currentVariation.image) {
            previewImage.src = "/static/images/" + currentVariation.image;
            previewImage.alt = currentVariation.image_alt || "Writing prompt image";
            previewImage.hidden = false;
        } else {
            previewImage.hidden = true;
            previewImage.removeAttribute("src");
        }
    }

    function selectLevel(levelId) {
        selectedLevelId = levelId;
        [...levelCards.children].forEach(c =>
            c.classList.toggle("selected", c.dataset.level === levelId));
        currentVariation = pickVariation(levelId);
        renderPreview();
    }

    levelCards.addEventListener("click", function (e) {
        const card = e.target.closest(".level-card");
        if (card) selectLevel(card.dataset.level);
    });

    shuffleBtn.addEventListener("click", function () {
        currentVariation = pickVariation(selectedLevelId);
        renderPreview();
    });

    // Show an initial prompt for the default level on page load.
    selectLevel(selectedLevelId);

    // Mirror the server's ID normalisation so the participant sees the exact
    // canonical form that will be stored (drop spaces, upper-case).
    participantInput.addEventListener("blur", function () {
        participantInput.value = participantInput.value.replace(/\s+/g, "").toUpperCase();
    });

    // ---- Start a session ----------------------------------------------------
    startBtn.addEventListener("click", function () {
        const pid = participantInput.value.trim();
        if (!pid) {
            startError.textContent = "Please enter your Participant ID.";
            startError.hidden = false;
            return;
        }
        startError.hidden = true;

        // Lock in the currently-previewed variation for this session.
        const v = currentVariation;
        session = {
            participant_id: pid,
            task_id: v.id,
            task_prompt: v.prompt,
            started_at: Date.now(),      // wall clock, for the record
            t0: performance.now(),       // monotonic origin for event timing
            events: [],                  // captured keystroke events
            paste_used: false,
            effort_rating: null,
        };

        taskPrompt.textContent = v.prompt;

        // Show the task image if this variation has one, otherwise hide it.
        if (v.image) {
            taskImage.src = "/static/images/" + v.image;
            taskImage.alt = v.image_alt || "Writing prompt image";
            taskImage.hidden = false;
        } else {
            taskImage.hidden = true;
            taskImage.removeAttribute("src");
        }

        editor.value = "";
        liveStats.textContent = "0 words · 0 characters";
        submitBtn.disabled = true;
        submitStatus.textContent = "";
        [...ratingBox.children].forEach(b => b.classList.remove("selected"));

        show(writeScreen);
        editor.focus();
    });

    // ---- Capture events on the editor --------------------------------------
    function record(type, key) {
        if (!session) return;
        session.events.push({
            type: type,
            key: key,
            t: Math.round(performance.now() - session.t0),
            caret: editor.selectionStart,        // start of caret/selection
            caretEnd: editor.selectionEnd,       // end of selection (== caret if none)
        });
    }

    editor.addEventListener("keydown", e => record("keydown", e.key));
    editor.addEventListener("keyup",   e => record("keyup",   e.key));

    // Pasting is DISABLED to protect data integrity: pasted text carries no
    // typing dynamics and would pollute the dataset. We block every paste
    // route (keyboard, right-click menu, drag-and-drop) but still log that an
    // attempt happened, so the researcher can see it in the data.
    let pasteWarnTimer = null;
    function flagBlockedPaste(kind, length) {
        if (!session) return;
        session.paste_used = true;                       // paste ATTEMPTED (blocked)
        record("paste", kind + (length != null ? ":" + length : ""));
        pasteWarning.hidden = false;
        if (pasteWarnTimer) clearTimeout(pasteWarnTimer);
        pasteWarnTimer = setTimeout(function () { pasteWarning.hidden = true; }, 2800);
    }

    editor.addEventListener("paste", function (e) {
        e.preventDefault();                              // nothing is inserted
        const clip = e.clipboardData || window.clipboardData;
        const pasted = clip ? clip.getData("text") : "";
        flagBlockedPaste("blocked", pasted ? pasted.length : 0);
    });

    // Block dragging text into the editor (another way to bypass typing).
    editor.addEventListener("drop", function (e) {
        e.preventDefault();
        flagBlockedPaste("drop-blocked", null);
    });
    editor.addEventListener("dragover", function (e) { e.preventDefault(); });

    // Belt-and-suspenders: modern browsers report HOW text was inserted via
    // beforeinput.inputType. Blocking here catches paste/drop even on mobile
    // browsers where the classic "paste"/"drop" events don't always fire or
    // can't be cancelled. Normal typing (insertText) is untouched.
    editor.addEventListener("beforeinput", function (e) {
        if (e.inputType === "insertFromPaste" ||
            e.inputType === "insertFromPasteAsQuotation" ||
            e.inputType === "insertFromDrop") {
            e.preventDefault();
            flagBlockedPaste(e.inputType, null);
        }
    });

    editor.addEventListener("input", function () {
        liveStats.textContent =
            wordCount(editor.value) + " words · " + editor.value.length + " characters";
    });

    // ---- Finish writing -> effort rating -----------------------------------
    // Anti-empty guard only: a small word floor stops blank/accidental submits.
    // It is NOT a quality gate — anything from 20 words up is saved, and short
    // answers (20–49 words) are still flagged "too_short" for researcher review.
    const MIN_WORDS = 20;
    finishBtn.addEventListener("click", function () {
        if (wordCount(editor.value) < MIN_WORDS) {
            alert("Please write at least " + MIN_WORDS +
                  " words before finishing.");
            editor.focus();
            return;
        }
        session.ended_at = Date.now();
        session.final_text = editor.value;
        show(rateScreen);
    });

    // ---- Pick a rating ------------------------------------------------------
    ratingBox.addEventListener("click", function (e) {
        const btn = e.target.closest(".rate");
        if (!btn) return;
        [...ratingBox.children].forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        session.effort_rating = parseInt(btn.dataset.value, 10);
        submitBtn.disabled = false;
    });

    // ---- Submit to backend --------------------------------------------------
    submitBtn.addEventListener("click", async function () {
        submitBtn.disabled = true;
        submitStatus.textContent = "Saving…";

        const payload = {
            participant_id: session.participant_id,
            task_id: session.task_id,
            started_at: session.started_at,
            ended_at: session.ended_at,
            final_text: session.final_text,
            effort_rating: session.effort_rating,
            paste_used: session.paste_used,
            events: session.events,
        };

        try {
            const res = await fetch("/api/session", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (data.ok) {
                submitStatus.textContent = "";
                show(doneScreen);
            } else {
                submitStatus.textContent = "Error: " + data.error;
                submitBtn.disabled = false;
            }
        } catch (err) {
            submitStatus.textContent = "Network error — could not save. Try again.";
            submitBtn.disabled = false;
        }
    });

    // ---- Do another task ----------------------------------------------------
    anotherBtn.addEventListener("click", function () {
        participantInput.value = session ? session.participant_id : "";
        session = null;
        show(startScreen);
    });

})();
