import assert from "node:assert/strict";
import test from "node:test";
import {
  createPublicGitHubProgressController,
  normalizePublicGitHubProgress,
  PUBLIC_PROGRESS_REFRESH_MS,
} from "../../progressStatus.js";

const updatedAt = "2026-11-23T15:20:00.000Z";
const checkedAt = "2026-11-23T15:30:00.000Z";
const sha = "a".repeat(40);

function issuePayload(title = "Plano Nivus") {
  return { number: 125, title, state: "open", updated_at: updatedAt, body: "public issue body is ignored" };
}

function commitPayload(subject = "docs: update Nivus plan") {
  return {
    sha,
    html_url: "https://example.invalid/untrusted",
    commit: {
      message: subject,
      committer: { date: updatedAt },
    },
  };
}

function snapshot() {
  return normalizePublicGitHubProgress(issuePayload(), commitPayload(), checkedAt);
}

class FakeNode {
  constructor(tagName = "div") {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.attributes = new Map();
    this.className = "";
    this._text = "";
    this.hidden = false;
  }

  get textContent() {
    return this._text + this.children.map((child) => child.textContent).join("");
  }

  set textContent(value) {
    this._text = String(value);
    this.children = [];
  }

  get firstChild() {
    return this.children[0] || null;
  }

  get innerHTML() {
    return "";
  }

  set innerHTML(_value) {
    throw new Error("Unsafe HTML rendering is forbidden in these tests");
  }

  append(...nodes) {
    this.children.push(...nodes);
  }

  prepend(node) {
    this.children.unshift(node);
  }

  replaceChildren(...nodes) {
    this._text = "";
    this.children = [...nodes];
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  querySelector(selector) {
    if (selector === "div") return this.children.find((child) => child.tagName === "DIV") || null;
    const match = selector.match(/^\[(data-nivus-public-(?:commit|status))\]$/);
    if (!match) return null;
    return this.children.find((child) => child.getAttribute(match[1]) !== null) || null;
  }
}

function createDocument() {
  const heroTitle = new FakeNode("h2");
  heroTitle.textContent = "Static milestone";
  const heroCopy = new FakeNode("p");
  heroCopy.textContent = "Static snapshot remains visible until public data arrives.";
  const feed = new FakeNode("div");
  const createdTags = [];
  const document = {
    getElementById(id) {
      return id === "hero-title" ? heroTitle : id === "hero-copy" ? heroCopy : null;
    },
    querySelector(selector) {
      return selector === ".feed" ? feed : null;
    },
    createElement(tag) {
      createdTags.push(tag.toLowerCase());
      return new FakeNode(tag);
    },
    createTextNode(text) {
      const node = new FakeNode("#text");
      node.textContent = text;
      return node;
    },
  };
  return { document, heroTitle, heroCopy, feed, createdTags };
}

function makeStorage(initial = null) {
  const values = new Map();
  if (initial) values.set("nivus-public-progress-v1", JSON.stringify(initial));
  return {
    getItem(key) { return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, value); },
  };
}

function response(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => null },
    async json() { return payload; },
  };
}

function publicFetch({ issue = issuePayload(), commit = commitPayload(), status = 200 } = {}) {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    if (status !== 200) return response({}, status);
    return response(url.endsWith("/issues/125") ? issue : [commit]);
  };
  return { fetchImpl, calls };
}

test("renders current public issue and main commit without credentials or HTML parsing", async () => {
  const ui = createDocument();
  const { fetchImpl, calls } = publicFetch({
    issue: issuePayload("<img src=x onerror=alert(1)>"),
    commit: commitPayload("<svg onload=alert(1)>"),
  });
  const storage = makeStorage();
  const controller = createPublicGitHubProgressController({
    document: ui.document,
    fetchImpl,
    storage,
    now: () => new Date(checkedAt),
  });

  const result = await controller.refresh();

  assert.equal(result.status, "fresh");
  assert.equal(calls.length, 2);
  assert.ok(calls.every(({ options }) => options.cache === "no-cache"));
  assert.ok(calls.every(({ options }) => options.headers.Accept === "application/vnd.github+json"));
  assert.ok(calls.every(({ options }) => !("Authorization" in options.headers)));
  assert.match(ui.heroTitle.textContent, /<img src=x onerror=alert\(1\)>/);
  assert.match(ui.heroCopy.textContent, /abrir Issue #125/);
  assert.match(ui.feed.textContent, /<svg onload=alert\(1\)>/);
  assert.deepEqual(ui.createdTags.filter((tag) => ["img", "svg", "script"].includes(tag)), []);
  assert.match(ui.feed.textContent, /GitHub atualizado/);
  assert.equal(storage.getItem("nivus-public-progress-v1") !== null, true);

  const links = ui.feed.children.flatMap((event) => event._nivusDetails?.children || [])
    .filter((node) => node.tagName === "A");
  assert.ok(links.every((link) => link.href.startsWith("https://github.com/astec10/nivus-edge-node/")));
});

for (const status of [403, 429]) {
  test(`keeps the cached snapshot and marks it stale on HTTP ${status}`, async () => {
    const ui = createDocument();
    const { fetchImpl } = publicFetch({ status });
    const controller = createPublicGitHubProgressController({
      document: ui.document,
      fetchImpl,
      storage: makeStorage(snapshot()),
      now: () => new Date(checkedAt),
    });

    const result = await controller.refresh();

    assert.equal(result.status, "stale");
    assert.equal(result.reason, "limite da API");
    assert.match(ui.heroTitle.textContent, /Plano Nivus/);
    assert.match(ui.feed.textContent, /GitHub desatualizado/);
    assert.match(ui.feed.textContent, /limite da API/);
  });
}

test("preserves the static page when offline and no saved GitHub snapshot exists", async () => {
  const ui = createDocument();
  const controller = createPublicGitHubProgressController({
    document: ui.document,
    fetchImpl: async () => { throw new TypeError("network unavailable"); },
    storage: makeStorage(),
  });

  const result = await controller.refresh();

  assert.equal(result.status, "offline");
  assert.equal(ui.heroTitle.textContent, "Static milestone");
  assert.match(ui.heroCopy.textContent, /Static snapshot/);
  assert.match(ui.feed.textContent, /GitHub offline/);
  assert.match(ui.feed.textContent, /sem conexão/);
});

test("prevents overlapping refreshes and schedules only the bounded interval", async () => {
  const ui = createDocument();
  const { fetchImpl } = publicFetch();
  let scheduledDelay = null;
  let scheduleCount = 0;
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  let firstRequest = true;
  const delayedFetch = async (url, options) => {
    if (firstRequest) {
      firstRequest = false;
      await pending;
    }
    return fetchImpl(url, options);
  };
  const controller = createPublicGitHubProgressController({
    document: ui.document,
    fetchImpl: delayedFetch,
    storage: makeStorage(),
    setIntervalImpl: (_callback, delay) => { scheduleCount += 1; scheduledDelay = delay; return 1; },
    clearIntervalImpl: () => {},
  });

  const first = controller.refresh();
  const second = await controller.refresh();
  assert.equal(second.status, "skipped");
  controller.start();
  controller.start();
  assert.equal(scheduleCount, 1);
  assert.equal(scheduledDelay, PUBLIC_PROGRESS_REFRESH_MS);

  release();
  const firstResult = await first;
  assert.equal(firstResult.status, "fresh");
  controller.stop();
});
