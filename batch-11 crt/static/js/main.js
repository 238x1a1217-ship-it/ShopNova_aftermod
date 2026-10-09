document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector("#main-nav");
  if (toggle && nav) {
    const closeMenu = () => {
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "Open navigation menu");
      nav.classList.remove("nav-open");
    };

    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      toggle.setAttribute("aria-label", expanded ? "Open navigation menu" : "Close navigation menu");
      nav.classList.toggle("nav-open", !expanded);
    });

    nav.addEventListener("click", (event) => {
      if (event.target.closest("a")) closeMenu();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeMenu();
    });
    document.addEventListener("click", (event) => {
      if (!nav.contains(event.target) && !toggle.contains(event.target)) closeMenu();
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 760) closeMenu();
    });
  }

  document.querySelectorAll(".quantity-step").forEach((button) => {
    button.addEventListener("click", () => {
      const input = button.closest(".quantity-control").querySelector('input[type="number"]');
      const step = Number(button.dataset.step);
      const minimum = Number(input.min) || 1;
      const maximum = Number(input.max) || Number.MAX_SAFE_INTEGER;
      input.value = String(Math.min(maximum, Math.max(minimum, Number(input.value || minimum) + step)));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
  });

  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
      button.setAttribute("aria-label", `${show ? "Hide" : "Show"} password`);
    });
  });

  document.querySelectorAll(".message-dismiss").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest(".message").remove();
    });
  });

  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll("[data-loading-form]").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector('button[type="submit"]');
      if (!button || button.disabled) return;
      button.disabled = true;
      button.dataset.originalText = button.textContent.trim();
      button.textContent = "Please wait…";
      button.setAttribute("aria-busy", "true");
    });
  });
});
