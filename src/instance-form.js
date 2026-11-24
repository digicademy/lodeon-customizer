// Switching instance returns to the overview. Preserve edits if the user cancels.
(() => {
  const connection = document.querySelector(".instance-connection");
  if (!connection) return;
  const forms = [...document.querySelectorAll("main form")];
  const snapshot = form => new URLSearchParams(new FormData(form)).toString();
  const initial = forms.map(snapshot);
  connection.addEventListener("submit", event => {
    if (forms.some((form, index) => snapshot(form) !== initial[index]) &&
        !window.confirm("Discard your unsaved edits and save the instance connection?")) {
      event.preventDefault();
    }
  });
})();
