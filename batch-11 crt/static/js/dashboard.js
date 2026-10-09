document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".sidebar-toggle");
  const sidebar = document.querySelector("#dashboard-sidebar");

  if (toggle && sidebar) {
    const closeSidebar = () => {
      sidebar.classList.remove("sidebar-open");
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "Open dashboard navigation");
    };

    toggle.addEventListener("click", () => {
      const open = toggle.getAttribute("aria-expanded") === "true";
      sidebar.classList.toggle("sidebar-open", !open);
      toggle.setAttribute("aria-expanded", String(!open));
      toggle.setAttribute("aria-label", open ? "Open dashboard navigation" : "Close dashboard navigation");
    });

    document.addEventListener("click", (event) => {
      if (!sidebar.contains(event.target) && !toggle.contains(event.target)) closeSidebar();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeSidebar();
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 900) closeSidebar();
    });
  }

  document.querySelectorAll(".dashboard-message-close").forEach((button) => {
    button.addEventListener("click", () => button.closest(".dashboard-message").remove());
  });

  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll(".inventory-update-form, .inline-status-form").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector('button[type="submit"]');
      if (button) {
        button.disabled = true;
        button.textContent = "…";
      }
    });
  });
});
