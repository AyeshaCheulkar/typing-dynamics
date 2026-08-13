/*
 * admin.js — interactions for the researcher dashboard.
 *   1. Expand a session row to read the full response text + quality flags.
 *   2. Include / exclude a session from the ML dataset (persisted server-side).
 * Everything degrades gracefully: with JS off, all rows/data are still present.
 */
(function () {
    "use strict";

    const includedCount = document.getElementById("included-count");

    // ---- Expand / collapse a row to reveal the full response ---------------
    const PAUSE_MS = 1000;   // gap between keystrokes counted as a "pause"

    document.querySelectorAll(".sess-row").forEach(function (row) {
        row.addEventListener("click", function (e) {
            // Don't toggle when the click was on the include/exclude button.
            if (e.target.closest(".incl-btn")) return;
            const detail = document.getElementById("detail-" + row.dataset.id);
            if (!detail) return;
            const open = detail.hidden === false;
            detail.hidden = open;
            row.classList.toggle("open", !open);
            if (!open) {
                const view = detail.querySelector(".ks-view");
                if (view && view.dataset.loaded === "0") loadKeystrokes(view);
            }
        });
    });

    // ---- Load + render the raw keystroke timeline for a session ------------
    async function loadKeystrokes(view) {
        view.dataset.loaded = "1";
        view.innerHTML = '<span class="muted">Loading keystrokes…</span>';
        try {
            const res = await fetch("/api/session/" + view.dataset.id);
            const data = await res.json();
            const events = data.events || [];

            let keydowns = 0, deletions = 0, pastes = 0, pauses = 0, maxGap = 0;
            let lastT = null;
            const rows = [];
            for (const ev of events) {
                if (ev.event_type === "keydown") {
                    keydowns++;
                    const gap = lastT === null ? 0 : ev.t_ms - lastT;
                    if (lastT !== null && gap >= PAUSE_MS) { pauses++; if (gap > maxGap) maxGap = gap; }
                    const isDel = ev.key_value === "Backspace" || ev.key_value === "Delete";
                    if (isDel) deletions++;
                    const isRange = ev.selection_end != null && ev.selection_end !== ev.caret_pos;
                    rows.push(
                        '<tr class="' + (isDel ? "ks-del " : "") + (gap >= PAUSE_MS ? "ks-pause" : "") + '">' +
                        "<td>" + (ev.t_ms / 1000).toFixed(2) + "s</td>" +
                        "<td>" + (gap >= PAUSE_MS ? "⏸ " : "") + gap + " ms</td>" +
                        "<td>" + esc(ev.key_value) + (isRange ? ' <span class="ks-tag">selection</span>' : "") + "</td>" +
                        "<td>" + ev.caret_pos + "</td></tr>"
                    );
                    lastT = ev.t_ms;
                } else if (ev.event_type === "paste") {
                    pastes++;
                    rows.push('<tr class="ks-paste"><td>' + (ev.t_ms / 1000).toFixed(2) +
                        's</td><td>—</td><td>⚠ paste attempt (' + esc(ev.key_value) +
                        ')</td><td>—</td></tr>');
                }
            }

            const summary =
                '<div class="ks-stats">' +
                stat(keydowns, "keys pressed") +
                stat(deletions, "deletions (⌫/Del)") +
                stat(pauses, "pauses ≥1s") +
                stat((maxGap / 1000).toFixed(1) + "s", "longest pause") +
                stat(pastes, "paste attempts") +
                "</div>";

            const table = rows.length
                ? '<div class="ks-table-wrap"><table class="ks-table"><thead><tr>' +
                  "<th>Time</th><th>Gap</th><th>Key</th><th>Caret</th></tr></thead><tbody>" +
                  rows.join("") + "</tbody></table></div>"
                : '<span class="muted">No keystroke events recorded for this session.</span>';

            view.innerHTML = summary + table;
        } catch (err) {
            view.innerHTML = '<span class="muted">Could not load keystrokes.</span>';
            view.dataset.loaded = "0";
        }
    }

    function stat(value, label) {
        return '<span class="ks-stat"><b>' + value + '</b>' + label + "</span>";
    }
    function esc(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // ---- Include / exclude toggle ------------------------------------------
    document.querySelectorAll(".incl-btn").forEach(function (btn) {
        btn.addEventListener("click", async function (e) {
            e.stopPropagation();
            const id = btn.dataset.id;
            const makeIncluded = btn.classList.contains("off"); // toggling to?
            btn.disabled = true;

            try {
                const res = await fetch("/api/session/" + id + "/include", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ included: makeIncluded ? 1 : 0 }),
                });
                const data = await res.json();
                if (!data.ok) throw new Error(data.error || "failed");

                // Update button + row styling to reflect the new state.
                btn.classList.toggle("on", makeIncluded);
                btn.classList.toggle("off", !makeIncluded);
                btn.textContent = makeIncluded ? "✓ Included" : "Excluded";
                btn.setAttribute("aria-pressed", makeIncluded ? "true" : "false");
                const sessRow = document.querySelector('.sess-row[data-id="' + id + '"]');
                if (sessRow) sessRow.classList.toggle("excluded", !makeIncluded);

                // Keep the "In ML dataset" counter in sync live.
                if (includedCount) {
                    const m = includedCount.firstChild;
                    let n = parseInt(m.textContent, 10);
                    n += makeIncluded ? 1 : -1;
                    m.textContent = n;
                }
            } catch (err) {
                alert("Could not update this session. Please try again.");
            } finally {
                btn.disabled = false;
            }
        });
    });
})();
