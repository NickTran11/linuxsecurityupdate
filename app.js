(async function () {
  const yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // File size (best-effort; some hosts block HEAD)
  const sizeEl = document.getElementById("size");
  const downloadBtn = document.getElementById("downloadBtn");
  if (sizeEl && downloadBtn) {
    try {
      const res = await fetch(downloadBtn.getAttribute("href"), { method: "HEAD" });
      const len = res.headers.get("content-length");
      if (len) {
        const bytes = Number(len);
        const kb = (bytes / 1024);
        const mb = kb / 1024;
        sizeEl.textContent = mb >= 1 ? `${mb.toFixed(2)} MB` : `${kb.toFixed(1)} KB`;
      } else {
        sizeEl.textContent = "—";
      }
    } catch {
      sizeEl.textContent = "—";
    }
  }

  // Copy download link
  const copyLinkBtn = document.getElementById("copyLinkBtn");
  if (copyLinkBtn && downloadBtn) {
    copyLinkBtn.addEventListener("click", async () => {
      const url = new URL(downloadBtn.getAttribute("href"), window.location.href).toString();
      try {
        await navigator.clipboard.writeText(url);
        copyLinkBtn.textContent = "Copied!";
        setTimeout(() => (copyLinkBtn.textContent = "Copy download link"), 1200);
      } catch {
        alert("Could not copy. Your browser may block clipboard access.");
      }
    });
  }

  // Copy quick command
  document.querySelectorAll(".copy").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const target = btn.getAttribute("data-copy");
      const ta = document.querySelector(target);
      if (!ta) return;
      try {
        await navigator.clipboard.writeText(ta.value.trim());
        btn.textContent = "Copied!";
        setTimeout(() => (btn.textContent = "Copy"), 1200);
      } catch {
        alert("Could not copy to clipboard.");
      }
    });
  });
})();
