// The form inputs remain the source of the worker, candidate and fallback order.
(() => {
  const form = document.querySelector('form[action="/broker"]');
  const pool = form.querySelector("[data-pool]");
  const memberFields = form.querySelector(".broker-members");
  const zones = [...form.querySelectorAll(".route-zone")];
  const status = form.querySelector("[data-routing-status]");
  let members = new Map();
  let selected = "";
  let drag = null;

  function input(zone) { return zone.querySelector("[data-manual] input"); }
  function ids(zone) { return input(zone).value.split(",").map(id => id.trim()).filter(Boolean); }
  function fixed(zone) {
    return zone.dataset.role === "workers" && zone.closest("[data-task]").querySelector("select").value === "fixed";
  }
  function title(zone) {
    return zone.dataset.role === "fallbacks" ? "Fallbacks" : fixed(zone) ? "Worker" : "Candidates";
  }
  function context(zone) { return zone.closest("[data-task]").dataset.task + " " + title(zone).toLowerCase(); }
  function button(text, label, action) {
    const element = document.createElement("button");
    element.type = "button";
    element.className = "ld-button";
    element.textContent = text;
    element.setAttribute("aria-label", label);
    element.title = label;
    element.addEventListener("click", action);
    return element;
  }

  function renderZone(zone) {
    const label = title(zone);
    zone.querySelector("strong").textContent = label;
    const assign = zone.querySelector("[data-assign]");
    assign.hidden = false;
    assign.disabled = !members.has(selected);
    assign.setAttribute("aria-label", "Assign selected model to " + context(zone));
    const list = zone.querySelector("[data-assignments]");
    list.replaceChildren();
    const ordered = ids(zone);
    for (const [index, id] of ordered.entries()) {
      const chip = document.createElement("span");
      chip.className = "route-chip";
      chip.draggable = true;
      chip.dataset.model = id;
      const name = document.createElement("span");
      name.textContent = members.get(id) || id;
      name.title = id;
      chip.append(name);
      if (index > 0) {
        chip.append(button("←", "Move " + id + " earlier in " + context(zone), () => {
          place(id, zone, zone, ordered[index - 1], false);
          focusAssignment(zone, id);
        }));
      }
      chip.append(button("×", "Remove " + id + " from " + context(zone), () => {
        remove(zone, id);
        focusAssignment(zone, ids(zone)[Math.min(index, ids(zone).length - 1)]);
      }));
      list.append(chip);
    }
    if (!ordered.length) list.textContent = label === "Fallbacks" ? "Drop fallbacks here (optional)" :
      fixed(zone) ? "Drop one worker here" : "Drop candidates here in order";
  }

  function focusAssignment(zone, id) {
    const next = [...zone.querySelectorAll("[data-model]")].find(chip => chip.dataset.model === id);
    (next?.querySelector("button") || zone).focus();
  }
  function update(zone, values) {
    input(zone).value = values.join(", ");
    renderZone(zone);
  }
  function remove(zone, id) {
    update(zone, ids(zone).filter(value => value !== id));
    status.textContent = "Removed " + id + " from " + context(zone) + ".";
  }
  function place(id, source, zone, neighbour, after) {
    if (!members.has(id) || (source === zone && id === neighbour)) return;
    const ordered = ids(zone).filter(value => value !== id);
    const index = ordered.indexOf(neighbour);
    ordered.splice(index < 0 ? ordered.length : index + Number(after), 0, id);
    if (source && source !== zone) remove(source, id);
    update(zone, fixed(zone) ? [id] : ordered);
    status.textContent = "Assigned " + id + " to " + context(zone) + ".";
  }

  function refreshMembers() {
    const next = new Map();
    for (const checkbox of memberFields.querySelectorAll("[data-model-name]")) {
      const id = checkbox.name.slice("member.".length);
      const row = checkbox.closest("label");
      row.draggable = checkbox.checked;
      if (checkbox.checked) {
        next.set(id, checkbox.dataset.modelName);
        row.dataset.model = id;
      } else {
        delete row.dataset.model;
      }
    }
    for (const line of form.elements.members.value.split(/\r?\n/)) {
      const id = line.split("|", 1)[0].trim();
      if (/^[A-Za-z][A-Za-z0-9_-]*$/.test(id) && !next.has(id)) next.set(id, id);
    }
    const router = form.elements.router;
    if (members.has(router.value) && !next.has(router.value)) router.value = "";
    members = next;
    if (!members.has(selected)) selected = "";
    const palette = pool.querySelector("[data-palette]");
    palette.replaceChildren();
    for (const [id, label] of members) {
      const chip = button(label, label + " (" + id + ")", () => {
        selected = selected === id ? "" : id;
        for (const item of palette.children) item.setAttribute("aria-pressed", String(item.dataset.model === selected));
        zones.forEach(renderZone);
      });
      chip.classList.add("pool-chip");
      chip.draggable = true;
      chip.dataset.model = id;
      chip.setAttribute("aria-pressed", String(selected === id));
      palette.append(chip);
    }
    if (!members.size) palette.textContent = "Select broker members above.";
    for (const zone of zones) {
      update(zone, ids(zone).filter(id => members.has(id)));
    }
  }

  for (const zone of zones) {
    zone.tabIndex = -1;
    zone.querySelector("[data-manual]").hidden = true;
    zone.querySelector("[data-assign]").addEventListener("click", () => place(selected, null, zone));
  }
  memberFields.addEventListener("change", refreshMembers);
  for (const task of form.querySelectorAll("[data-task]")) {
    const zone = task.querySelector('[data-role="workers"]');
    task.querySelector("select").addEventListener("change", () => {
      const assigned = ids(zone);
      // A fixed task with several previous candidates needs an explicit choice.
      update(zone, fixed(zone) && assigned.length > 1 ? [] : assigned);
    });
  }

  form.addEventListener("dragstart", event => {
    const chip = event.target.closest("[data-model]");
    if (!chip || !members.has(chip.dataset.model)) return;
    drag = {id: chip.dataset.model, source: chip.closest(".route-zone")};
    event.dataTransfer.effectAllowed = drag.source ? "move" : "copy";
    event.dataTransfer.setData("text/plain", drag.id);
  });
  function dropTarget(event) {
    return drag && event.target.closest(".route-zone, [data-pool], .broker-members");
  }
  function clearHighlight() {
    form.querySelector(".drag-over")?.classList.remove("drag-over");
  }
  function acceptDrop(event) {
    const target = dropTarget(event);
    clearHighlight();
    if (!target || (!drag.source && !target.matches(".route-zone"))) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = drag.source ? "move" : "copy";
    target.classList.add("drag-over");
  }
  form.addEventListener("dragenter", acceptDrop);
  form.addEventListener("dragover", acceptDrop);
  form.addEventListener("dragleave", event => {
    if (!event.target.closest(".drag-over")?.contains(event.relatedTarget)) clearHighlight();
  });
  form.addEventListener("drop", event => {
    const target = dropTarget(event);
    if (!target) return;
    event.preventDefault();
    clearHighlight();
    const {id, source} = drag;
    drag = null;
    if (!target.matches(".route-zone")) {
      if (source) remove(source, id);
      return;
    }
    const chip = event.target.closest("[data-model]");
    const box = chip?.getBoundingClientRect();
    place(id, source, target, chip?.dataset.model, box && event.clientX >= box.left + box.width / 2);
  });
  form.addEventListener("dragend", () => { drag = null; clearHighlight(); });
  form.addEventListener("submit", event => {
    if (!members.size) return; // The server reports missing broker members.
    const empty = zones.find(zone => zone.dataset.role === "workers" && !ids(zone).length);
    if (empty) {
      event.preventDefault();
      empty.querySelector("[data-assignments]").textContent = "Assign a model before saving.";
      empty.focus();
    }
  });
  pool.hidden = false;
  refreshMembers();
})();
