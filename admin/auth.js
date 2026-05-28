if (sessionStorage.getItem("srsAdminAuthed") !== "true") {
  window.location.replace("../?admin=required");
}
