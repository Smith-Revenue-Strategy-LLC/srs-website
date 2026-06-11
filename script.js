const siteHeader = document.querySelector(".site-header");
const brand = document.querySelector(".brand");
const navToggle = document.querySelector(".nav-toggle");
const nav = document.querySelector(".site-nav");
const navMenus = document.querySelectorAll(".nav-menu");
const rodneyProfileImageUrl = "/assets/images/team/Rodney%20Smith.jpg";
const rodneyLinkedInUrl = "https://www.linkedin.com/in/rodney-smith-profile";
let lastHeaderScrollY = window.scrollY;
let headerScrollTicking = false;

function linkedInIconMarkup(className) {
  return `
    <a
      class="linkedin-link ${className}"
      href="${rodneyLinkedInUrl}"
      target="_blank"
      rel="noopener noreferrer"
      aria-label="View Rodney Smith on LinkedIn"
      title="View Rodney Smith on LinkedIn"
    >
      in
    </a>
  `;
}

function createHeaderPersona() {
  if (!siteHeader || !brand || document.querySelector("[data-header-persona]")) return;

  const persona = document.createElement("div");
  persona.className = "header-persona";
  persona.dataset.headerPersona = "";
  persona.innerHTML = `
    <img
      class="profile-photo-mini header-profile-photo"
      src="${rodneyProfileImageUrl}"
      alt="Rodney Smith"
      width="80"
      height="80"
    >
    ${linkedInIconMarkup("header-linkedin")}
  `;
  brand.insertAdjacentElement("afterend", persona);
}

function revealSiteHeader() {
  siteHeader?.classList.remove("is-hidden");
}

function siteHeaderShouldStayVisible() {
  return (
    !siteHeader ||
    window.scrollY <= 96 ||
    nav?.classList.contains("is-open") ||
    document.body.classList.contains("booking-modal-open")
  );
}

function updateSiteHeaderVisibility() {
  if (!siteHeader) return;

  const currentScrollY = Math.max(window.scrollY, 0);
  const scrollDelta = currentScrollY - lastHeaderScrollY;

  if (siteHeaderShouldStayVisible()) {
    revealSiteHeader();
    lastHeaderScrollY = currentScrollY;
    return;
  }

  if (Math.abs(scrollDelta) < 8) return;

  siteHeader.classList.toggle("is-hidden", scrollDelta > 0);
  lastHeaderScrollY = currentScrollY;
}

function requestSiteHeaderUpdate() {
  if (headerScrollTicking) return;

  headerScrollTicking = true;
  window.requestAnimationFrame(() => {
    updateSiteHeaderVisibility();
    headerScrollTicking = false;
  });
}

function closeNav() {
  if (!nav || !navToggle) return;
  nav.classList.remove("is-open");
  navToggle.setAttribute("aria-expanded", "false");
  navMenus.forEach((menu) => {
    menu.classList.remove("is-open");
    menu.querySelector(".nav-menu-button")?.setAttribute("aria-expanded", "false");
  });
}

if (navToggle && nav) {
  navToggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
    if (isOpen) revealSiteHeader();
  });

  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      closeNav();
    });
  });
}

navMenus.forEach((menu) => {
  const button = menu.querySelector(".nav-menu-button");
  if (!button) return;

  button.addEventListener("click", (event) => {
    event.stopPropagation();
    const isOpen = menu.classList.toggle("is-open");
    button.setAttribute("aria-expanded", String(isOpen));
  });
});

document.addEventListener("click", (event) => {
  if (nav && navToggle && !nav.contains(event.target) && !navToggle.contains(event.target)) {
    closeNav();
    return;
  }

  navMenus.forEach((menu) => {
    if (menu.contains(event.target)) return;
    menu.classList.remove("is-open");
    menu.querySelector(".nav-menu-button")?.setAttribute("aria-expanded", "false");
  });
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeNav();
});

window.addEventListener("scroll", requestSiteHeaderUpdate, { passive: true });

createHeaderPersona();

const bookingUrl =
  "https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ2mSMpkde6JzlfVSu2HEvnWfhKFofDRUU7D1ly8uAUcfrHj6R1kZdg61wH2XZJKWkzP5kmaKElU";
const bookingEmbedUrl =
  "https://calendar.google.com/calendar/appointments/schedules/AcZssZ2mSMpkde6JzlfVSu2HEvnWfhKFofDRUU7D1ly8uAUcfrHj6R1kZdg61wH2XZJKWkzP5kmaKElU";
const visibleBookingTriggers = Array.from(document.querySelectorAll("[data-booking-open]"));
let stickyBookingCta = null;
let stickyBookingButton = null;
const visibleBookingTriggerSet = new Set();
let bookingModal = document.querySelector("[data-booking-modal]");
let bookingClose = null;
let bookingReturnTarget = null;

function createStickyBookingCta() {
  const cta = document.createElement("aside");
  cta.className = "sticky-booking-cta";
  cta.dataset.stickyBookingCta = "";
  cta.setAttribute("aria-label", "Book a call with Rodney");
  cta.setAttribute("aria-hidden", "true");
  cta.innerHTML = `
    <div class="sticky-booking-persona">
      <img
        class="profile-photo-mini sticky-booking-photo"
        src="${rodneyProfileImageUrl}"
        alt="Rodney Smith"
        width="80"
        height="80"
      >
      ${linkedInIconMarkup("sticky-linkedin")}
    </div>
    <p>
      <span>Ready for a practical conversation?</span>
      <strong>Meet with Rodney.</strong>
    </p>
    <button class="button primary sticky-booking-button" type="button" data-booking-open>
      Book a Call
    </button>
  `;
  document.body.append(cta);
  return cta;
}

if (visibleBookingTriggers.length) {
  stickyBookingCta = createStickyBookingCta();
  stickyBookingButton = stickyBookingCta.querySelector("[data-booking-open]");
  stickyBookingButton.tabIndex = -1;
}

const bookingOpenButtons = stickyBookingButton
  ? [...visibleBookingTriggers, stickyBookingButton]
  : visibleBookingTriggers;

function setStickyBookingCtaVisible(isVisible) {
  if (!stickyBookingCta || !stickyBookingButton) return;
  stickyBookingCta.classList.toggle("is-visible", isVisible);
  stickyBookingCta.setAttribute("aria-hidden", String(!isVisible));
  stickyBookingButton.tabIndex = isVisible ? 0 : -1;
}

function updateStickyBookingCta() {
  const modalIsOpen = Boolean(bookingModal && !bookingModal.hidden);
  setStickyBookingCtaVisible(!modalIsOpen && visibleBookingTriggerSet.size === 0);
}

function triggerIsInViewport(trigger) {
  const rect = trigger.getBoundingClientRect();
  return (
    rect.width > 0 &&
    rect.height > 0 &&
    rect.bottom > 0 &&
    rect.right > 0 &&
    rect.top < window.innerHeight &&
    rect.left < window.innerWidth
  );
}

function setupStickyBookingCta() {
  if (!stickyBookingCta || !visibleBookingTriggers.length) return;

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            visibleBookingTriggerSet.add(entry.target);
            return;
          }

          visibleBookingTriggerSet.delete(entry.target);
        });

        updateStickyBookingCta();
      },
      { threshold: 0.01 }
    );

    visibleBookingTriggers.forEach((trigger) => {
      if (triggerIsInViewport(trigger)) visibleBookingTriggerSet.add(trigger);
      observer.observe(trigger);
    });
    updateStickyBookingCta();
    return;
  }

  const checkVisibleTriggers = () => {
    visibleBookingTriggerSet.clear();
    visibleBookingTriggers.forEach((trigger) => {
      if (triggerIsInViewport(trigger)) visibleBookingTriggerSet.add(trigger);
    });
    updateStickyBookingCta();
  };

  window.addEventListener("scroll", checkVisibleTriggers, { passive: true });
  window.addEventListener("resize", checkVisibleTriggers);
  checkVisibleTriggers();
}

function createBookingModal() {
  const modal = document.createElement("div");
  modal.className = "booking-modal";
  modal.dataset.bookingModal = "";
  modal.hidden = true;
  modal.innerHTML = `
    <div
      class="booking-modal-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="booking-modal-title"
    >
      <div class="booking-modal-header">
        <div>
          <p class="eyebrow">Complimentary connect call</p>
          <h2 id="booking-modal-title">Book My Free Call</h2>
        </div>
        <button class="booking-modal-close" type="button" aria-label="Close booking calendar" data-booking-close>
          &times;
        </button>
      </div>
      <iframe
        class="booking-calendar"
        src="${bookingEmbedUrl}"
        title="Book a call with Smith Revenue Strategy"
        loading="lazy"
      ></iframe>
      <a
        class="booking-fallback"
        href="${bookingUrl}"
        target="_blank"
        rel="noopener noreferrer"
      >
        Open booking calendar in a new window
      </a>
    </div>
  `;
  document.body.append(modal);
  return modal;
}

if (bookingOpenButtons.length && !bookingModal) {
  bookingModal = createBookingModal();
}

if (bookingModal) {
  bookingClose = bookingModal.querySelector("[data-booking-close]");
}

function closeBookingModal() {
  if (!bookingModal) return;
  bookingModal.hidden = true;
  document.body.classList.remove("booking-modal-open");
  updateStickyBookingCta();
  bookingReturnTarget?.focus();
}

function openBookingModal(trigger) {
  if (!bookingModal) return;
  bookingReturnTarget = trigger;
  bookingModal.hidden = false;
  document.body.classList.add("booking-modal-open");
  revealSiteHeader();
  updateStickyBookingCta();
  bookingClose?.focus();
}

bookingOpenButtons.forEach((button) => {
  button.addEventListener("click", (event) => {
    event.preventDefault();
    closeNav();
    openBookingModal(button);
  });

  button.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    closeNav();
    openBookingModal(button);
  });
});

bookingClose?.addEventListener("click", closeBookingModal);

bookingModal?.addEventListener("click", (event) => {
  if (event.target === bookingModal) closeBookingModal();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && bookingModal && !bookingModal.hidden) {
    closeBookingModal();
  }
});

setupStickyBookingCta();

const canvas = document.querySelector("#flow-canvas");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (canvas) {
  const ctx = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  let tick = 0;

  const nodes = [
    { x: 0.18, y: 0.2, label: "CRM" },
    { x: 0.38, y: 0.16, label: "OPS" },
    { x: 0.68, y: 0.28, label: "AI" },
    { x: 0.26, y: 0.55, label: "DATA" },
    { x: 0.52, y: 0.62, label: "LOGIC" },
    { x: 0.78, y: 0.76, label: "REVENUE" }
  ];

  const links = [
    [0, 1],
    [1, 2],
    [0, 3],
    [3, 4],
    [2, 4],
    [4, 5]
  ];

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const scale = window.devicePixelRatio || 1;
    width = Math.max(1, rect.width);
    height = Math.max(1, rect.height);
    canvas.width = width * scale;
    canvas.height = height * scale;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
  }

  function drawGrid() {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#020711";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(127,199,154,0.07)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x += 38) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += 38) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }

  function nodePoint(node) {
    return { x: node.x * width, y: node.y * height };
  }

  function drawLinks() {
    links.forEach(([from, to], index) => {
      const a = nodePoint(nodes[from]);
      const b = nodePoint(nodes[to]);
      const pulse = (Math.sin(tick * 0.035 + index) + 1) / 2;

      ctx.strokeStyle = "rgba(127,199,154,0.24)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      const midX = (a.x + b.x) / 2;
      ctx.bezierCurveTo(midX, a.y, midX, b.y, b.x, b.y);
      ctx.stroke();

      const px = a.x + (b.x - a.x) * pulse;
      const py = a.y + (b.y - a.y) * pulse;
      ctx.fillStyle = index === links.length - 1 ? "#f0cf73" : "#7fc79a";
      ctx.beginPath();
      ctx.arc(px, py, 4, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawNodes() {
    nodes.forEach((node, index) => {
      const point = nodePoint(node);
      const radius = index === 2 || index === 5 ? 38 : 30;

      ctx.fillStyle = "#071f17";
      ctx.beginPath();
      ctx.roundRect(point.x - radius, point.y - radius, radius * 2, radius * 2, 8);
      ctx.fill();

      ctx.strokeStyle = index === 2 ? "#7fc79a" : index === 5 ? "#f0cf73" : "#9ed2df";
      ctx.lineWidth = 3;
      ctx.stroke();

      ctx.fillStyle = "#f7f5f0";
      ctx.font = "800 12px ui-monospace, SFMono-Regular, Consolas, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(node.label, point.x, point.y);
    });
  }

  function drawCapacityMeter() {
    const x = width * 0.12;
    const y = height * 0.9;
    const w = width * 0.72;
    const h = 14;
    const fill = reduceMotion ? 0.72 : 0.66 + Math.sin(tick * 0.025) * 0.08;

    ctx.fillStyle = "rgba(127,199,154,0.1)";
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 7);
    ctx.fill();

    const gradient = ctx.createLinearGradient(x, y, x + w, y);
    gradient.addColorStop(0, "#9ed2df");
    gradient.addColorStop(0.55, "#7fc79a");
    gradient.addColorStop(1, "#f0cf73");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.roundRect(x, y, w * fill, h, 7);
    ctx.fill();

    ctx.fillStyle = "rgba(158,210,223,0.9)";
    ctx.font = "700 11px ui-monospace, SFMono-Regular, Consolas, monospace";
    ctx.textAlign = "left";
    ctx.fillText("OPERATING BURDEN REDUCED", x, y - 12);
  }

  function render() {
    drawGrid();
    drawLinks();
    drawNodes();
    drawCapacityMeter();
    tick += 1;
    if (!reduceMotion) requestAnimationFrame(render);
  }

  window.addEventListener("resize", () => {
    resizeCanvas();
    if (reduceMotion) render();
  });

  resizeCanvas();
  render();
}
