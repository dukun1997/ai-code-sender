import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const LOCK_DIR_ENV = "OPENCODE_IDE_LOCK_DIR";
const TOKEN_HEADER = "X-OpenCode-Ide-Authorization";
const DEFAULT_LOCK_DIR = path.join(os.homedir(), ".opencode", "ide");
const REQUEST_TIMEOUT_MS = 1500;
const LOCK_STALE_MS = 45_000;
const CONTEXT_FORMAT = (process.env.OPENCODE_IDE_CONTEXT_FORMAT || "compact")
  .trim()
  .toLowerCase();

function lockDir() {
  const configured = (process.env[LOCK_DIR_ENV] || "").trim();
  return configured ? path.resolve(configured) : DEFAULT_LOCK_DIR;
}

function isWithin(basePath, targetPath) {
  const relative = path.relative(basePath, targetPath);
  return (
    relative === "" ||
    (!relative.startsWith("..") && !path.isAbsolute(relative))
  );
}

function toIntOrNull(value) {
  return Number.isInteger(value) ? value : null;
}

function displayPath(snapshot, cwd) {
  const filePath = String(snapshot.filePath || "").trim();
  if (!filePath) return "";

  const workspace = typeof snapshot.workspace === "string" ? snapshot.workspace.trim() : "";
  const base = workspace || cwd;
  if (!base) return filePath;

  try {
    const rel = path.relative(path.resolve(base), path.resolve(filePath));
    if (rel && !rel.startsWith("..") && !path.isAbsolute(rel)) {
      return rel.replaceAll(path.sep, "/");
    }
  } catch {
    // fall through
  }
  return filePath;
}

function rangeText(snapshot) {
  const lineStart = toIntOrNull(snapshot.lineStart);
  const lineEnd = toIntOrNull(snapshot.lineEnd);
  if (lineStart === null || lineEnd === null) return "";
  return lineStart === lineEnd ? `L${lineStart}` : `L${lineStart}-${lineEnd}`;
}

function parseLock(filePath, raw) {
  const workspaceFolders = Array.isArray(raw.workspaceFolders)
    ? raw.workspaceFolders.filter((it) => typeof it === "string")
    : [];
  const url = typeof raw.url === "string" ? raw.url.trim().replace(/\/+$/, "") : "";
  const authToken = typeof raw.authToken === "string" ? raw.authToken.trim() : "";
  const updatedAtMs = Date.parse(String(raw.updatedAt || ""));
  if (!url || !authToken) return null;
  return {
    path: filePath,
    workspaceFolders,
    url,
    authToken,
    updatedAtMs: Number.isFinite(updatedAtMs) ? updatedAtMs : 0,
    stale: Number.isFinite(updatedAtMs) ? Date.now() - updatedAtMs > LOCK_STALE_MS : false,
  };
}

async function discoverLocks() {
  const dir = lockDir();
  let entries = [];
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch {
    return [];
  }

  const locks = [];
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith(".lock")) continue;
    const filePath = path.join(dir, entry.name);
    try {
      const raw = JSON.parse(await fs.readFile(filePath, "utf-8"));
      const parsed = parseLock(filePath, raw);
      if (parsed) locks.push(parsed);
    } catch {
      // ignore invalid lock file
    }
  }
  return locks;
}

function chooseLock(cwd, locks) {
  let best = null;
  for (const lock of locks) {
    for (const folder of lock.workspaceFolders) {
      const resolved = path.resolve(folder);
      if (!isWithin(resolved, cwd)) continue;
      const score = {
        freshness: lock.stale ? 0 : 1,
        workspaceDepth: resolved.length,
        updatedAtMs: lock.updatedAtMs,
      };
      if (
        !best ||
        score.freshness > best.score.freshness ||
        (score.freshness === best.score.freshness && score.workspaceDepth > best.score.workspaceDepth) ||
        (score.freshness === best.score.freshness &&
          score.workspaceDepth === best.score.workspaceDepth &&
          score.updatedAtMs > best.score.updatedAtMs)
      ) {
        best = { score, lock };
      }
    }
  }
  return best ? best.lock : null;
}

async function fetchContext(lock) {
  let signal;
  if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
    signal = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  } else {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS).unref?.();
    signal = controller.signal;
  }
  const response = await fetch(`${lock.url}/context/current`, {
    method: "GET",
    headers: {
      [TOKEN_HEADER]: lock.authToken,
    },
    signal,
  });
  if (!response.ok) {
    throw new Error(`context endpoint returned HTTP ${response.status}`);
  }
  return response.json();
}

function renderContextFull(snapshot) {
  if (!snapshot || typeof snapshot !== "object") return "";

  const contextType = String(snapshot.contextType || "unknown");
  const filePath = String(snapshot.filePath || "");
  const className = String(snapshot.className || "");
  const revision = Number.isInteger(snapshot.revision) ? snapshot.revision : 0;
  const truncated = snapshot.truncated === true ? "true" : "false";
  const lineStart = toIntOrNull(snapshot.lineStart);
  const lineEnd = toIntOrNull(snapshot.lineEnd);
  const rangeText =
    lineStart !== null && lineEnd !== null ? `L${lineStart}-L${lineEnd}` : "";
  const classLine = className ? `class: ${className}\n` : "";
  const text = String(snapshot.text || "").trimEnd();
  if (!text) return "";

  return (
    "[IDE Context]\n" +
    `type: ${contextType}\n` +
    `file: ${filePath}\n` +
    `range: ${rangeText}\n` +
    `revision: ${revision}\n` +
    `truncated: ${truncated}\n` +
    classLine +
    "content:\n" +
    `${text}\n` +
    "[/IDE Context]"
  );
}

function renderContextCompact(snapshot, cwd) {
  if (!snapshot || typeof snapshot !== "object") return "";

  const relPath = displayPath(snapshot, cwd);
  if (!relPath) return "";

  const range = rangeText(snapshot);
  const className = String(snapshot.className || "").trim();
  const head = range ? `@${relPath}#${range}` : `@${relPath}`;

  if (className) return `${head}\nclass: ${className}`;
  return head;
}

function renderContextBlock(snapshot, cwd) {
  if (CONTEXT_FORMAT === "full") {
    return renderContextFull(snapshot);
  }
  return renderContextCompact(snapshot, cwd);
}

function prependContext(contextBlock, originalPrompt) {
  const prompt = String(originalPrompt || "").trimEnd();
  if (!prompt) return contextBlock;
  return `${contextBlock}\n\n${prompt}`;
}

export default async function IdeContextPlugin(ctx) {
  const cwd = path.resolve(ctx.directory || process.cwd());
  const lastInjectedRevisionBySession = new Map();

  return {
    async "chat.message"(input, output) {
      const textPart = output.parts.find(
        (part) => part && part.type === "text" && typeof part.text === "string",
      );
      if (!textPart) return;
      if (textPart.text.includes("[IDE Context]")) return;

      try {
        const locks = await discoverLocks();
        const matchedLock = chooseLock(cwd, locks);
        if (!matchedLock) {
          if (process.env.OPENCODE_IDE_DEBUG === "1") {
            console.error("[ide-context-plugin] no lock matched cwd:", cwd);
          }
          return;
        }

        const snapshot = await fetchContext(matchedLock);
        const contextType = String(snapshot?.contextType || "");
        if (contextType !== "selection") {
          if (process.env.OPENCODE_IDE_DEBUG === "1") {
            console.error(
              `[ide-context-plugin] skip non-selection context: type=${contextType || "unknown"}`,
            );
          }
          return;
        }

        const revision = Number.isInteger(snapshot?.revision) ? snapshot.revision : null;
        const sessionID = typeof input?.sessionID === "string" && input.sessionID
          ? input.sessionID
          : "__default__";
        if (revision !== null) {
          const lastRevision = lastInjectedRevisionBySession.get(sessionID);
          if (lastRevision === revision) {
            if (process.env.OPENCODE_IDE_DEBUG === "1") {
              console.error(
                `[ide-context-plugin] skip unchanged context: session=${sessionID} revision=${revision}`,
              );
            }
            return;
          }
        }

        const contextBlock = renderContextBlock(snapshot, cwd);
        if (!contextBlock) return;

        textPart.text = prependContext(contextBlock, textPart.text);
        if (revision !== null) {
          lastInjectedRevisionBySession.set(sessionID, revision);
        }
      } catch (error) {
        if (process.env.OPENCODE_IDE_DEBUG === "1") {
          console.error("[ide-context-plugin] inject failed:", error);
        }
      }
    },
  };
}
