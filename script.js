const siteHeader = document.querySelector(".site-header");
const brand = document.querySelector(".brand");
const navToggle = document.querySelector(".nav-toggle");
const nav = document.querySelector(".site-nav");
const rodneyProfileImageUrl = "/assets/images/team/Rodney%20Smith.jpg";
const rodneyLinkedInUrl = "https://www.linkedin.com/in/rodney-smith-profile";
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
  // Insert after the brand ANCHOR, never after .brand-words.
  // 2026-08-19: the flat top nav moved .brand-words INSIDE the <a class="brand">
  // lockup (it used to be a sibling). Anchoring to .brand-words therefore
  // injected this chip - which contains its own <a> to LinkedIn - inside the
  // brand anchor, producing a nested <a> in <a>. Because the chip is built with
  // DOM methods rather than parsed from markup, the parser rule that would
  // normally split nested anchors never runs, so the invalid structure survives
  // into the live DOM: one click fires the LinkedIn link AND bubbles to the
  // brand link, and the browser can navigate home instead of to LinkedIn.
  // .brand still ends with the wordmark, so "afterend" on the anchor keeps the
  // chip welded to the lockup exactly as before.
  brand.insertAdjacentElement("afterend", persona);
}

// The header never hides. Past the fold it compacts and the SRS lockup
// cross-fades to the S-mark, so Book a Call stays reachable the whole page.
// The two thresholds are deliberately apart: a single one flickers when a
// scroll settles right on the boundary.
const HEADER_COMPACT_ENTER = 88;
const HEADER_COMPACT_EXIT = 56;

function updateSiteHeaderCompact() {
  if (!siteHeader) return;

  const currentScrollY = Math.max(window.scrollY, 0);
  const isCompact = siteHeader.classList.contains("is-compact");

  if (!isCompact && currentScrollY > HEADER_COMPACT_ENTER) {
    siteHeader.classList.add("is-compact");
  } else if (isCompact && currentScrollY < HEADER_COMPACT_EXIT) {
    siteHeader.classList.remove("is-compact");
  }
}

function requestSiteHeaderUpdate() {
  if (headerScrollTicking) return;

  headerScrollTicking = true;
  window.requestAnimationFrame(() => {
    updateSiteHeaderCompact();
    headerScrollTicking = false;
  });
}

function closeNav() {
  if (!nav || !navToggle) return;
  nav.classList.remove("is-open");
  document.body.classList.remove("nav-menu-open");
  navToggle.setAttribute("aria-expanded", "false");
}

if (navToggle && nav) {
  navToggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    document.body.classList.toggle("nav-menu-open", isOpen);
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      closeNav();
    });
  });
}

document.addEventListener("click", (event) => {
  if (nav && navToggle && !nav.contains(event.target) && !navToggle.contains(event.target)) {
    closeNav();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeNav();
});

window.addEventListener("scroll", requestSiteHeaderUpdate, { passive: true });

// Deep links and restored scroll positions land mid-page, so settle the
// state once at load rather than waiting for the first scroll event.
updateSiteHeaderCompact();

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
          <h2 id="booking-modal-title">Book My Call</h2>
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


// Scroll-linked tray swap: scrolling past the open Board of Advisors closes it and
// opens Trusted Partners (and reverses on the way back up). No-op on every page that
// lacks both trays or in browsers without IntersectionObserver.
//
// DESKTOP ONLY. On touch/small screens the swap collapses ~700px above the reader and
// the scroll compensation fights momentum scrolling, which feels janky. There, both
// trays stay plain tap-to-open accordions (no auto-scroll, no jump).
(function setupTraySwap() {
  if (!("IntersectionObserver" in window)) return;
  if (
    !window.matchMedia ||
    !window.matchMedia("(min-width: 768px) and (pointer: fine)").matches
  ) {
    return;
  }
  const advisors = document.getElementById("advisors-tray");
  const partners = document.getElementById("partners-tray");
  if (!advisors || !partners) return;
  const partnersSummary = partners.querySelector("summary");
  if (!partnersSummary) return;

  let partnersActive = partners.open; // true once partners is the open tray
  let autoDisabled = false; // any manual click hands control back to the user for good
  let swapping = false; // re-entrancy lock while we compensate scroll
  let lastY = window.scrollY;
  const root = document.documentElement;

  // Keep the partners summary pinned in the viewport across the open/close so the page
  // never lurches. Force instant scroll so the site's smooth scroll-behavior doesn't
  // animate the correction.
  function applySwap(openEl, closeEl) {
    swapping = true;
    const prevBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = "auto";
    const topBefore = partnersSummary.getBoundingClientRect().top;
    openEl.open = true;
    closeEl.open = false;
    const topAfter = partnersSummary.getBoundingClientRect().top;
    window.scrollBy(0, topAfter - topBefore);
    root.style.scrollBehavior = prevBehavior;
    lastY = window.scrollY;
    // Release the lock after the browser has settled the two frames of layout/scroll.
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        swapping = false;
      });
    });
  }

  function evaluate() {
    if (autoDisabled || swapping) {
      lastY = window.scrollY;
      return;
    }
    const dir = window.scrollY > lastY ? "down" : "up";
    lastY = window.scrollY;
    const top = partnersSummary.getBoundingClientRect().top;
    const line = window.innerHeight * 0.6; // trigger around the lower third
    if (!partnersActive && dir === "down" && top <= line) {
      // Don't yank a tray closed while the reader's keyboard focus lives inside it.
      if (advisors.contains(document.activeElement)) return;
      applySwap(partners, advisors);
      partnersActive = true;
    } else if (partnersActive && dir === "up" && top > line) {
      applySwap(advisors, partners);
      partnersActive = false;
    }
  }

  let ticking = false;
  window.addEventListener(
    "scroll",
    function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        evaluate();
        ticking = false;
      });
    },
    { passive: true }
  );

  // First manual toggle of either tray disables auto-control permanently.
  [advisors, partners].forEach(function (tray) {
    const summary = tray.querySelector("summary");
    if (summary) {
      summary.addEventListener("click", function () {
        autoDisabled = true;
      });
    }
  });
})();
