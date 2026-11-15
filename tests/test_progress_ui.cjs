"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "PROGRESS.html"), "utf8");
const script = fs.readFileSync(path.join(root, "progress.js"), "utf8");

function makeElement({ filter, status, active = false } = {}) {
  const classes = new Set(active ? ["active"] : []);
  const countNode = { textContent: "" };
  return {
    dataset: filter ? { filter } : status ? { status } : {},
    hidden: false,
    disabled: false,
    textContent: "",
    className: "",
    attributes: {},
    listeners: {},
    countNode,
    classList: {
      contains: (name) => classes.has(name),
      add: (name) => classes.add(name),
      remove: (name) => classes.delete(name),
      toggle(name, force) {
        const enabled = force === undefined ? !classes.has(name) : Boolean(force);
        if (enabled) classes.add(name);
        else classes.delete(name);
        return enabled;
      },
    },
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
    removeAttribute(name) {
      delete this.attributes[name];
    },
    addEventListener(name, callback) {
      (this.listeners[name] ||= []).push(callback);
    },
    querySelector(selector) {
      return selector === "[data-count]" ? countNode : null;
    },
  };
}

async function waitFor(predicate, description) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    if (predicate()) return;
    await new Promise((resolve) => setImmediate(resolve));
  }
  assert.fail("Timed out waiting for " + description);
}

async function main() {
  const statuses = [...html.matchAll(/<article class="item [^"]+" data-status="([^"]+)"/g)]
    .map((match) => match[1]);
  const filters = [...html.matchAll(/<button[^>]*data-filter="([^"]+)"[^>]*>/g)]
    .map((match) => match[1]);
  const allowed = new Set(["done", "active", "blocked", "planned"]);
  assert.ok(statuses.length > 0, "milestone cards must exist");
  assert.ok(statuses.every((state) => allowed.has(state)), "every card must have a known state");
  assert.deepEqual(filters, ["all", "active", "blocked", "planned", "done"]);
  assert.match(html, /\.item\[hidden\]\s*\{\s*display:\s*none\s*!important;?\s*\}/);

  const expectedCounts = Object.fromEntries([...allowed].map((state) => [state, 0]));
  statuses.forEach((state) => {
    expectedCounts[state] += 1;
  });
  expectedCounts.all = statuses.length;

  const filterButtons = filters.map((filter, index) =>
    makeElement({ filter, active: index === 0 }),
  );
  const items = statuses.map((status) => makeElement({ status }));
  const ids = [
    "page-updated",
    "refresh-status",
    "connection-dot",
    "connection-label",
    "empty-filter",
    "filter-summary",
    "milestone-completion",
    "milestone-state-summary",
    "check-now",
    "controls-status",
  ];
  const elements = Object.fromEntries(ids.map((id) => [id, makeElement()]));
  const scriptElement = {
    src: "https://example.test/progress.js?v=20261114-roadmap-1",
  };
  const document = {
    lastModified: "11/14/2026 3:00:00 PM",
    getElementById: (id) => elements[id] || null,
    querySelectorAll(selector) {
      if (selector === "#milestones .item") return items;
      if (selector === "#filters [data-filter]") return filterButtons;
      if (selector === '[data-when="now"]') return [];
      return [];
    },
    querySelector(selector) {
      return selector === 'script[src*="progress.js"]' ? scriptElement : null;
    },
  };

  let requests = 0;
  let reloads = 0;
  const location = {
    protocol: "https:",
    href: "https://example.test/PROGRESS.html",
    reload() {
      reloads += 1;
    },
  };
  const fetch = async (url) => {
    requests += 1;
    return {
      ok: true,
      text: async () => (String(url).includes("progress.js") ? script : html),
    };
  };

  vm.runInNewContext(script, {
    document,
    location,
    fetch,
    setInterval: () => 1,
    Date,
    URL,
    console,
  });

  for (const button of filterButtons) {
    button.listeners.click[0]();
    const visible = items.filter((item) => !item.hidden).length;
    assert.equal(visible, expectedCounts[button.dataset.filter], button.dataset.filter);
    assert.equal(button.attributes["aria-pressed"], "true");
    assert.equal(elements["empty-filter"].hidden, visible !== 0);
  }
  assert.equal(elements["milestone-completion"].textContent, expectedCounts.done + " / " + statuses.length);
  assert.match(elements["controls-status"].textContent, /ativos/);

  await waitFor(
    () => elements["refresh-status"].textContent.includes("Página e controles conferidos"),
    "initial page and script check",
  );
  const beforeManualCheck = requests;
  elements["check-now"].listeners.click[0]();
  assert.equal(elements["check-now"].disabled, true);
  await waitFor(
    () => requests >= beforeManualCheck + 2 &&
      elements["refresh-status"].textContent.includes("Página e controles conferidos"),
    "manual check of HTML and JavaScript",
  );
  assert.equal(reloads, 0, "unchanged page must not reload");
  console.log("Progress UI filters, counts, hidden cards, ARIA and manual refresh passed.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
