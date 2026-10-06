/* TissueAgent project page interactions. No dependencies. */
(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /** Run `cb` once when `node` first scrolls into view. */
  function whenVisible(node, cb, threshold = 0.3) {
    if (!("IntersectionObserver" in window)) {
      cb();
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          io.disconnect();
          cb();
        }
      },
      { threshold }
    );
    io.observe(node);
  }

  /** Track whether `node` is on screen; `cb(visible)` fires on every change. */
  function watchVisible(node, cb) {
    if (!("IntersectionObserver" in window)) return cb(true);
    new IntersectionObserver((entries) => entries.forEach((e) => cb(e.isIntersecting)), {
      threshold: 0.15,
    }).observe(node);
  }

  /** A cancellable sequence: `wait` rejects silently once a newer run starts. */
  function sequencer() {
    let token = 0;
    return {
      start() {
        token += 1;
        const mine = token;
        return {
          alive: () => mine === token,
          wait: (ms) =>
            new Promise((resolve, reject) =>
              setTimeout(() => (mine === token ? resolve() : reject(new Error("cancelled"))), ms)
            ),
        };
      },
    };
  }

  /* ------------------------------------------------------------ header */

  const topbar = $(".topbar");
  const progress = $(".read-progress span");
  const spyLinks = $$("[data-spy]");
  const spyTargets = spyLinks.map((a) => document.getElementById(a.dataset.spy));
  let scrollQueued = false;

  function onScroll() {
    scrollQueued = false;
    const doc = document.documentElement;
    const max = doc.scrollHeight - window.innerHeight;
    progress.style.setProperty("--p", max > 0 ? (window.scrollY / max).toFixed(4) : 0);
    topbar.classList.toggle("is-scrolled", window.scrollY > 4);

    const probe = window.innerHeight * 0.35;
    let active = null;
    spyTargets.forEach((section, i) => {
      const r = section.getBoundingClientRect();
      if (r.top <= probe && r.bottom > probe) active = i;
    });
    spyLinks.forEach((a, i) => a.classList.toggle("is-active", i === active));
  }

  window.addEventListener(
    "scroll",
    () => {
      if (!scrollQueued) {
        scrollQueued = true;
        requestAnimationFrame(onScroll);
      }
    },
    { passive: true }
  );
  onScroll();

  /* ---------------------------------------------------- count-up numbers */

  function formatCount(node, value) {
    const decimals = Number(node.dataset.decimals || 0);
    return value.toFixed(decimals) + (node.dataset.suffix || "");
  }

  $$("[data-count]").forEach((node) => {
    if (reduceMotion) return;
    const target = Number(node.dataset.count);
    node.textContent = formatCount(node, 0);
    whenVisible(
      node,
      () => {
        const t0 = performance.now();
        const dur = 1200;
        const tick = (now) => {
          const p = Math.min(1, (now - t0) / dur);
          const eased = 1 - Math.pow(1 - p, 3);
          node.textContent = formatCount(node, target * eased);
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      },
      0.6
    );
  });

  /* ---------------------------------------------- framework: role explorer */

  const ROLES = {
    planner: {
      name: "Planner",
      desc: "Turns the request into a plan of explicit steps, each with a rationale and the artifacts it should produce. Requests it can answer right away are answered directly, and underspecified ones go back to you for clarification.",
      writes: "Step names, rationales, and expected artifacts",
      uses: "Workflow templates from the Plan Registry",
    },
    recruiter: {
      name: "Recruiter",
      desc: "Assigns every step to the expert agent best suited to it and records why. Relevant skills are attached to the step alongside the agent.",
      writes: "Assigned agent, assignment rationale, and skills",
      uses: "The Agent Registry and the Skill Registry",
    },
    manager: {
      name: "Manager",
      desc: "Dispatches each step to its expert agent, audits what comes back, and marks the step succeeded, failed, or skipped. A stuck step can be rerun with revised inputs, tools, or strategy.",
      writes: "Step status, outcome summaries, and artifact links",
      uses: "Expert agents working in Python and R",
    },
    evaluator: {
      name: "Evaluator",
      desc: "Checks whether the intermediate and final outputs satisfy the request. When they don't, it sends the run back to the Planner with targeted feedback instead of starting over.",
      writes: "A verdict, plus feedback when it asks for a replan",
      uses: "The updated plan and its linked artifacts",
    },
    reporter: {
      name: "Reporter",
      desc: "Returns a concise answer together with a reproducible Jupyter notebook, with explicit artifact paths and provenance.",
      writes: "The final report and notebook",
      uses: "Everything recorded in the plan",
    },
  };

  function initPipeline() {
    const root = $("[data-pipeline]");
    if (!root) return;
    const tabs = $$("[role=tab]", root);
    const panel = $("[data-pipeline-detail]", root);
    let auto = !reduceMotion;
    let timer = 0;
    let index = 0;

    function render(i) {
      index = i;
      tabs.forEach((t, j) => {
        t.setAttribute("aria-selected", String(j === i));
        t.tabIndex = j === i ? 0 : -1;
      });
      const role = ROLES[tabs[i].dataset.role];
      const left = el("div");
      left.append(el("h3", null, role.name), el("p", null, role.desc));
      const dl = el("dl");
      [
        ["Writes to the plan", role.writes],
        ["Draws on", role.uses],
      ].forEach(([k, v]) => {
        const wrap = el("div");
        wrap.append(el("dt", null, k), el("dd", null, v));
        dl.append(wrap);
      });
      panel.replaceChildren(left, dl);
    }

    function stopAuto() {
      auto = false;
      clearInterval(timer);
    }

    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => {
        stopAuto();
        render(i);
      });
      tab.addEventListener("keydown", (e) => {
        const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
        if (!step) return;
        e.preventDefault();
        stopAuto();
        const next = (i + step + tabs.length) % tabs.length;
        render(next);
        tabs[next].focus();
      });
    });

    render(0);

    watchVisible(root, (visible) => {
      root.classList.toggle("is-flowing", visible && !reduceMotion);
      clearInterval(timer);
      if (visible && auto) timer = setInterval(() => render((index + 1) % tabs.length), 3600);
    });
  }

  /* --------------------------------------------------- method: plan demo */

  const PLAN = [
    {
      title: "Load and validate the MERFISH section",
      expected: "outputs/heart.h5ad",
      agent: "data_onboarding_agent",
      outputs: "outputs/heart.h5ad",
    },
    {
      title: "Annotate cell types",
      expected: "outputs/cell_types.h5ad, umap.png",
      agent: "cell_annotator_agent",
      skills: "cell_type_annotation",
      error: "reference genes miss the 238-gene panel",
      retry: "rerun with a matched CELLxGENE reference",
      outputs: "outputs/cell_types.h5ad, umap.png",
    },
    {
      title: "Identify spatial niches",
      expected: "outputs/niches.h5ad, niche_map.png",
      agent: "cell_annotator_agent",
      skills: "tissue_niche_annotation",
      outputs: "outputs/niches.h5ad, niche_map.png",
    },
    {
      title: "Summarize niche composition",
      expected: "outputs/niche_composition.csv",
      agent: "coding_agent",
      outputs: "outputs/niche_composition.csv",
    },
  ];

  function initPlan() {
    const root = $("[data-plan]");
    if (!root) return;
    const list = $("[data-plan-steps]", root);
    const verdict = $("[data-plan-verdict]", root);
    const replay = $("[data-plan-replay]", root);
    const seq = sequencer();

    // Build the final layout up front so nothing shifts while it plays.
    const steps = PLAN.map((s, i) => {
      const li = el("li", "plan-step");
      const head = el("div", "plan-step-head");
      const status = el("span", "status", "pending");
      status.dataset.status = "pending";
      head.append(el("span", "plan-step-n", `Step ${i + 1}`), el("span", "plan-step-title", s.title), status);
      const fields = el("ul", "plan-fields");
      const field = (by, key, value, extra) => {
        const f = el("li", "plan-field" + (extra ? ` ${extra}` : ""));
        f.dataset.by = by;
        f.append(el("span", null, key), el("span", null, value));
        fields.append(f);
        return f;
      };
      const out = {
        li,
        status,
        expected: field("planner", "expected", s.expected),
        agent: field("recruiter", "agent", s.agent),
        skills: s.skills ? field("recruiter", "skills", s.skills) : null,
        error: s.error ? field("manager", "error", s.error, "is-error") : null,
        retry: s.retry ? field("manager", "retry", s.retry) : null,
        outputs: field("manager", "outputs", s.outputs),
      };
      li.append(head, fields);
      list.append(li);
      return out;
    });
    verdict.innerHTML = "";
    verdict.append(
      document.createTextNode("Evaluator: "),
      el("b", null, "outputs satisfy the request"),
      document.createTextNode(", handing off to the Reporter.")
    );

    const setStatus = (s, value) => {
      s.status.dataset.status = value;
      s.status.textContent = value;
    };
    const show = (node, on = true) => node && node.classList.toggle("is-in", on);

    function reset() {
      steps.forEach((s) => {
        show(s.li, false);
        Object.values(s).forEach((n) => n && n.classList && n.classList.contains("plan-field") && show(n, false));
        setStatus(s, "pending");
      });
      show(verdict, false);
      replay.classList.remove("is-visible");
    }

    function finalState() {
      steps.forEach((s) => {
        show(s.li);
        [s.expected, s.agent, s.skills, s.error, s.retry, s.outputs].forEach((n) => show(n));
        setStatus(s, "succeeded");
      });
      show(verdict);
    }

    async function play() {
      const run = seq.start();
      reset();
      try {
        await run.wait(200);
        for (const s of steps) {
          show(s.li);
          show(s.expected);
          await run.wait(260);
        }
        await run.wait(350);
        for (const s of steps) {
          show(s.agent);
          show(s.skills);
          await run.wait(260);
        }
        await run.wait(350);
        for (const s of steps) {
          setStatus(s, "running");
          await run.wait(650);
          if (s.error) {
            setStatus(s, "failed");
            show(s.error);
            await run.wait(900);
            show(s.retry);
            setStatus(s, "running");
            await run.wait(800);
          }
          setStatus(s, "succeeded");
          show(s.outputs);
          await run.wait(320);
        }
        await run.wait(300);
        show(verdict);
        replay.classList.add("is-visible");
      } catch {
        /* superseded */
      }
    }

    replay.addEventListener("click", play);
    if (reduceMotion) finalState();
    else {
      reset();
      whenVisible(root, play, 0.4);
    }
  }

  /* ------------------------------------------- method: skill evolution */

  const EVOLVE = [
    "Every run is saved as a full trace: the code that ran, its outputs, the errors it hit, and how it recovered.",
    "An optimizer mines a chosen set of traces for error–correction pairs, unresolved failures, and avoidable cost, such as turns spent rereading scripts.",
    "Recurring patterns become candidate edits to the matching skills and plan templates: warnings, fixes, execution guidance, and validation checks.",
    "A reviewer approves or rejects each proposed edit. Guardrails cap the size of every edit and block changes to source code and to the validated scripts that skills run.",
    "Approved lessons are committed to the skill file as a versioned edit, and future runs retrieve them whenever that skill is assigned.",
  ];

  function initEvolve() {
    const root = $("[data-evolve]");
    if (!root) return;
    const tabs = $$("[data-evolve-step]", root);
    const track = $(".evolve-steps", root);
    const desc = $("[data-evolve-desc]", root);
    const lines = $$("[data-evolve-line]", root);
    let timer = 0;
    let current = 0;

    function render(i) {
      current = i;
      tabs.forEach((t, j) => {
        t.setAttribute("aria-selected", String(j === i));
        t.classList.toggle("is-past", j < i);
        t.tabIndex = j === i ? 0 : -1;
      });
      track.style.setProperty("--p", i / (tabs.length - 1));
      desc.textContent = EVOLVE[i];
      desc.style.animation = "none";
      void desc.offsetWidth;
      desc.style.animation = "";
      lines.forEach((line, k) => {
        line.classList.toggle("is-proposed", i === 2 || i === 3);
        line.classList.remove("is-in");
        if (i === 4) {
          if (reduceMotion) line.classList.add("is-in");
          else setTimeout(() => current === 4 && line.classList.add("is-in"), 180 + k * 260);
        }
      });
    }

    function stop() {
      clearInterval(timer);
      timer = 0;
    }

    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => {
        stop();
        render(i);
      });
      tab.addEventListener("keydown", (e) => {
        const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        if (!step) return;
        e.preventDefault();
        stop();
        const next = Math.max(0, Math.min(tabs.length - 1, i + step));
        render(next);
        tabs[next].focus();
      });
    });

    render(reduceMotion ? 4 : 0);
    if (!reduceMotion) {
      whenVisible(
        root,
        () => {
          timer = setInterval(() => {
            if (current >= tabs.length - 1) return stop();
            render(current + 1);
          }, 2600);
        },
        0.45
      );
    }
  }

  /* ------------------------------------------------------------- charts */

  const tip = $("[data-tip]");

  function showTip(target, strong, label) {
    tip.replaceChildren(el("strong", null, strong), el("span", null, label));
    tip.hidden = false;
    const r = target.getBoundingClientRect();
    const tr = tip.getBoundingClientRect();
    let x = r.left + r.width / 2 - tr.width / 2;
    x = Math.max(8, Math.min(window.innerWidth - tr.width - 8, x));
    let y = r.top - tr.height - 8;
    if (y < 64) y = r.bottom + 8;
    tip.style.left = `${x}px`;
    tip.style.top = `${y}px`;
  }

  function hideTip() {
    tip.hidden = true;
  }

  window.addEventListener("scroll", hideTip, { passive: true });

  const pct1 = (v) => `${v.toFixed(1)}%`;
  const dec2 = (v) => v.toFixed(2);

  /**
   * Small-multiple bar chart: one panel per metric, one row per method.
   * TissueAgent is the emphasis series; every row is labeled, so identity never
   * depends on color. data[dataset][method] = [[mean, sd] | null, ...] per metric.
   */
  function barChart(node, cfg) {
    const datasets = Object.keys(cfg.data);
    let active = datasets[0];
    const rows = [];

    const head = el("div", "viz-head");
    const titles = el("div");
    titles.append(el("p", "viz-title", cfg.title));
    if (cfg.sub) titles.append(el("p", "viz-sub", cfg.sub));
    head.append(titles);

    let seg = null;
    if (datasets.length > 1) {
      seg = el("div", "seg");
      seg.setAttribute("role", "group");
      seg.setAttribute("aria-label", "Dataset");
      datasets.forEach((d) => {
        const b = el("button", null, cfg.datasetLabels[d]);
        b.type = "button";
        b.setAttribute("aria-pressed", String(d === active));
        b.addEventListener("click", () => {
          active = d;
          $$("button", seg).forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
          update();
        });
        seg.append(b);
      });
      head.append(seg);
    }

    const panels = el("div", "viz-panels");
    if (cfg.labelWidth) panels.style.setProperty("--label-w", `${cfg.labelWidth}px`);
    panels.style.setProperty("--n", cfg.metrics.length);

    // Method names once, in their own column; CSS shows it only when panels line up.
    const labelsCol = el("div", "viz-labels");
    labelsCol.setAttribute("aria-hidden", "true");
    labelsCol.append(el("h5", null, " "));
    cfg.methods.forEach((m) => labelsCol.append(el("span", "viz-label" + (m === cfg.highlight ? " is-ta" : ""), m)));
    panels.append(labelsCol);

    cfg.metrics.forEach((metric, mi) => {
      const panel = el("div", "viz-panel");
      panel.append(el("h5", null, metric.label));
      cfg.methods.forEach((method) => {
        const row = el("div", "viz-row" + (method === cfg.highlight ? " is-ta" : ""));
        row.tabIndex = 0;
        const label = el("span", "viz-label", method);
        const trackEl = el("span", "viz-track");
        const bar = el("span", "viz-bar");
        bar.style.display = "block";
        const err = el("span", "viz-err");
        trackEl.append(bar, err);
        const value = el("span", "viz-value");
        row.append(label, trackEl, value);
        panel.append(row);
        const entry = { row, bar, err, value, method, mi, metric };
        rows.push(entry);
        const enter = () => {
          const v = cfg.data[active][method]?.[mi];
          if (v) {
            const sd = v[1] ? ` ± ${metric.fmt(v[1]).replace("%", "")}` : "";
            showTip(row, `${metric.fmt(v[0])}${sd}`, `${method}, ${metric.label.toLowerCase()}`);
          } else {
            showTip(row, cfg.naText?.[method] || "Not available", method);
          }
        };
        row.addEventListener("pointerenter", enter);
        row.addEventListener("focus", enter);
        row.addEventListener("pointerleave", hideTip);
        row.addEventListener("blur", hideTip);
      });
      panels.append(panel);
    });

    const foot = el("div", "viz-foot");
    if (cfg.note) foot.append(el("p", "viz-note", cfg.note));
    const details = el("details", "viz-table");
    details.append(el("summary", null, "Show table"));
    const tableWrap = el("div", "viz-table-scroll");
    details.append(tableWrap);
    foot.append(details);

    node.append(head, panels, foot);

    let drawn = false;

    function renderTable() {
      const table = el("table");
      const thead = el("thead");
      const hr = el("tr");
      hr.append(el("th", null, "Method"));
      cfg.metrics.forEach((m) => hr.append(el("th", null, m.label)));
      thead.append(hr);
      const tbody = el("tbody");
      cfg.methods.forEach((method) => {
        const tr = el("tr", method === cfg.highlight ? "is-ta" : "");
        tr.append(el("td", null, method));
        cfg.metrics.forEach((m, mi) => {
          const v = cfg.data[active][method]?.[mi];
          const text = v ? m.fmt(v[0]) + (v[1] ? ` ± ${m.fmt(v[1]).replace("%", "")}` : "") : "—";
          tr.append(el("td", null, text));
        });
        tbody.append(tr);
      });
      table.append(thead, tbody);
      tableWrap.replaceChildren(table);
    }

    function update() {
      rows.forEach(({ row, bar, err, value, method, mi, metric }) => {
        const v = cfg.data[active][method]?.[mi];
        row.classList.toggle("is-na", !v);
        if (!v) {
          bar.style.width = "0%";
          err.style.width = "0%";
          value.textContent = "—";
          return;
        }
        const [mean, sd] = v;
        const clamp = (x) => Math.max(0, Math.min(100, x));
        if (drawn) bar.style.width = `${clamp((mean / metric.max) * 100)}%`;
        value.textContent = metric.fmt(mean).replace(/\.0%$/, "%");
        if (sd) {
          const lo = clamp(((mean - sd) / metric.max) * 100);
          const hi = clamp(((mean + sd) / metric.max) * 100);
          err.style.left = `${lo}%`;
          err.style.width = `${hi - lo}%`;
          err.style.display = "block";
        } else {
          err.style.display = "none";
        }
      });
      renderTable();
    }

    update();

    const draw = () => {
      drawn = true;
      node.classList.add("is-drawn");
      update();
    };
    if (reduceMotion) draw();
    else whenVisible(node, () => requestAnimationFrame(draw), 0.35);
  }

  const M01 = (label) => ({ label, max: 1, fmt: dec2 });

  const CHARTS = {
    lohoff: {
      title: "Lohoff et al. panel 2E, reproduced from text",
      sub: "Cell types reproduced, out of 22 in the published panel",
      metrics: [{ label: "Cell types reproduced", max: 22, fmt: (v) => v.toFixed(0) }],
      methods: ["TissueAgent", "Biomni", "SpatialAgent"],
      highlight: "TissueAgent",
      naText: { SpatialAgent: "Produced an invalid figure" },
      data: { all: { TissueAgent: [[22, 0]], Biomni: [[12, 0]], SpatialAgent: [null] } },
      note: "SpatialAgent produced an invalid figure. Spearman ρ with the published ordering: ≈0.9 for TissueAgent, ≈0.5 for Biomni.",
    },
    genegpt: {
      title: "GeneGPT on GeneTuring",
      sub: "Accuracy on 450 questions across nine tasks",
      metrics: [{ label: "Accuracy", max: 100, fmt: pct1 }],
      methods: ["Through TissueAgent", "Direct GeneGPT"],
      highlight: "Through TissueAgent",
      labelWidth: 132,
      data: { all: { "Through TissueAgent": [[79.1, 0]], "Direct GeneGPT": [[77.6, 0]] } },
      note: "Same LLM, prompts, and tools in both settings.",
    },
    cellvoyager: {
      title: "CellVoyager on CellBench",
      sub: "50 queries, 483 reference analyses. Mean ± s.d. over three paired runs",
      metrics: [
        { label: "Micro-average", max: 100, fmt: pct1 },
        { label: "Macro-average", max: 100, fmt: pct1 },
      ],
      methods: ["Through TissueAgent", "Direct CellVoyager"],
      highlight: "Through TissueAgent",
      labelWidth: 132,
      data: {
        all: {
          "Through TissueAgent": [
            [73.64, 2.77],
            [75.85, 1.82],
          ],
          "Direct CellVoyager": [
            [69.48, 2.17],
            [72.74, 1.57],
          ],
        },
      },
      note: "Both settings use the o3-mini backbone and identical prompts.",
    },
    celltype: {
      title: "Cell-type annotation",
      sub: "Mean ± s.d. over three runs. Higher is better",
      metrics: [M01("Accuracy"), M01("Macro precision"), M01("Balanced accuracy"), M01("Macro F1")],
      methods: ["TissueAgent", "SpatialAgent", "STAgent", "Biomni", "GPTCellType", "CellTypist"],
      highlight: "TissueAgent",
      datasetLabels: { heart: "Human heart (MERFISH)", ovarian: "Ovarian cancer (Xenium)", brain: "Mouse brain (Stereo-seq)" },
      data: {
        heart: {
          TissueAgent: [[0.8508, 0.0066], [0.5957, 0.0361], [0.7268, 0.061], [0.6156, 0.0381]],
          SpatialAgent: [[0.9054, 0.0059], [0.558, 0.1303], [0.6921, 0.1382], [0.552, 0.1287]],
          STAgent: [[0.7455, 0.167], [0.5923, 0.1793], [0.6139, 0.15], [0.5679, 0.1884]],
          Biomni: [[0.768, 0.0298], [0.333, 0.0526], [0.268, 0.0928], [0.288, 0.0736]],
          GPTCellType: [[0.8006, 0.0112], [0.4502, 0.0144], [0.3513, 0.0072], [0.3906, 0.009]],
          CellTypist: [[0.6118, 0.0048], [0.3074, 0.003], [0.3145, 0.0027], [0.239, 0.0034]],
        },
        ovarian: {
          TissueAgent: [[0.9067, 0.0043], [0.6603, 0.0286], [0.6179, 0.035], [0.626, 0.0313]],
          SpatialAgent: [[0.382, 0.0058], [0.2974, 0.0054], [0.4546, 0.0352], [0.3341, 0.0061]],
          STAgent: [[0.7182, 0.145], [0.627, 0.0216], [0.658, 0.0935], [0.5976, 0.0406]],
          Biomni: [[0.8749, 0.0248], [0.5567, 0.1017], [0.6079, 0.0919], [0.5726, 0.0995]],
          GPTCellType: [[0.8763, 0.0143], [0.5525, 0.011], [0.5697, 0.0431], [0.546, 0.0042]],
          CellTypist: [[0.9038, 0.0003], [0.6414, 0.0042], [0.5987, 0.0121], [0.6092, 0.0119]],
        },
        brain: {
          TissueAgent: [[0.4958, 0.004], [0.3519, 0.0038], [0.313, 0.001], [0.3199, 0.0014]],
          SpatialAgent: [[0.455, 0], [0.102, 0.0088], [0.13, 0.0032], [0.112, 0.0053]],
          STAgent: [[0.3266, 0.1244], [0.3266, 0.0566], [0.315, 0.028], [0.2486, 0.0668]],
          Biomni: [[0.427, 0.2072], [0.187, 0.0794], [0.172, 0.0189], [0.135, 0.0568]],
          GPTCellType: [[0.4924, 0.0705], [0.2807, 0.0388], [0.2531, 0.0421], [0.228, 0.0349]],
          CellTypist: [[0.3126, 0.0042], [0.3934, 0.0236], [0.2001, 0.007], [0.2144, 0.0096]],
        },
      },
      note: "Error bars show ±1 s.d. Source: Supplementary Table S3.",
    },
    niche: {
      title: "Spatial niche annotation",
      sub: "Mean ± s.d. over three seeds. Higher is better",
      metrics: [M01("Accuracy"), M01("Macro precision"), M01("Balanced accuracy"), M01("Macro F1")],
      methods: ["TissueAgent", "SpatialAgent", "STAgent", "Biomni"],
      highlight: "TissueAgent",
      datasetLabels: { heart: "Human heart (MERFISH)", ovarian: "Ovarian cancer (Xenium)" },
      data: {
        heart: {
          TissueAgent: [[0.8273, 0.0042], [0.7192, 0.0074], [0.757, 0.0085], [0.7294, 0.008]],
          SpatialAgent: [[0.6601, 0.3068], [0.7282, 0.0272], [0.5709, 0.2863], [0.5932, 0.2161]],
          STAgent: [[0.7817, 0.0151], [0.6696, 0.0188], [0.6516, 0.0186], [0.6386, 0.0157]],
          Biomni: [[0.4901, 0.0223], [0.6067, 0.0294], [0.613, 0.0456], [0.5957, 0.038]],
        },
        ovarian: {
          TissueAgent: [[0.8995, 0.0373], [0.5541, 0.0228], [0.556, 0.0086], [0.5543, 0.0099]],
          SpatialAgent: [[0.7553, 0.0203], [0.5577, 0.0059], [0.6009, 0.0397], [0.541, 0.0041]],
          STAgent: [[0.8719, 0.0294], [0.6038, 0.0522], [0.4656, 0.0519], [0.4925, 0.0627]],
          Biomni: [[0.8986, 0.006], [0.6255, 0.1091], [0.5179, 0.0338], [0.5355, 0.0315]],
        },
      },
      note: "Error bars show ±1 s.d. Source: Supplementary Table S4.",
    },
    deconv: {
      title: "Cell-type deconvolution",
      sub: "Composite score combining RMSE, JSD, and Pearson correlation, 0–100. Agents: mean ± s.d. over five runs",
      metrics: [
        { label: "Composite score", max: 100, fmt: (v) => v.toFixed(1) },
        { label: "Runs completed", max: 100, fmt: (v) => `${v.toFixed(0)}%` },
      ],
      methods: ["TissueAgent", "cell2location", "NNLS", "Tangram", "CARD", "STAgent", "SpatialAgent", "Biomni"],
      highlight: "TissueAgent",
      datasetLabels: { dlpfc: "Visium DLPFC", merfish: "MERFISH spots" },
      naText: {
        cell2location: "Deterministic method, single run",
        NNLS: "Deterministic method, single run",
        Tangram: "Deterministic method, single run",
        CARD: "Deterministic method, single run",
      },
      data: {
        dlpfc: {
          TissueAgent: [[72.9, 0.03], [100, 0]],
          cell2location: [[72.88, 0.02], null],
          NNLS: [[68.35, 0], null],
          Tangram: [[69.62, 0.02], null],
          CARD: [[64.5, 0], null],
          STAgent: [[66.55, 3.74], [80, 0]],
          SpatialAgent: [[68.4, 2.57], [60, 0]],
          Biomni: [[67.09, 3.4], [60, 0]],
        },
        merfish: {
          TissueAgent: [[88.02, 0], [100, 0]],
          cell2location: [[79.78, 0.09], null],
          NNLS: [[88.02, 0], null],
          Tangram: [[77.88, 0.01], null],
          CARD: [[76.75, 0], null],
          STAgent: [[82.1, 10.51], [80, 0]],
          SpatialAgent: [[69.14, 15.72], [73.3, 0]],
          Biomni: [[75.76, 19.54], [80, 0]],
        },
      },
      note: "On MERFISH the router chose NNLS at every resolution, so the scores match. Source: Supplementary Table S5.",
    },
    "ccc-repro": {
      title: "Cell–cell communication: reproducibility",
      sub: "Top-K overlap of predicted interactions across repeated runs",
      metrics: [M01("Top-K overlap")],
      methods: ["TissueAgent", "SpatialAgent", "Biomni", "GPT-5.1"],
      highlight: "TissueAgent",
      data: { all: { TissueAgent: [[1, 0]], SpatialAgent: [[0.83, 0]], Biomni: [[0.38, 0]], "GPT-5.1": [[0.01, 0]] } },
      note: "GPT-5.1 chose a different method on nearly every run.",
    },
    "ccc-reliab": {
      title: "Cell–cell communication: reliability",
      sub: "Share of attempts that produced a well-formed output",
      metrics: [{ label: "Valid outputs", max: 100, fmt: (v) => `${v.toFixed(0)}%` }],
      methods: ["TissueAgent", "GPT-5.1", "SpatialAgent", "Biomni", "STAgent"],
      highlight: "TissueAgent",
      data: {
        all: {
          TissueAgent: [[100, 0]],
          "GPT-5.1": [[89, 0]],
          SpatialAgent: [[60, 0]],
          Biomni: [[42, 0]],
          STAgent: [[10, 0]],
        },
      },
      note: "Three datasets from SpatialCCCbench, within a fixed budget.",
    },
  };

  function initCharts() {
    $$("[data-chart]").forEach((node) => {
      const cfg = CHARTS[node.dataset.chart];
      if (cfg) barChart(node, cfg);
    });
  }

  /* ----------------------------------------------------------- lightbox */

  function initLightbox() {
    const dialog = $("[data-lightbox]");
    const img = $("[data-lightbox-img]", dialog);
    if (!dialog || typeof dialog.showModal !== "function") return;

    $$("[data-zoom]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const source = $("img", btn);
        img.src = source.currentSrc || source.src;
        img.alt = source.alt;
        dialog.showModal();
      });
    });
    $("[data-lightbox-close]", dialog).addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog) dialog.close();
    });
  }

  initPipeline();
  initPlan();
  initEvolve();
  initCharts();
  initLightbox();
})();
