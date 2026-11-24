import { bindThemeToggle, initializeTheme, renderThemeToggleButton } from "./ui/theme";

const theme = initializeTheme();
document.addEventListener("DOMContentLoaded", () => {
  const slot = document.querySelector<HTMLElement>("[data-customizer-theme]");
  if (!slot) return;
  const text = (key: string) =>
    key === "topbar.themeSwitchDay" ? "Switch to day theme" : "Switch to night theme";
  slot.innerHTML = renderThemeToggleButton(theme, text);
  bindThemeToggle(slot, text);
  const favicon = document.querySelector<HTMLLinkElement>("link[rel=icon]");
  if (favicon) {
    const sync = () => {
      const url = document.documentElement.dataset.theme === "night" ? favicon.dataset.night : favicon.dataset.day;
      if (url) favicon.href = url;
    };
    sync();
    slot.addEventListener("click", sync);
  }
});
