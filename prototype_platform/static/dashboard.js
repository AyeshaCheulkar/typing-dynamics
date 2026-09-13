/* dashboard.js — KPI count-up, analytics charts, segmented controls, toggles,
   and the typing-timeline tooltip. Monochrome + restrained semantic accents. */
(function () {
  "use strict";
  var INK = "#2563eb", SELF = "#2563eb", EXP = "#d97706", GREY = "#c7d2ec",
      GRID = "#e6edfb", VIOLET = "#60a5fa", MEAS = "#0f9d6e", CYAN = "#3b82f6";
  if (window.Chart) {
    Chart.defaults.font.family = "Inter, system-ui, sans-serif";
    Chart.defaults.color = "#7286a6";
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.font = { family: "Space Grotesk", size: 11 };
  }
  function el(id) { return document.getElementById(id); }

  /* ---- KPI count-up ---- */
  document.querySelectorAll(".k-num[data-count]").forEach(function (n) {
    var target = parseFloat(n.dataset.count) || 0, dec = parseInt(n.dataset.dec || "0", 10);
    var t0 = null, dur = 900;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min((ts - t0) / dur, 1), e = 1 - Math.pow(1 - p, 3);
      n.textContent = (target * e).toFixed(dec);
      if (p < 1) requestAnimationFrame(step); else n.textContent = target.toFixed(dec);
    }
    requestAnimationFrame(step);
  });

  /* ---- Segmented control: card/table view toggle ---- */
  var vseg = el("view-seg");
  if (vseg) vseg.addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b) return;
    vseg.querySelectorAll("button").forEach(function (x) { x.classList.remove("on"); });
    b.classList.add("on");
    var v = b.dataset.v;
    if (el("view-cards")) el("view-cards").classList.toggle("hidden", v !== "cards");
    if (el("view-table")) el("view-table").classList.toggle("hidden", v !== "table");
  });

  /* ---- Timeline tooltip ---- */
  var tl = el("timeline");
  if (tl) {
    var tip = document.createElement("div"); tip.className = "tooltip";
    document.body.appendChild(tip);
    tl.addEventListener("mousemove", function (e) {
      var s = e.target.closest(".tl-seg");
      if (!s) { tip.classList.remove("show"); return; }
      tip.textContent = s.dataset.tip;
      tip.style.left = (e.clientX + 12) + "px";
      tip.style.top = (e.clientY - 34) + "px";
      tip.classList.add("show");
    });
    tl.addEventListener("mouseleave", function () { tip.classList.remove("show"); });
  }

  /* ================= OVERVIEW ================= */
  if (window.OVERVIEW) {
    var o = window.OVERVIEW;
    var AX = { speed: "Typing speed (chars/s)", pauses: "Pause time ratio",
               revisions: "Revisions per 100", time: "Writing time (s)" };
    var current = "speed";
    var primary = el("c-primary") && new Chart(el("c-primary"), {
      type: "scatter",
      data: { datasets: [{ label: "Session", data: o.feature_vs_effort[current],
        backgroundColor: INK, borderColor: INK, pointRadius: 6, pointHoverRadius: 8 }] },
      options: { scales: {
        x: { title: { display: true, text: "Self-rated effort (1–5)" }, min: 0.5, max: 5.5,
             ticks: { stepSize: 1 } },
        y: { title: { display: true, text: AX[current] } } },
        plugins: { legend: { display: false } } }
    });
    var fseg = el("feat-seg");
    if (fseg && primary) fseg.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      fseg.querySelectorAll("button").forEach(function (x) { x.classList.remove("on"); });
      b.classList.add("on"); current = b.dataset.k;
      primary.data.datasets[0].data = o.feature_vs_effort[current];
      primary.options.scales.y.title.text = AX[current];
      primary.update();
    });
    if (el("c-effort")) new Chart(el("c-effort"), {
      type: "bar",
      data: { labels: ["1", "2", "3", "4", "5"],
        datasets: [{ data: o.effort_dist, backgroundColor: INK, borderRadius: 6 }] },
      options: { plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });
  }

  /* ================= PARTICIPANT PROFILE ================= */
  if (window.PROFILE) {
    var pr = window.PROFILE;
    if (el("c-effort")) new Chart(el("c-effort"), {
      type: "line",
      data: { labels: pr.labels, datasets: [{ label: "Self-rated effort", data: pr.effort,
        borderColor: SELF, backgroundColor: SELF, tension: .3, pointRadius: 5 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { min: 0.5, max: 5.5 } } }
    });
    if (el("c-behaviour")) {
      var mx = function (a) { var m = Math.max.apply(null, a.concat([1])); return a.map(function (v) { return v / m; }); };
      new Chart(el("c-behaviour"), {
        type: "line",
        data: { labels: pr.labels, datasets: [
          { label: "Speed", data: mx(pr.speed), borderColor: INK, tension: .3 },
          { label: "Pauses", data: mx(pr.pauses), borderColor: EXP, tension: .3 },
          { label: "Revisions", data: mx(pr.revisions), borderColor: SELF, tension: .3, borderDash: [5, 4] } ] },
        options: { scales: { y: { min: 0, max: 1, title: { display: true, text: "relative to max" } } } }
      });
    }
  }
})();
