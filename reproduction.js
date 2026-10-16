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

  function renderScope(node, ctx) {
    const parts = [
      `This page lists the ${ctx.panels.length} panels from ${plural(ctx.data.papers.length, "paper")} on which ` +
        "TissueAgent, SpatialAgent, and Biomni were all run in the current snapshot. The automated runs used GPT-5.5 " +
        "with high reasoning effort and a two-hour limit per panel, and when a panel was retried the latest attempt is " +
        "shown. Panels whose required data could not be obtained were skipped and are not listed.",
    ];
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
    ["Panels", "Images produced", "Median SSIM", "Median pHash", "Median ORB"].forEach((h) => hr.append(el("th", null, h)));
    head.append(hr);
    const body = el("tbody");
    AGENTS.forEach((a) => {
      const tr = el("tr", a.key === "tissueagent" ? "row-ours" : "row-base");
      tr.append(el("td", "setting", a.name));
      [
        String(ctx.panels.length),
        String(ctx.panels.filter((p) => p.runs[a.key].image).length),
        ...METRICS.map((m) => fmt(median(ctx.matchedValues(m.key, a.key)))),
      ].forEach((v) => tr.append(el("td", null, v)));
      body.append(tr);
    });
    table.append(head, body);

    noteEl.textContent =
      `Every method was run on all ${ctx.panels.length} panels. Medians are taken over the ` +
      `${ctx.data.matchedCount} matched panels.`;
  }

  /* ---- benchmark statistics ---- */

  const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const LABEL_OVERRIDES = {
    "legacy Spatial Transcriptomics": "Spatial Transcriptomics (legacy)",
    "No auxiliary modality identified": "None identified",
  };
  const LAST = new Set(["Other / unspecified", "None identified"]);

  // Plain words that open a label get a capital; names such as seqFISH or scRNA-seq keep their spelling.
  const CAPITALISE = new Set(["histology", "genotype", "bulk", "microscopy", "immunofluorescence"]);

  function prettyLabel(label) {
    if (LABEL_OVERRIDES[label]) return LABEL_OVERRIDES[label];
    const spaced = label.replace(/\s*\/\s*/g, " / ");
    const first = spaced.split(/[\s/]/)[0];
    return CAPITALISE.has(first) ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : spaced;
  }

  /** Count labels; each item is one label or a list of labels. */
  function tally(items) {
    const counts = new Map();
    items.forEach((item) =>
      (Array.isArray(item) ? item : [item]).forEach((key) => {
        if (key) counts.set(key, (counts.get(key) || 0) + 1);
      })
    );
    return [...counts].map(([label, count]) => ({ label: prettyLabel(label), count }));
  }

  const byCount = (a, b) =>
    LAST.has(a.label) - LAST.has(b.label) || b.count - a.count || a.label.localeCompare(b.label);

  const drawObserver =
    !REDUCED_MOTION && "IntersectionObserver" in window
      ? new IntersectionObserver(
          (entries) =>
            entries.forEach((e) => {
              if (!e.isIntersecting) return;
              e.target.classList.add("is-drawn");
              drawObserver.unobserve(e.target);
            }),
          { threshold: 0.25 }
        )
      : null;

  function statCard(host, title, note, rows, total) {
    const card = el("div", "rp-card rp-stat");
    card.append(el("h5", null, title));
    if (note) card.append(el("p", "rp-stat-note", note));
    const max = Math.max(...rows.map((r) => r.count));
    const list = el("ul", "rp-bars");
    rows.forEach((row) => {
      const item = el("li");
      const head = el("div", "rp-bar-head");
      const value = el("span", "rp-bar-val");
      value.append(el("b", null, String(row.count)), document.createTextNode(` · ${((row.count * 100) / total).toFixed(1)}%`));
      head.append(el("span", "rp-bar-label", row.label), value);
      const track = el("div", "rp-bar-track");
      const fill = el("i");
      fill.style.setProperty("--w", `${((row.count / max) * 100).toFixed(1)}%`);
      track.append(fill);
      item.append(head, track);
      list.append(item);
    });
    card.append(list);
    host.append(card);
    if (drawObserver) drawObserver.observe(card);
    else card.classList.add("is-drawn");
  }

  function renderStats(host, leadEl, papersTable, ctx) {
    const total = ctx.panels.length;
    const papers = ctx.data.papers;
    const journals = new Set(papers.map((p) => p.journal));
    const years = papers.map((p) => Number(p.year)).filter(Number.isFinite);
    const span = years.length ? `${Math.min(...years)}–${Math.max(...years)}` : "";
    leadEl.textContent =
      `The ${total} panels come from ${plural(papers.length, "paper")} in ${plural(journals.size, "journal")}` +
      (span ? `, published ${span}` : "") +
      ". Each panel has one task type. Spatial technology, auxiliary data, and raw-data source can have several " +
      "labels per panel, so their percentages can add up to more than 100%. Technology and auxiliary-data labels " +
      "come from a rule-based reading of each panel's data records and text.";

    const kind = (p) => (/^Extended/i.test(p.label) ? "Extended Data figure" : /^Supp/i.test(p.label) ? "Supplementary figure" : "Main figure");
    const KIND_ORDER = ["Main figure", "Extended Data figure", "Supplementary figure"];
    const chrono = (a, b) => a.label.localeCompare(b.label);
    const panelPaper = (p) => p.paper;

    statCard(host, "Task type", "One label per panel", tally(ctx.panels.map((p) => p.figureType)).sort(byCount), total);
    statCard(host, "Spatial technology", "Several labels possible", tally(ctx.panels.map((p) => p.technologies)).sort(byCount), total);
    statCard(host, "Auxiliary data", "Other data a panel draws on. Several labels possible", tally(ctx.panels.map((p) => p.modalities)).sort(byCount), total);
    statCard(host, "Raw-data source", "Where the raw data are hosted. Several possible", tally(ctx.panels.map((p) => p.dataSources)).sort(byCount), total);
    statCard(host, "Journal", "", tally(ctx.panels.map((p) => panelPaper(p).journal)).sort(byCount), total);
    statCard(host, "Publication year", "", tally(ctx.panels.map((p) => panelPaper(p).year)).sort(chrono), total);
    statCard(
      host,
      "Figure type",
      "",
      tally(ctx.panels.map(kind)).sort((a, b) => KIND_ORDER.indexOf(a.label) - KIND_ORDER.indexOf(b.label)),
      total
    );

    // Source papers, most panels first.
    const head = el("thead");
    const hr = el("tr");
    ["Paper", "Journal", "Year", "Panels"].forEach((h) => hr.append(el("th", h === "Paper" || h === "Journal" ? "setting" : null, h)));
    head.append(hr);
    const body = el("tbody");
    [...papers]
      .sort((a, b) => b.panels.length - a.panels.length || a.title.localeCompare(b.title))
      .forEach((paper) => {
        const tr = el("tr", "row-base");
        const title = el("td", "text-left");
        const url = doiUrl(paper.doi);
        if (url) {
          const a = el("a", null, paper.title);
          a.href = url;
          a.target = "_blank";
          a.rel = "noopener";
          title.append(a);
        } else {
          title.textContent = paper.title;
        }
        tr.append(title, el("td", "text-left", paper.journal), el("td", null, paper.year), el("td", null, String(paper.panels.length)));
        body.append(tr);
      });
    papersTable.append(head, body);
  }

  /* ---- method text: the small Markdown subset it uses, built with DOM nodes ---- */

  function appendInline(parent, text) {
    text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).forEach((part) => {
      if (!part) return;
      if (part.length > 4 && part.startsWith("**") && part.endsWith("**")) parent.append(el("strong", null, part.slice(2, -2)));
      else if (part.length > 2 && part.startsWith("`") && part.endsWith("`")) parent.append(el("code", null, part.slice(1, -1)));
      else parent.append(document.createTextNode(part));
    });
  }

  function renderMarkdown(source) {
    const root = el("div", "rp-md");
    let lines = [];
    let list = null;

    const flushText = () => {
      if (!lines.length) return;
      const text = lines.join(" ").replace(/\s+/g, " ").trim();
      lines = [];
      const src = text.match(/^(?:\*\*)?Source(?::\*\*|\*\*:|:)\s*(.*)$/s);
      if (src) {
        const p = el("p", "rp-source");
        p.append(el("span", null, "Source"), document.createTextNode(" "));
        appendInline(p, src[1]);
        root.append(p);
      } else {
        const p = el("p");
        appendInline(p, text);
        root.append(p);
      }
    };
    const flushAll = () => {
      flushText();
      list = null;
    };

    source.split(/\r?\n/).forEach((raw) => {
      const line = raw.trim();
      let m;
      if (!line) return flushAll();
      if ((m = line.match(/^#{1,6}\s+(.*)$/))) {
        flushAll();
        const h = el("h5", "rp-md-h");
        appendInline(h, m[1]);
        root.append(h);
      } else if ((m = line.match(/^([-*]|\d+[.)])\s+(.*)$/))) {
        flushText();
        const type = /\d/.test(m[1]) ? "ol" : "ul";
        if (!list || list.type !== type) {
          list = { type, node: el(type) };
          root.append(list.node);
        }
        const li = el("li");
        appendInline(li, m[2]);
        list.node.append(li);
      } else {
        if (list) list = null;
        lines.push(line);
      }
    });
    flushAll();
    return root;
  }

  /* Long text is clamped to a few lines with a fade; "Show more" reveals the rest. */
  const clampLinks = new WeakMap();

  function measureClamp(body) {
    const toggle = clampLinks.get(body);
    if (!toggle) return;
    if (body.classList.contains("is-open")) return;
    const clipped = body.scrollHeight > body.clientHeight + 2;
    body.classList.toggle("is-clipped", clipped);
    toggle.hidden = !clipped;
  }

  const clampObserver =
    "ResizeObserver" in window
      ? new ResizeObserver((entries) => entries.forEach((e) => measureClamp(e.target)))
      : null;

  function textBlock(title, hint, content) {
    const col = el("section", "rp-text-col");
    const head = el("h5", null, title);
    if (hint) head.append(el("span", null, hint));
    const body = el("div", "rp-clamp");
    body.append(content);
    const toggle = el("button", "rp-more", "Show more");
    toggle.type = "button";
    toggle.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    clampLinks.set(body, toggle);

    toggle.addEventListener("click", () => {
      const opening = !body.classList.contains("is-open");
      toggle.setAttribute("aria-expanded", String(opening));
      toggle.textContent = opening ? "Show less" : "Show more";
      if (opening) {
        body.classList.add("is-open");
        body.style.maxHeight = `${body.scrollHeight}px`;
        body.addEventListener(
          "transitionend",
          () => {
            if (body.classList.contains("is-open")) body.style.maxHeight = "none";
          },
          { once: true }
        );
      } else {
        body.style.maxHeight = `${body.scrollHeight}px`;
        requestAnimationFrame(() => {
          body.classList.remove("is-open");
          body.style.maxHeight = "";
        });
      }
    });

    col.append(head, body, toggle);
    if (clampObserver) clampObserver.observe(body);
    else requestAnimationFrame(() => measureClamp(body));
    return col;
  }

  /* ---- gallery ---- */

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
      cap.append(el("strong", null, agent.name));
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
        cell.append(el("div", "rp-thumb is-empty", "No image"));
      }
      cell.append(scoreRow(panel, agent.key, best));
      row.append(cell);
    });
    card.append(row);

    const band = el("div", "rp-text");
    if (panel.caption) {
      const caption = el("p");
      caption.textContent = panel.caption;
      band.append(textBlock("Figure caption", "", caption));
    }
    if (panel.methods) band.append(textBlock("Method description", "Supplied with the task", renderMarkdown(panel.methods)));
    if (band.children.length) card.append(band);
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

      const mk = (title, imageSrc, emptyText, footer, cls) => {
        const cell = el("figure", `rp-dcell ${cls || ""}`);
        const cap = el("figcaption", "rp-cell-head");
        cap.append(el("strong", null, title));
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

      grid.append(mk("Original", imageUrl(panel, "original", false), "", el("p", "rp-meta", "Published figure")));
      AGENTS.forEach((agent, i) => {
        const run = panel.runs[agent.key];
        const footer = scoreRow(panel, agent.key, best);
        grid.append(
          mk(
            agent.name,
            run.image ? imageUrl(panel, agent.key, false) : "",
            "No image",
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

  /* ---- search ---- */

  function initSearch(ctx, groups, openCompare) {
    const search = $("[data-rp-search]");
    const summary = $("[data-rp-summary]");
    let visible = ctx.panels.slice();

    function apply() {
      const needle = search.value.trim().toLowerCase();
      visible = [];
      groups.forEach(({ section, cards }) => {
        let shown = 0;
        cards.forEach(({ panel, card }) => {
          const ok = !needle || panel.search.includes(needle);
          card.hidden = !ok;
          if (ok) {
            shown += 1;
            visible.push(panel);
          }
        });
        section.hidden = shown === 0;
      });
      if (!needle) summary.textContent = "";
      else if (visible.length) summary.textContent = `Showing ${visible.length} of ${ctx.panels.length} panels.`;
      else summary.textContent = "No panels match. Clear the search to see all panels.";
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
        p.search = [paper.title, paper.journal, paper.year, p.label, p.figureType, ...(p.technologies || []), paper.article, p.methods]
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
    renderStats($("[data-rp-stats]"), $("[data-rp-stats-lead]"), $("[data-rp-papers]"), ctx);
    renderLegend($("[data-rp-legend]"));
    renderPlots($("[data-rp-plots]"), $("[data-rp-plot-note]"), ctx);
    renderCoverage($("[data-rp-coverage]"), $("[data-rp-coverage-note]"), ctx);
    const groups = buildGallery($("[data-rp-gallery]"), ctx);
    initSearch(ctx, groups, initDialog(ctx));
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
