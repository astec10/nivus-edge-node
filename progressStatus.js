const REPOSITORY = "astec10/nivus-edge-node";
const PLAN_ISSUE_NUMBER = 125;
const API_ROOT = `https://api.github.com/repos/${REPOSITORY}`;
const CACHE_KEY = "nivus-public-progress-v1";

export const PUBLIC_PROGRESS_REFRESH_MS = 10 * 60 * 1000;

function cleanText(value, maxLength) {
  if (typeof value !== "string") return "";
  return value.replace(/[\u0000-\u001f\u007f-\u009f]/g, " ").trim().slice(0, maxLength);
}

function isoDate(value) {
  if (typeof value !== "string") return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function normalizeCachedSnapshot(value) {
  if (!value || typeof value !== "object") return null;
  const issueTitle = cleanText(value.issue?.title, 300);
  const issueUpdatedAt = isoDate(value.issue?.updatedAt);
  const commitSubject = cleanText(value.commit?.subject, 240);
  const commitAt = isoDate(value.commit?.committedAt);
  const checkedAt = isoDate(value.checkedAt);
  const sha = typeof value.commit?.sha === "string" ? value.commit.sha : "";
  if (
    value.issue?.number !== PLAN_ISSUE_NUMBER ||
    !["open", "closed"].includes(value.issue?.state) ||
    !issueTitle ||
    !issueUpdatedAt ||
    !/^[a-f0-9]{40}$/i.test(sha) ||
    !commitSubject ||
    !commitAt ||
    !checkedAt
  ) return null;

  return {
    issue: {
      number: PLAN_ISSUE_NUMBER,
      title: issueTitle,
      state: value.issue.state,
      updatedAt: issueUpdatedAt,
      url: `https://github.com/${REPOSITORY}/issues/${PLAN_ISSUE_NUMBER}`,
    },
    commit: {
      sha: sha.toLowerCase(),
      subject: commitSubject,
      committedAt: commitAt,
      url: `https://github.com/${REPOSITORY}/commit/${sha.toLowerCase()}`,
    },
    checkedAt,
  };
}

export function normalizePublicGitHubProgress(issuePayload, commitPayload, checkedAt = new Date().toISOString()) {
  if (!issuePayload || issuePayload.number !== PLAN_ISSUE_NUMBER) {
    throw new TypeError("Unexpected public plan issue");
  }
  const title = cleanText(issuePayload.title, 300);
  const issueUpdatedAt = isoDate(issuePayload.updated_at);
  if (!title || !issueUpdatedAt || !["open", "closed"].includes(issuePayload.state)) {
    throw new TypeError("Invalid public plan metadata");
  }

  const sha = typeof commitPayload?.sha === "string" ? commitPayload.sha.toLowerCase() : "";
  const commit = commitPayload?.commit;
  const subject = cleanText(typeof commit?.message === "string" ? commit.message.split(/\r?\n/, 1)[0] : "", 240);
  const committedAt = isoDate(commit?.committer?.date || commit?.author?.date);
  if (!/^[a-f0-9]{40}$/.test(sha) || !subject || !committedAt) {
    throw new TypeError("Invalid public commit metadata");
  }

  return normalizeCachedSnapshot({
    issue: { number: PLAN_ISSUE_NUMBER, title, state: issuePayload.state, updatedAt: issueUpdatedAt },
    commit: { sha, subject, committedAt },
    checkedAt,
  });
}

function safeRead(storage) {
  try {
    const raw = storage?.getItem(CACHE_KEY);
    return raw ? normalizeCachedSnapshot(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

function safeWrite(storage, snapshot) {
  try {
    storage?.setItem(CACHE_KEY, JSON.stringify(snapshot));
  } catch {
    // Storage can be unavailable in private browsing or under a quota policy.
  }
}

function formatDate(value) {
  return new Date(value).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function ensureEvent(document, feed, attribute, value) {
  let event = feed.querySelector(`[${attribute}]`);
  if (!event) {
    event = document.createElement("div");
    event.className = "event";
    event.setAttribute(attribute, value);
    event.setAttribute("role", "status");
    event.setAttribute("aria-live", "polite");
    const marker = document.createElement("i");
    marker.setAttribute("aria-hidden", "true");
    const details = document.createElement("div");
    event.append(marker, details);
    event._nivusDetails = details;
    feed.prepend(event);
  }
  return event._nivusDetails || event.querySelector("div");
}

function renderLink(document, href, label) {
  const link = document.createElement("a");
  link.href = href;
  link.target = "_blank";
  link.rel = "noreferrer noopener";
  link.textContent = label;
  return link;
}

export function renderPublicGitHubProgress(document, snapshot, { stale = false, reason = "" } = {}) {
  const feed = document.querySelector(".feed");
  const heroTitle = document.getElementById("hero-title");
  const heroCopy = document.getElementById("hero-copy");
  if (!feed) return;

  if (snapshot) {
    const safe = normalizeCachedSnapshot(snapshot);
    if (!safe) return;
    if (heroTitle) heroTitle.textContent = `#${safe.issue.number} · ${safe.issue.title}`;
    if (heroCopy) {
      heroCopy.replaceChildren(
        document.createTextNode(`Estado: ${safe.issue.state === "open" ? "em andamento" : "encerrada"} · atualizada em ${formatDate(safe.issue.updatedAt)} · `),
        renderLink(document, safe.issue.url, "abrir Issue #125"),
      );
    }

    const commitDetails = ensureEvent(document, feed, "data-nivus-public-commit", "true");
    const commitLink = renderLink(document, safe.commit.url, safe.commit.sha.slice(0, 7));
    const commitTime = document.createElement("time");
    commitTime.dateTime = safe.commit.committedAt;
    commitTime.textContent = formatDate(safe.commit.committedAt);
    commitDetails.replaceChildren(
      document.createElement("strong"),
      document.createTextNode(" "),
      commitLink,
      document.createTextNode(` · ${safe.commit.subject}`),
      commitTime,
    );
    commitDetails.firstChild.textContent = "Último commit público";
  }

  const statusDetails = ensureEvent(document, feed, "data-nivus-public-status", "true");
  const checkedAt = snapshot ? normalizeCachedSnapshot(snapshot)?.checkedAt : null;
  const message = snapshot
    ? stale
      ? `GitHub desatualizado · último retrato de ${formatDate(checkedAt)} · ${reason || "fonte pública indisponível"}.`
      : `GitHub atualizado · conferido em ${formatDate(checkedAt)}.`
    : `GitHub offline · mostrando o retrato estático. ${reason || "A fonte pública ainda não respondeu"}.`;
  statusDetails.replaceChildren(document.createTextNode(message));
}

function failureReason(error) {
  if (error?.kind === "rate-limit") return "limite da API";
  if (error?.kind === "network") return "sem conexão";
  if (error?.kind === "invalid-data") return "resposta inválida";
  return "fonte pública indisponível";
}

export function createPublicGitHubProgressController({
  document,
  fetchImpl = globalThis.fetch,
  storage = null,
  now = () => new Date(),
  setIntervalImpl = globalThis.setInterval,
  clearIntervalImpl = globalThis.clearInterval,
} = {}) {
  let inFlight = false;
  let intervalId = null;

  async function requestJson(url) {
    let response;
    try {
      response = await fetchImpl(url, {
        cache: "no-cache",
        headers: { Accept: "application/vnd.github+json" },
      });
    } catch {
      const error = new Error("Public GitHub connection failed");
      error.kind = "network";
      throw error;
    }
    const remaining = response.headers?.get?.("X-RateLimit-Remaining");
    if (!response.ok) {
      const error = new Error("Public GitHub request failed");
      error.kind = response.status === 403 || response.status === 429 || remaining === "0"
        ? "rate-limit"
        : "network";
      throw error;
    }
    try {
      return await response.json();
    } catch {
      const error = new Error("Public GitHub response was invalid");
      error.kind = "invalid-data";
      throw error;
    }
  }

  async function refresh() {
    if (inFlight) return { status: "skipped" };
    inFlight = true;
    try {
      const [issueResult, commitsResult] = await Promise.allSettled([
        requestJson(`${API_ROOT}/issues/${PLAN_ISSUE_NUMBER}`),
        requestJson(`${API_ROOT}/commits?sha=main&per_page=1`),
      ]);
      if (issueResult.status === "rejected") throw issueResult.reason;
      if (commitsResult.status === "rejected") throw commitsResult.reason;
      const issue = issueResult.value;
      const commits = commitsResult.value;
      if (!Array.isArray(commits) || !commits[0]) {
        const error = new Error("No public commit found");
        error.kind = "invalid-data";
        throw error;
      }
      const checkedAt = new Date(now()).toISOString();
      const snapshot = normalizePublicGitHubProgress(issue, commits[0], checkedAt);
      safeWrite(storage, snapshot);
      renderPublicGitHubProgress(document, snapshot);
      return { status: "fresh", snapshot };
    } catch (error) {
      const cached = safeRead(storage);
      renderPublicGitHubProgress(document, cached, { stale: Boolean(cached), reason: failureReason(error) });
      return { status: cached ? "stale" : "offline", reason: failureReason(error) };
    } finally {
      inFlight = false;
    }
  }

  return {
    refresh,
    start() {
      void refresh();
      if (intervalId === null) intervalId = setIntervalImpl(refresh, PUBLIC_PROGRESS_REFRESH_MS);
    },
    stop() {
      if (intervalId !== null) clearIntervalImpl(intervalId);
      intervalId = null;
    },
  };
}

export function startPublicProgressStatus(document, options = {}) {
  let storage = null;
  try {
    storage = globalThis.localStorage;
  } catch {
    // The static snapshot remains available when browser storage is disabled.
  }
  const controller = createPublicGitHubProgressController({
    document,
    fetchImpl: globalThis.fetch?.bind(globalThis),
    storage,
    ...options,
  });
  controller.start();
  return controller;
}
