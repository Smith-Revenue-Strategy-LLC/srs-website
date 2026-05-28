const adminOpenButton = document.querySelector("[data-admin-open]");
const adminModal = document.querySelector("[data-admin-modal]");
const adminCloseButton = document.querySelector("[data-admin-close]");
const adminForm = document.querySelector("[data-admin-form]");
const adminStatus = document.querySelector("[data-admin-status]");

function openAdminModal() {
  if (!adminModal) return;
  adminModal.hidden = false;
  adminStatus.textContent = "";
  adminForm?.elements.username.focus();
}

function closeAdminModal() {
  if (!adminModal) return;
  adminModal.hidden = true;
  adminForm?.reset();
  adminOpenButton?.focus();
}

adminOpenButton?.addEventListener("click", openAdminModal);
adminCloseButton?.addEventListener("click", closeAdminModal);

adminModal?.addEventListener("click", (event) => {
  if (event.target === adminModal) {
    closeAdminModal();
  }
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && adminModal && !adminModal.hidden) {
    closeAdminModal();
  }
});

adminForm?.addEventListener("submit", (event) => {
  event.preventDefault();

  const formData = new FormData(adminForm);
  const username = String(formData.get("username") || "").trim();
  const password = String(formData.get("password") || "");

  if (username === "Rodney" && password === "Consult") {
    sessionStorage.setItem("srsAdminAuthed", "true");
    window.location.href = "admin/";
    return;
  }

  adminStatus.textContent = "The username or password is incorrect.";
});
