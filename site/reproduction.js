/* Figure-reproduction page. Everything is drawn from assets/reproduction/data.json,
   which scripts/build_site_reproduction.py exports from the BioFigBench package. */
(() => {
  "use strict";

  const DATA_URL = "assets/reproduction/data.json";
  const IMG_ROOT = "assets/reproduction/img/";
  const AGENTS = [
    { key: "tissueagent", name: "TissueAgent" },
    { key: "spatialagent", name: "SpatialAgent" },
    { key: "biomni", name: "Biomni" },
  ];
  const METRICS = [
    { key: "ssim", label: "SSIM" },
    { key: "phash", label: "pHash" },
    { key: "orb", label: "ORB" },
  ];
  const STATUS = {
    success: ["Completed", "ok"],
    failure: ["Failed", "bad"],
    timeout: ["Timed out", "warn"],
    harness_error: ["Harness error", "bad"],
    pending: ["Not run", "idle"],
    running: ["Running", "idle"],
    unknown: ["Unknown", "idle"],
  };
  const SVG_NS = "http://www.w3.org/2000/svg";
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function svg(tag, attrs = {}, text) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (text != null) node.textContent = text;
    return node;
  }

  const fmt = (v, digits = 3) => (v == null ? "—" : v.toFixed(digits));
  const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

  function fmtTime(seconds) {
    if (seconds == null) return "—";
    if (seconds < 60) return `${Math.round(seconds)} s`;
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return `${minutes} min`;
    return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, "0")} min`;
  }

  function fmtDate(iso) {
    const d = new Date(iso);
    return Number.isNaN(d.getTime())
      ? ""
      : d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" });
  }

  /* ---- statistics (linear-interpolated quantiles, as numpy and matplotlib use) ---- */

  function quantile(sorted, q) {
    if (!sorted.length) return NaN;
    const pos = (sorted.length - 1) * q;
    const lo = Math.floor(pos);
    const hi = Math.ceil(pos);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
  }

  const median = (values) => quantile([...values].sort((a, b) => a - b), 0.5);
  const mean = (values) => values.reduce((s, v) => s + v, 0) / values.length;

  function boxStats(values) {
    const sorted = [...values].sort((a, b) => a - b);
    const q1 = quantile(sorted, 0.25);
    const med = quantile(sorted, 0.5);
    const q3 = quantile(sorted, 0.75);
    const iqr = q3 - q1;
    const inside = sorted.filter((v) => v >= q1 - 1.5 * iqr && v <= q3 + 1.5 * iqr);
    return {
      n: sorted.length,
      q1, med, q3,
      mean: mean(sorted),
      lo: inside[0],
      hi: inside[inside.length - 1],
      outliers: sorted.filter((v) => v < q1 - 1.5 * iqr || v > q3 + 1.5 * iqr),
    };
  }

  /* ---- tooltip ---- */

  const tip = $("[data-rp-tip]");

  function showTip(target, title, lines) {
    tip.replaceChildren(el("strong", null, title), ...lines.map((l) => el("span", null, l)));
    tip.hidden = false;
    const r = target.getBoundingClientRect();
    const t = tip.getBoundingClientRect();
    let x = r.left + r.width / 2 - t.width / 2;
    x = Math.max(8, Math.min(window.innerWidth - t.width - 8, x));
    let y = r.top - t.height - 8;
    if (y < 64) y = r.bottom + 8;
    tip.style.left = `${x}px`;
    tip.style.top = `${y}px`;
  }

  const hideTip = () => {
    tip.hidden = true;
  };
  window.addEventListener("scroll", hideTip, { passive: true });

  /* ---- box plots ---- */

  function niceCeil(value) {
    const step = value > 0.5 ? 0.2 : 0.1;
    return Math.min(1, Math.ceil(value / step) * step);
  }

  function boxPlot(metric, stats) {
    const W = 320;
    const H = 292;
    const m = { l: 40, r: 8, t: 10, b: 56 };
    const innerW = W - m.l - m.r;
    const innerH = H - m.t - m.b;
    const top = niceCeil(
      Math.max(...stats.map((s) => Math.max(s.hi, ...s.outliers, s.q3)).filter(Number.isFinite))
    );
    const y = (v) => m.t + innerH * (1 - v / top);
    const slot = innerW / AGENTS.length;

    const root = svg("svg", {
      viewBox: `0 0 ${W} ${H}`,
      role: "img",
      "aria-label": `${metric.label} distribution by method`,
    });

    const ticks = 5;
    for (let i = 0; i <= ticks; i += 1) {
      const v = (top / ticks) * i;
      root.append(
        svg("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: "rp-grid" }),
        svg("text", { x: m.l - 7, y: y(v) + 4, class: "rp-tick", "text-anchor": "end" }, v.toFixed(2))
      );
    }

    AGENTS.forEach((agent, i) => {
      const s = stats[i];
      const cx = m.l + slot * (i + 0.5);
      const bw = 38;
      const g = svg("g", { class: `rp-box rp-c-${agent.key}`, tabindex: 0, role: "img" });
      g.setAttribute("aria-label", `${agent.name}, ${metric.label}: median ${fmt(s.med)}, n = ${s.n}`);

      g.append(
        svg("line", { x1: cx, x2: cx, y1: y(s.hi), y2: y(s.q3), class: "rp-whisker" }),
        svg("line", { x1: cx, x2: cx, y1: y(s.q1), y2: y(s.lo), class: "rp-whisker" }),
        svg("line", { x1: cx - 8, x2: cx + 8, y1: y(s.hi), y2: y(s.hi), class: "rp-whisker" }),
        svg("line", { x1: cx - 8, x2: cx + 8, y1: y(s.lo), y2: y(s.lo), class: "rp-whisker" }),
        svg("rect", {
          x: cx - bw / 2, y: y(s.q3), width: bw, height: Math.max(1, y(s.q1) - y(s.q3)), rx: 3, class: "rp-body",
        }),
        svg("line", { x1: cx - bw / 2, x2: cx + bw / 2, y1: y(s.med), y2: y(s.med), class: "rp-median" })
      );
      const my = y(s.mean);
      g.append(svg("path", { d: `M${cx - 5} ${my - 4.5}L${cx + 5} ${my - 4.5}L${cx} ${my + 4.5}Z`, class: "rp-mean" }));
      s.outliers.forEach((v) => g.append(svg("circle", { cx, cy: y(v), r: 3.2, class: "rp-outlier" })));
      // A wide, transparent target so the whole column is hoverable.
      g.append(svg("rect", { x: cx - slot / 2, y: m.t, width: slot, height: innerH, class: "rp-hit" }));
      root.append(g);

      root.append(
        svg("text", { x: cx, y: H - 30, class: "rp-xlabel", "text-anchor": "middle" }, agent.name),
        svg("text", { x: cx, y: H - 14, class: "rp-xn", "text-anchor": "middle" }, `n = ${s.n}`)
      );

      const show = () =>
        showTip(g, `${agent.name} · ${metric.label}`, [
          `Median ${fmt(s.med)} · Mean ${fmt(s.mean)}`,
          `Q1–Q3 ${fmt(s.q1)}–${fmt(s.q3)}`,
          `Whiskers ${fmt(s.lo)}–${fmt(s.hi)}`,
          `${plural(s.outliers.length, "outlier")} · n = ${s.n}`,
        ]);
      g.addEventListener("pointerenter", show);
      g.addEventListener("focus", show);
      g.addEventListener("pointerleave", hideTip);
      g.addEventListener("blur", hideTip);
    });
    return root;
  }

  /* ---- sections ---- */

  function renderGlance(box, ctx) {
    const med = (metric, agent) => median(ctx.matchedValues(metric, agent));
    const others = (metric) =>
      AGENTS.slice(1).map((a) => `${a.name} ${fmt(med(metric, a.key))}`).join(" · ");
    const cards = [
      ["#gallery", String(ctx.panels.length), "Panels with a result", plural(ctx.data.papers.length, "paper")],
      ["#gallery", String(ctx.data.matchedCount), "Matched panels", "Images from all three methods"],
      ["#similarity", fmt(med("ssim", "tissueagent")), "Median SSIM, TissueAgent", others("ssim")],
      ["#similarity", fmt(med("phash", "tissueagent")), "Median pHash, TissueAgent", others("phash")],
    ];
    cards.forEach(([href, num, label, sub]) => {
      const a = el("a", "paper-highlight");
      a.href = href;
      a.append(el("span", "ph-num", num), el("span", "ph-lab", label), el("span", "ph-sub", sub));
      box.append(a);
    });
  }

  function renderScope(node, ctx) {
    const reruns = ctx.panels.filter((p) => p.runs.tissueagent.rerun);
    const rerunPapers = [...new Set(reruns.map((p) => p.paper.title))];
    const parts = [
      `This page lists the ${ctx.panels.length} panels from ${plural(ctx.data.papers.length, "paper")} that have ` +
        "at least one completed attempt in the current snapshot. The automated runs used GPT-5.5 with high " +
        "reasoning effort and a two-hour limit per panel, and when a panel was retried the latest attempt is shown. " +
        "Panels whose required data could not be obtained were skipped and are not listed.",
    ];
    if (reruns.length) {
      parts.push(
        ` The ${plural(reruns.length, "TissueAgent result")} for “${rerunPapers.join("”, “")}”, marked †, ` +
          "come from a rerun in a separate notebook workflow rather than the automated harness, so they do not " +
          "follow an identical protocol."
      );
    }
    const date = fmtDate(ctx.data.generatedAt);
    if (date) parts.push(` Similarity scores were computed on ${date}.`);
    node.textContent = parts.join("");
  }

  function renderLegend(list) {
    AGENTS.forEach((a) => {
      const li = el("li", `rp-c-${a.key}`);
      li.append(el("i"), document.createTextNode(a.name));
      list.append(li);
    });
  }

  function renderPlots(grid, noteEl, ctx) {
    METRICS.forEach((metric) => {
      const stats = AGENTS.map((a) => boxStats(ctx.matchedValues(metric.key, a.key)));
      const wrap = el("div", "rp-plot");
      wrap.append(el("h5", null, metric.label), el("p", "rp-plot-sub", "Higher is more similar"), boxPlot(metric, stats));
      grid.append(wrap);
    });
    noteEl.textContent =
      "Boxes show the quartiles, the line is the median, triangles are means, whiskers reach the furthest points " +
      "within 1.5 × IQR, and circles are outliers. Every method is scored on the same matched panels; ORB " +
      "additionally needs detected image features, so its n can be smaller.";
  }

  function renderCoverage(table, noteEl, ctx) {
    const head = el("thead");
    const hr = el("tr");
    hr.append(el("th", "setting", "Method"));
    ["Attempts", "Completed", "Failed or timed out", "Images produced", "Median run time"].forEach((h) =>
      hr.append(el("th", null, h))
    );
    head.append(hr);
    const body = el("tbody");
    AGENTS.forEach((a) => {
      const runs = ctx.panels.map((p) => p.runs[a.key]);
      const count = (...statuses) => runs.filter((r) => statuses.includes(r.status)).length;
      const times = runs.map((r) => r.seconds).filter((s) => s != null);
      const coverage = ctx.data.coverage[a.key] || {};
      const tr = el("tr", a.key === "tissueagent" ? "row-ours" : "row-base");
      tr.append(el("td", "setting", a.name));
      [
        coverage.terminal ?? count("success", "failure", "timeout", "harness_error"),
        count("success"),
        count("failure", "timeout", "harness_error"),
        coverage.images ?? runs.filter((r) => r.image).length,
        fmtTime(times.length ? median(times) : null),
      ].forEach((v) => tr.append(el("td", null, String(v))));
      body.append(tr);
    });
    table.append(head, body);

    const notRun = AGENTS.map((a) => [a.name, ctx.panels.filter((p) => p.runs[a.key].status === "pending").length]).filter(
      ([, n]) => n
    );
    const flagged = ctx.panels.filter((p) => AGENTS.some((a) => p.runs[a.key].flagged)).length;
    const bits = [`The snapshot has ${ctx.panels.length} panels.`];
    if (notRun.length) bits.push(`${notRun.map(([name, n]) => `${name} has ${plural(n, "panel")}`).join(" and ")} with no completed attempt.`);
    bits.push(
      `${ctx.data.matchedCount} panels have an image from every method (the matched set)` +
        (flagged ? `; ${plural(flagged, "panel")} with an automatic access-audit flag ${flagged === 1 ? "is" : "are"} left out of it` : "") +
        ". Median run times include failed and timed-out attempts."
    );
    noteEl.textContent = bits.join(" ");
  }

  /* ---- gallery ---- */

  function statusPill(status) {
    const [label, tone] = STATUS[status] || STATUS.unknown;
    return el("span", `rp-pill rp-pill-${tone}`, label);
  }

  function bestFlags(panel, metric) {
    const values = AGENTS.map((a) => panel.runs[a.key][metric]);
    const present = values.filter((v) => v != null);
    if (present.length < 2) return values.map(() => false);
    const top = Math.max(...present);
    return values.map((v) => v != null && Math.abs(v - top) < 1e-9);
  }

  function imageUrl(panel, slot, thumb) {
    return `${IMG_ROOT}${panel.paper.article}/${panel.panel}/${slot}${thumb ? "-s" : ""}.webp`;
  }

  function emptyMessage(run) {
    return run.status === "pending" ? "Not run" : "No image produced";
  }

  function scoreRow(panel, agentKey, best) {
    const row = el("div", "rp-scores");
    METRICS.forEach((metric, i) => {
      const cell = el("span", best[i][AGENTS.findIndex((a) => a.key === agentKey)] ? "is-best" : "");
      cell.append(el("i", null, metric.label), el("b", null, fmt(panel.runs[agentKey][metric.key])));
      row.append(cell);
    });
    return row;
  }

  function buildCard(panel) {
    const card = el("article", "rp-panel");
    card.dataset.key = panel.key;

    const head = el("header", "rp-panel-head");
    head.append(el("h4", null, panel.label));
    if (panel.figureType) head.append(el("span", "rp-type", panel.figureType));
    if (panel.matched) head.append(el("span", "rp-badge", "Matched"));
    card.append(head);

    const best = METRICS.map((m) => bestFlags(panel, m.key));
    const row = el("div", "rp-row");

    const original = el("figure", "rp-cell");
    original.append(el("figcaption", "rp-cell-head"));
    original.firstChild.append(el("strong", null, "Original"));
    const originalThumb = el("button", "rp-thumb");
    originalThumb.type = "button";
    originalThumb.dataset.key = panel.key;
    originalThumb.setAttribute("aria-label", `Compare ${panel.label} from ${panel.paper.title}`);
    const oi = el("img");
    oi.loading = "lazy";
    oi.decoding = "async";
    oi.alt = `Published ${panel.label}`;
    oi.src = imageUrl(panel, "original", true);
    originalThumb.append(oi);
    original.append(originalThumb, el("p", "rp-meta", "Published figure"));
    row.append(original);

    AGENTS.forEach((agent) => {
      const run = panel.runs[agent.key];
      const cell = el("figure", `rp-cell rp-c-${agent.key}`);
      const cap = el("figcaption", "rp-cell-head");
      cap.append(el("strong", null, run.rerun ? `${agent.name} †` : agent.name), statusPill(run.status));
      cell.append(cap);
      if (run.image) {
        const btn = el("button", "rp-thumb");
        btn.type = "button";
        btn.dataset.key = panel.key;
        btn.dataset.slot = agent.key;
        btn.setAttribute("aria-label", `Compare ${panel.label}, starting from the ${agent.name} image`);
        const img = el("img");
        img.loading = "lazy";
        img.decoding = "async";
        img.alt = `${agent.name} reproduction of ${panel.label}`;
        img.src = imageUrl(panel, agent.key, true);
        btn.append(img);
        cell.append(btn);
      } else {
        cell.append(el("div", "rp-thumb is-empty", emptyMessage(run)));
      }
      cell.append(el("p", "rp-meta", run.seconds != null ? `Run time ${fmtTime(run.seconds)}` : "No run time"));
      cell.append(scoreRow(panel, agent.key, best));
      row.append(cell);
    });
    card.append(row);

    const notes = [];
    if (panel.runs.tissueagent.rerun) {
      notes.push("† The TissueAgent result for this panel is a rerun in a separate notebook workflow, not the automated harness.");
    }
    const flagged = AGENTS.filter((a) => panel.runs[a.key].flagged).map((a) => a.name);
    if (flagged.length) {
      notes.push(
        `An automatic access-audit flag on the ${flagged.join(" and ")} run leaves this panel out of the matched set. ` +
          "Flags are review signals, not confirmed violations."
      );
    }
    notes.forEach((text) => card.append(el("p", "rp-note", text)));

    if (panel.caption) {
      const details = el("details", "rp-caption");
      details.append(el("summary", null, "Figure caption"), el("p", null, panel.caption));
      card.append(details);
    }
    return card;
  }

  function doiUrl(doi) {
    if (!doi) return "";
    return /^https?:/.test(doi) ? doi : `https://doi.org/${doi}`;
  }

  function buildGallery(root, ctx) {
    const groups = [];
    ctx.data.papers.forEach((paper) => {
      const section = el("section", "rp-paper");
      const head = el("header", "rp-paper-head");
      head.append(el("h3", null, paper.title));
      const meta = el("p", "rp-paper-meta");
      meta.append(document.createTextNode(`${paper.journal}, ${paper.year} · ${plural(paper.panels.length, "panel")}`));
      const url = doiUrl(paper.doi);
      if (url) {
        const link = el("a", null, "DOI");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener";
        meta.append(document.createTextNode(" · "), link);
      }
      head.append(meta);
      section.append(head);
      const list = el("div", "rp-panel-list");
      const cards = paper.panels.map((p) => {
        const card = buildCard(ctx.byKey.get(`${paper.article}/${p.panel}`));
        list.append(card);
        return { panel: ctx.byKey.get(`${paper.article}/${p.panel}`), card };
      });
      section.append(list);
      root.append(section);
      groups.push({ section, cards });
    });
    return groups;
  }

  /* ---- compare dialog ---- */

  function initDialog(ctx) {
    const dialog = $("[data-rp-dialog]");
    if (!dialog || typeof dialog.showModal !== "function") return () => {};
    const grid = $("[data-rp-dialog-grid]", dialog);
    let list = [];
    let index = 0;

    function paint() {
      const panel = list[index];
      if (!panel) return;
      $("[data-rp-dialog-label]", dialog).textContent = panel.label;
      $("[data-rp-dialog-paper]", dialog).textContent = `${panel.paper.title} · ${panel.paper.journal}, ${panel.paper.year}`;
      $("[data-rp-dialog-count]", dialog).textContent = `${index + 1} / ${list.length}`;
      const best = METRICS.map((m) => bestFlags(panel, m.key));
      grid.replaceChildren();
      grid.style.removeProperty("--frame-ar");

      // All four frames share one aspect ratio, taken from the tallest image, so rows line up.
      const refit = () => {
        const ratios = $$("img", grid).filter((i) => i.naturalWidth).map((i) => i.naturalWidth / i.naturalHeight);
        if (ratios.length) grid.style.setProperty("--frame-ar", String(Math.min(2.2, Math.max(0.7, Math.min(...ratios)))));
      };

      const mk = (title, status, imageSrc, emptyText, footer, cls) => {
        const cell = el("figure", `rp-dcell ${cls || ""}`);
        const cap = el("figcaption", "rp-cell-head");
        cap.append(el("strong", null, title));
        if (status) cap.append(statusPill(status));
        cell.append(cap);
        if (imageSrc) {
          const frame = el("div", "rp-dframe");
          const img = el("img");
          img.decoding = "async";
          img.alt = title;
          img.addEventListener("load", refit);
          img.src = imageSrc;
          frame.append(img);
          cell.append(frame);
        } else {
          cell.append(el("div", "rp-dframe is-empty", emptyText));
        }
        if (footer) cell.append(footer);
        return cell;
      };

      grid.append(mk("Original", null, imageUrl(panel, "original", false), "", el("p", "rp-meta", "Published figure")));
      AGENTS.forEach((agent, i) => {
        const run = panel.runs[agent.key];
        const footer = el("div");
        footer.append(
          el("p", "rp-meta", run.seconds != null ? `Run time ${fmtTime(run.seconds)}` : "No run time"),
          scoreRow(panel, agent.key, best)
        );
        grid.append(
          mk(
            run.rerun ? `${agent.name} †` : agent.name,
            run.status,
            run.image ? imageUrl(panel, agent.key, false) : "",
            emptyMessage(run),
            footer,
            `rp-c-${agent.key}`
          )
        );
      });
    }

    const step = (delta) => {
      if (!list.length) return;
      index = (index + delta + list.length) % list.length;
      paint();
    };

    $("[data-rp-dialog-prev]", dialog).addEventListener("click", () => step(-1));
    $("[data-rp-dialog-next]", dialog).addEventListener("click", () => step(1));
    $("[data-rp-dialog-close]", dialog).addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog) dialog.close();
    });
    dialog.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") step(-1);
      if (e.key === "ArrowRight") step(1);
    });

    return (panels, key) => {
      list = panels;
      index = Math.max(0, panels.findIndex((p) => p.key === key));
      paint();
      dialog.showModal();
    };
  }

  /* ---- filters ---- */

  function initFilters(ctx, groups, openCompare) {
    const filterBox = $("[data-rp-filters]");
    const search = $("[data-rp-search]");
    const summary = $("[data-rp-summary]");
    const missing = (p) => AGENTS.some((a) => !p.runs[a.key].image);
    const filters = [
      { id: "all", label: "All", test: () => true },
      { id: "matched", label: "Matched", test: (p) => p.matched },
      { id: "missing", label: "Missing an image", test: missing },
    ];
    let active = "all";
    let visible = ctx.panels.slice();

    filters.forEach((f) => {
      const btn = el("button");
      btn.type = "button";
      btn.dataset.filter = f.id;
      btn.append(document.createTextNode(`${f.label} `), el("span", null, String(ctx.panels.filter(f.test).length)));
      btn.addEventListener("click", () => {
        active = f.id;
        apply();
      });
      filterBox.append(btn);
    });

    function apply() {
      const needle = search.value.trim().toLowerCase();
      const test = filters.find((f) => f.id === active).test;
      visible = [];
      groups.forEach(({ section, cards }) => {
        let shown = 0;
        cards.forEach(({ panel, card }) => {
          const ok = test(panel) && (!needle || panel.search.includes(needle));
          card.hidden = !ok;
          if (ok) {
            shown += 1;
            visible.push(panel);
          }
        });
        section.hidden = shown === 0;
      });
      $$("button", filterBox).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.filter === active)));
      summary.textContent = visible.length
        ? `Showing ${visible.length} of ${ctx.panels.length} panels.`
        : "No panels match. Clear the search or choose another filter.";
    }

    search.addEventListener("input", apply);
    $("[data-rp-gallery]").addEventListener("click", (e) => {
      const btn = e.target.closest(".rp-thumb[data-key]");
      if (btn) openCompare(visible, btn.dataset.key);
    });
    apply();
  }

  /* ---- section spy for the top bar ---- */

  function initSpy() {
    const links = $$("[data-spy]");
    const sections = links.map((a) => document.getElementById(a.dataset.spy));
    let queued = false;
    const spy = () => {
      queued = false;
      const probe = window.innerHeight * 0.3;
      let active = -1;
      sections.forEach((s, i) => {
        const r = s.getBoundingClientRect();
        if (r.top <= probe && r.bottom > probe) active = i;
      });
      links.forEach((a, i) => a.classList.toggle("is-active", i === active));
    };
    window.addEventListener(
      "scroll",
      () => {
        if (!queued) {
          queued = true;
          requestAnimationFrame(spy);
        }
      },
      { passive: true }
    );
    spy();
  }

  /* ---- boot ---- */

  function showError(message) {
    const box = el("div", "paper-preprint-notice");
    box.append(el("p", null, message));
    $(".paper-hero").after(box);
  }

  function init(data) {
    const panels = [];
    data.papers.forEach((paper) =>
      paper.panels.forEach((p) => {
        p.paper = paper;
        p.key = `${paper.article}/${p.panel}`;
        p.search = [paper.title, paper.journal, paper.year, p.label, p.figureType, ...(p.technologies || []), paper.article]
          .join(" ")
          .toLowerCase();
        panels.push(p);
      })
    );
    const ctx = {
      data,
      panels,
      byKey: new Map(panels.map((p) => [p.key, p])),
      matchedValues: (metric, agent) =>
        panels.filter((p) => p.matched).map((p) => p.runs[agent][metric]).filter((v) => v != null),
    };

    renderScope($("[data-rp-scope]"), ctx);
    renderGlance($("[data-rp-glance]"), ctx);
    renderLegend($("[data-rp-legend]"));
    renderPlots($("[data-rp-plots]"), $("[data-rp-plot-note]"), ctx);
    renderCoverage($("[data-rp-coverage]"), $("[data-rp-coverage-note]"), ctx);
    const groups = buildGallery($("[data-rp-gallery]"), ctx);
    initFilters(ctx, groups, initDialog(ctx));
    initSpy();
  }

  fetch(DATA_URL)
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then(init)
    .catch((err) => {
      showError(
        `Could not load ${DATA_URL} (${err.message}). Serve the site over HTTP, for example with ` +
          "“python -m http.server” in the site folder, because browsers block fetch() on file:// pages."
      );
    });
})();
