/* =========================================================================
   Python под капотом — runtime hooks
   1. Mark elements containing ⚠️ emoji with [data-warn="true"]
      → CSS paints them as soft yellow callouts.
   ========================================================================= */

(function () {
  "use strict";

  /**
   * Walk the DOM inside .md-typeset and tag any blockquote / li / p
   * whose text content includes the ⚠️ warning emoji.
   *
   * We intentionally skip <pre><code> blocks — pygments outputs each line
   * as a <span>, and tagging individual lines would break syntax highlighting.
   * The emoji remains visible inside code; we just don't yellow-tint it.
   */
  function tagWarnings() {
    const root = document.querySelector(".md-typeset");
    if (!root) return;

    // U+26A0 U+FE0F = ⚠️ (warning sign + variation selector)
    const WARN_EMOJI = "\u26A0\uFE0F";
    // Also catch bare ⚠ without selector (some fonts render without VS16)
    const WARN_BARE = "\u26A0";

    const candidates = root.querySelectorAll("blockquote, li, p");
    candidates.forEach(function (el) {
      // Skip if inside a <pre> (code block)
      if (el.closest("pre")) return;
      // Skip if already tagged (idempotent on re-runs)
      if (el.hasAttribute("data-warn")) return;

      const text = el.textContent || "";
      if (text.includes(WARN_EMOJI) || text.includes(WARN_BARE)) {
        el.setAttribute("data-warn", "true");
      }
    });
  }

  // Run on initial load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tagWarnings);
  } else {
    tagWarnings();
  }

  // Re-run when MkDocs Material swaps page content (instant navigation)
  document.addEventListener("DOMContentSwap", tagWarnings);

  // MutationObserver — catches dynamically rendered content
  const observer = new MutationObserver(function (mutations) {
    let needsCheck = false;
    for (const m of mutations) {
      if (m.addedNodes.length > 0) {
        needsCheck = true;
        break;
      }
    }
    if (needsCheck) {
      // Debounce — tagWarnings is cheap but no need to run on every mutation
      clearTimeout(window.__pyWarnTimer);
      window.__pyWarnTimer = setTimeout(tagWarnings, 100);
    }
  });

  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener("DOMContentLoaded", function () {
      observer.observe(document.body, { childList: true, subtree: true });
    });
  }
})();
