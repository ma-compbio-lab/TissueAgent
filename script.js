/* TissueAgent project page: scroll reveal, count-up highlights, figure zoom, section spy. */
(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* Blocks below the fold fade up once, as they scroll into view. */
  const revealables = $$(".reveal");
  if (reduceMotion || !("IntersectionObserver" in window)) {
    revealables.forEach((el) => el.classList.add("is-in"));
  } else {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-in");
          io.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );
    revealables.forEach((el) => io.observe(el));
  }

  /* At a Glance numbers count up when first shown. */
  const counters = $$("[data-count]");
  const format = (el, v) => v.toFixed(Number(el.dataset.decimals || 0)) + (el.dataset.suffix || "");
  if (!reduceMotion && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          io.unobserve(entry.target);
          const el = entry.target;
          const target = Number(el.dataset.count);
          const t0 = performance.now();
          const tick = (now) => {
            const p = Math.min(1, (now - t0) / 1100);
            el.textContent = format(el, target * (1 - Math.pow(1 - p, 3)));
            if (p < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        });
      },
      { threshold: 0.6 }
    );
    counters.forEach((el) => {
      el.textContent = format(el, 0);
      io.observe(el);
    });
  }

  /* Click a figure to view it larger. */
  const dialog = document.querySelector("[data-lightbox]");
  if (dialog && typeof dialog.showModal === "function") {
    const big = dialog.querySelector("[data-lightbox-img]");
    $$(".paper-figure-full img").forEach((img) => {
      img.tabIndex = 0;
      img.setAttribute("role", "button");
      const open = () => {
        big.src = img.currentSrc || img.src;
        big.alt = img.alt;
        dialog.showModal();
      };
      img.addEventListener("click", open);
      img.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open();
        }
      });
    });
    dialog.querySelector("[data-lightbox-close]").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog) dialog.close();
    });
  }

  /* Highlight the topbar link for the section in view. */
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
})();
