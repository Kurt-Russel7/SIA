// Small client-side behaviours that don't need a server round-trip.
(function () {
  // ---- Mobile sidebar -----------------------------------------------------
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("backdrop");
  const menuBtn = document.getElementById("menu-btn");

  function setSidebar(open) {
    sidebar.classList.toggle("open", open);
    backdrop.hidden = !open;
    menuBtn.setAttribute("aria-expanded", String(open));
  }
  menuBtn.addEventListener("click", () => setSidebar(true));
  backdrop.addEventListener("click", () => setSidebar(false));

  // ---- Notifications popover ----------------------------------------------
  const notifBtn = document.getElementById("notif-btn");
  const notifPanel = document.getElementById("notif-panel");

  function setNotif(open) {
    notifPanel.hidden = !open;
    notifBtn.setAttribute("aria-expanded", String(open));
  }
  notifBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    setNotif(notifPanel.hidden);
  });
  document.addEventListener("click", (e) => {
    if (!notifPanel.hidden && !notifPanel.contains(e.target)) setNotif(false);
  });

  // ---- Keyboard: Esc closes, Ctrl/⌘+K focuses search ----------------------
  const search = document.getElementById("search");
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      setNotif(false);
      setSidebar(false);
    }
  });

  // ---- CSV import: submit as soon as a file is picked or dropped ----------
  const form = document.getElementById("import-form");
  const input = document.getElementById("dataset-input");
  if (form && input) {
    const title = document.getElementById("dropzone-title");
    const btnText = document.getElementById("dropzone-btn-text");

    function submit() {
      if (!input.files.length) return;
      title.textContent = "Validating passenger records...";
      btnText.textContent = "Processing...";
      form.submit();
    }
    input.addEventListener("change", submit);

    ["dragenter", "dragover"].forEach((type) =>
      form.addEventListener(type, (e) => {
        e.preventDefault();
        form.classList.add("dragover");
      })
    );
    ["dragleave", "drop"].forEach((type) =>
      form.addEventListener(type, (e) => {
        e.preventDefault();
        form.classList.remove("dragover");
      })
    );
    form.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        submit();
      }
    });
  }
})();
