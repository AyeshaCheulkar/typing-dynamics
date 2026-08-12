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
    document.querySelectorAll(".sess-row").forEach(function (row) {
        row.addEventListener("click", function (e) {
            // Don't toggle when the click was on the include/exclude button.
            if (e.target.closest(".incl-btn")) return;
            const detail = document.getElementById("detail-" + row.dataset.id);
            if (!detail) return;
            const open = detail.hidden === false;
            detail.hidden = open;
            row.classList.toggle("open", !open);
        });
    });

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
