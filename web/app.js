const chatStream = document.querySelector("#chat-stream");
const chatForm = document.querySelector("#chat-form");
const messageInput = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const requestState = document.querySelector("#request-state");
const activeSessionTitle = document.querySelector("#active-session-title");
const sessionList = document.querySelector("#session-list");
const newSessionButton = document.querySelector("#new-session");
const refreshSessionsButton = document.querySelector("#refresh-sessions");
const historyList = document.querySelector("#history-list");
const refreshHistoryButton = document.querySelector("#refresh-history");
const clearHistoryButton = document.querySelector("#clear-history");
const serviceStatus = document.querySelector("#service-status");
const documentForm = document.querySelector("#document-form");
const documentInput = document.querySelector("#document-input");
const uploadDocumentButton = document.querySelector("#upload-document");
const refreshDocumentsButton = document.querySelector("#refresh-documents");
const clearDocumentsButton = document.querySelector("#clear-documents");
const documentState = document.querySelector("#document-state");
const documentList = document.querySelector("#document-list");

let currentSessionId = null;
let sessions = [];

function appendMessage(role, content, meta = "") {
  const message = document.createElement("article");
  message.className = `message ${role}`;

  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "User" : role === "error" ? "Error" : "Assistant";

  const body = document.createElement("div");
  body.className = "message-content";
  if (role === "assistant") {
    body.innerHTML = renderAssistantAnswer(content);
  } else {
    body.textContent = content;
  }

  message.append(label, body);

  if (meta) {
    const footer = document.createElement("div");
    footer.className = "message-meta";
    footer.textContent = meta;
    message.appendChild(footer);
  }

  chatStream.appendChild(message);
  chatStream.scrollTop = chatStream.scrollHeight;
  return message;
}

function replaceAssistantMessage(message, content, meta = "") {
  if (!message) {
    return;
  }

  message.className = "message assistant";
  const body = message.querySelector(".message-content");
  if (body) {
    body.innerHTML = renderAssistantAnswer(content);
  }

  let footer = message.querySelector(".message-meta");
  if (meta) {
    if (!footer) {
      footer = document.createElement("div");
      footer.className = "message-meta";
      message.appendChild(footer);
    }
    footer.textContent = meta;
  } else if (footer) {
    footer.remove();
  }

  chatStream.scrollTop = chatStream.scrollHeight;
}

function renderAssistantAnswer(text) {
  const cleaned = cleanAssistantAnswer(text);
  const blocks = splitMarkdownBlocks(cleaned);
  return blocks.map(renderMarkdownBlock).join("");
}

function cleanAssistantAnswer(text) {
  return String(text ?? "")
    .replace(/\r\n/g, "\n")
    .replace(/^\s*(Assistant|AI|回答|答复|模型回答)\s*[:：]\s*/i, "")
    .replace(/^[\s"'`]*(以下是|下面是)?\s*(我的)?\s*(回答|答复)\s*[:：]\s*/i, "")
    .replace(/[✅🔍😊😉😄👍]/g, "")
    .replace(/[▪▫]\s*/g, "- ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function splitMarkdownBlocks(text) {
  const blocks = [];
  const pattern = /```([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      blocks.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    blocks.push({ type: "code", value: match[1].replace(/^\w+\n/, "").trim() });
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    blocks.push({ type: "text", value: text.slice(lastIndex) });
  }

  return blocks;
}

function renderMarkdownBlock(block) {
  if (block.type === "code") {
    return `<pre><code>${escapeHtml(block.value)}</code></pre>`;
  }

  return block.value
    .split(/\n{2,}/)
    .map((section) => renderTextSection(section.trim()))
    .join("");
}

function renderTextSection(section) {
  if (!section) {
    return "";
  }

  const lines = section.split("\n").filter(Boolean);
  const listType = detectListType(lines);
  if (listType) {
    const tag = listType === "ordered" ? "ol" : "ul";
    const items = lines
      .map((line) => line.replace(/^(\d+[.、]|[-*])\s*/, ""))
      .map((line) => `<li>${renderInlineMarkdown(line)}</li>`)
      .join("");
    return `<${tag}>${items}</${tag}>`;
  }

  const heading = section.match(/^(#{1,3})\s+(.+)$/);
  if (heading) {
    const level = Math.min(heading[1].length + 2, 4);
    return `<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`;
  }

  return `<p>${renderInlineMarkdown(lines.join("\n"))}</p>`;
}

function detectListType(lines) {
  if (lines.every((line) => /^\d+[.、]\s+/.test(line))) {
    return "ordered";
  }
  if (lines.every((line) => /^[-*]\s+/.test(line))) {
    return "unordered";
  }
  return "";
}

function renderInlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br>");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function summarizeText(text, maxLength = 64) {
  const cleaned = cleanAssistantAnswer(text).replace(/\s+/g, " ");
  if (cleaned.length <= maxLength) {
    return cleaned;
  }
  return `${cleaned.slice(0, maxLength - 1)}…`;
}

function setBusy(isBusy, text = "") {
  sendButton.disabled = isBusy;
  messageInput.disabled = isBusy;
  requestState.textContent = "";
  requestState.classList.toggle("is-busy", false);
}

async function requestJson(url, options = {}) {
  const headers = options.body instanceof FormData ? {} : { "Content-Type": "application/json" };
  const response = await fetch(url, { headers, ...options });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function loadHealth() {
  try {
    const health = await requestJson("/health");
    serviceStatus.textContent = health.database === "available" ? "服务在线" : "数据库未连接";
  } catch {
    serviceStatus.textContent = "服务不可用";
  }
}

async function ensureActiveSession() {
  sessions = await requestJson("/sessions");
  if (!sessions.length) {
    const session = await requestJson("/sessions", {
      method: "POST",
      body: JSON.stringify({ title: "新会话" }),
    });
    sessions = [session];
  }

  if (!currentSessionId || !sessions.some((session) => session.session_id === currentSessionId)) {
    currentSessionId = sessions[0].session_id;
  }

  renderSessions();
  updateActiveSessionTitle();
}

async function loadSessions() {
  try {
    await ensureActiveSession();
  } catch (error) {
    sessionList.innerHTML = "";
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "会话读取失败";
    sessionList.appendChild(empty);
    appendMessage("error", error.message);
  }
}

function renderSessions() {
  sessionList.innerHTML = "";

  sessions.forEach((session) => {
    const item = document.createElement("button");
    item.className = `session-item${session.session_id === currentSessionId ? " active" : ""}`;
    item.type = "button";

    const title = document.createElement("strong");
    title.textContent = session.title;

    const meta = document.createElement("span");
    meta.textContent = `${session.turn_count} turns`;

    if (session.last_message) {
      const preview = document.createElement("span");
      preview.className = "session-preview";
      preview.textContent = summarizeText(session.last_message, 36);
      item.append(title, preview, meta);
    } else {
      item.append(title, meta);
    }

    item.addEventListener("click", () => switchSession(session.session_id));
    sessionList.appendChild(item);
  });
}

function updateActiveSessionTitle() {
  const session = sessions.find((item) => item.session_id === currentSessionId);
  activeSessionTitle.textContent = session ? session.title : "多会话长期记忆 RAG 问答系统";
}

async function switchSession(sessionId) {
  if (currentSessionId === sessionId) {
    return;
  }

  currentSessionId = sessionId;
  renderSessions();
  updateActiveSessionTitle();
  await loadHistory();
  await loadConversation();
  messageInput.focus();
}

async function createSession() {
  newSessionButton.disabled = true;
  try {
    const session = await requestJson("/sessions", {
      method: "POST",
      body: JSON.stringify({ title: "新会话" }),
    });
    currentSessionId = session.session_id;
    await loadSessions();
    await loadHistory();
    chatStream.innerHTML = "";
    messageInput.focus();
  } catch (error) {
    appendMessage("error", error.message);
  } finally {
    newSessionButton.disabled = false;
  }
}

async function loadHistory() {
  if (!currentSessionId) {
    return;
  }

  try {
    const turns = await requestJson(`/history/recent?session_id=${currentSessionId}&limit=5`);
    historyList.innerHTML = "";

    if (!turns.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "暂无历史";
      historyList.appendChild(empty);
      return;
    }

    turns
      .slice()
      .reverse()
      .forEach((turn) => {
        const item = document.createElement("article");
        item.className = "history-item";

        const title = document.createElement("strong");
        title.textContent = `Turn ${turn.turn_index}`;

        const content = document.createElement("p");
        content.textContent = turn.user;

        const answer = document.createElement("p");
        answer.className = "history-answer";
        answer.textContent = summarizeText(turn.assistant);

        item.append(title, content, answer);
        historyList.appendChild(item);
      });
  } catch (error) {
    historyList.innerHTML = "";
    const item = document.createElement("p");
    item.className = "empty";
    item.textContent = "历史读取失败";
    historyList.appendChild(item);
  }
}

async function loadConversation() {
  if (!currentSessionId) {
    return;
  }

  try {
    const turns = await requestJson(`/history?session_id=${currentSessionId}`);
    chatStream.innerHTML = "";
    turns.forEach((turn) => {
      appendMessage("user", turn.user);
      appendMessage("assistant", turn.assistant, `Turn：${turn.turn_index}`);
    });
  } catch (error) {
    chatStream.innerHTML = "";
    appendMessage("error", error.message);
  }
}

async function loadDocuments() {
  try {
    const documents = await requestJson("/documents");
    documentList.innerHTML = "";

    if (!documents.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "暂无文档";
      documentList.appendChild(empty);
      return;
    }

    documents
      .slice()
      .reverse()
      .forEach((documentItem) => {
        const item = document.createElement("article");
        item.className = "document-item";

        const title = document.createElement("strong");
        title.textContent = documentItem.filename;

        const meta = document.createElement("p");
        meta.textContent = `Document ${documentItem.document_id} · ${documentItem.chunk_count} chunks`;

        const remove = document.createElement("button");
        remove.className = "text-button";
        remove.type = "button";
        remove.textContent = "删除";
        remove.addEventListener("click", () => deleteDocument(documentItem.document_id));

        item.append(title, meta, remove);
        documentList.appendChild(item);
      });
  } catch {
    documentList.innerHTML = "";
    const item = document.createElement("p");
    item.className = "empty";
    item.textContent = "文档读取失败";
    documentList.appendChild(item);
  }
}

async function deleteDocument(documentId) {
  documentState.textContent = "删除中";
  try {
    await requestJson(`/documents/${documentId}`, { method: "DELETE" });
    await loadDocuments();
    documentState.textContent = "";
  } catch (error) {
    documentState.textContent = "删除失败";
    appendMessage("error", error.message);
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();
  if (!message) {
    messageInput.focus();
    return;
  }
  if (!currentSessionId) {
    await ensureActiveSession();
  }

  appendMessage("user", message);
  const pendingMessage = appendMessage("assistant pending", "AI生成中");
  messageInput.value = "";
  setBusy(true, "AI生成中");

  try {
    const result = await requestJson("/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: currentSessionId, message }),
    });
    const retrieved = result.retrieved_turn_indexes.length
      ? `参考 Turn：${result.retrieved_turn_indexes.join(", ")}`
      : "未召回额外历史";
    const documentChunks = result.retrieved_document_chunk_ids.length
      ? `参考 Chunk：${result.retrieved_document_chunk_ids.join(", ")}`
      : "未召回文档";
    replaceAssistantMessage(
      pendingMessage,
      result.answer,
      `当前 Turn：${result.turn_index}；${retrieved}；${documentChunks}`,
    );
    await loadSessions();
    await loadHistory();
  } catch (error) {
    pendingMessage.remove();
    appendMessage("error", error.message);
  } finally {
    setBusy(false);
    messageInput.focus();
  }
});

newSessionButton.addEventListener("click", createSession);

refreshSessionsButton.addEventListener("click", loadSessions);

refreshHistoryButton.addEventListener("click", loadHistory);

refreshDocumentsButton.addEventListener("click", loadDocuments);

documentForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = documentInput.files[0];
  if (!file) {
    documentInput.focus();
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  uploadDocumentButton.disabled = true;
  documentInput.disabled = true;
  documentState.textContent = "上传并切片中";

  try {
    const result = await requestJson("/documents", {
      method: "POST",
      body: formData,
    });
    documentInput.value = "";
    documentState.textContent = `已入库 ${result.chunk_count} 个切片`;
    await loadDocuments();
  } catch (error) {
    documentState.textContent = "上传失败";
    appendMessage("error", error.message);
  } finally {
    uploadDocumentButton.disabled = false;
    documentInput.disabled = false;
  }
});

clearHistoryButton.addEventListener("click", async () => {
  if (!currentSessionId) {
    return;
  }

  clearHistoryButton.disabled = true;
  try {
    await requestJson(`/history?session_id=${currentSessionId}`, { method: "DELETE" });
    chatStream.innerHTML = "";
    await loadSessions();
    await loadHistory();
  } catch (error) {
    appendMessage("error", error.message);
  } finally {
    clearHistoryButton.disabled = false;
  }
});

clearDocumentsButton.addEventListener("click", async () => {
  clearDocumentsButton.disabled = true;
  documentState.textContent = "清空中";
  try {
    await requestJson("/documents", { method: "DELETE" });
    await loadDocuments();
    documentState.textContent = "";
  } catch (error) {
    documentState.textContent = "清空失败";
    appendMessage("error", error.message);
  } finally {
    clearDocumentsButton.disabled = false;
  }
});

async function init() {
  await loadHealth();
  await loadSessions();
  await loadHistory();
  await loadConversation();
  await loadDocuments();
}

init();
