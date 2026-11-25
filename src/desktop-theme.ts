import { bindThemeToggle, initializeTheme, renderThemeToggleButton } from "./ui/theme";

import { CircleHelp, X } from "lucide";
import { renderIcon } from "./ui/icons";

const theme = initializeTheme();
document.addEventListener("DOMContentLoaded", () => {
  const slot = document.querySelector<HTMLElement>("[data-customizer-theme]");
  if (!slot) return;
  const text = (key: string) =>
    key === "topbar.themeSwitchDay" ? "Switch to day theme" : "Switch to night theme";
  slot.innerHTML = renderThemeToggleButton(theme, text);
  bindThemeToggle(slot, text);
  const help = document.querySelector<HTMLDialogElement>("#customizer-help")!;
  const helpButton = document.querySelector<HTMLButtonElement>("[data-help]")!;
  helpButton.innerHTML = renderIcon(CircleHelp);
  help.querySelector("[data-help-close]")!.innerHTML = renderIcon(X);
  helpButton.addEventListener("click", () => help.showModal());
  help.addEventListener("close", () => helpButton.focus());
  help.addEventListener("click", event => { if (event.target === help) help.close(); });

  const favicon = document.querySelector<HTMLLinkElement>("link[rel=icon]");
  if (favicon) {
    const sync = () => {
      const url = document.documentElement.dataset.theme === "night" ? favicon.dataset.night : favicon.dataset.day;
      if (url) favicon.href = url;
    };
    sync();
    slot.addEventListener("click", sync);
  }

  const folder = document.querySelector<HTMLInputElement>("#field-folder");
  const folderAction = document.querySelector<HTMLButtonElement>("[data-folder-action]");
  if (folder && folderAction) {
    const current = folder.form?.querySelector<HTMLInputElement>('[name="current"]')?.value;
    folder.addEventListener("input", () => {
      folderAction.textContent = folder.value === current ? "Reload configuration" : "Use folder";
    });
  }

  const status = document.querySelector<HTMLElement>("[data-connection-status]");
  if (!status) return;
  let pending = false;
  async function refresh() {
    if (!status || document.hidden || pending) return;
    pending = true;
    let connected = false;
    let label = "Disconnected";
    try {
      const reply = await fetch("/connection-status", { mode: "same-origin", cache: "no-store" });
      if (!reply.ok) throw Error();
      const current = await reply.json();
      connected = current.connected && current.instance === status.dataset.instance;
      if (connected) label = "Connected";
    } catch {
      label = "Unavailable";
    } finally {
      pending = false;
    }
    status.dataset.state = connected ? "ready" : "checking";
    if (status.textContent !== label) status.textContent = label;
  }
  document.addEventListener("visibilitychange", refresh);
  window.setInterval(refresh, 3000);
});
