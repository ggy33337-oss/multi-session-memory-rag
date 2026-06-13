const chatStream = document.querySelector("#chat-stream");
const chatForm = document.querySelector("#chat-form");
const messageInput = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const requestState = document.querySelector("#request-state");
const historyList = document.querySelector("#history-list");
const refreshHistoryButton = document.querySelector("#refresh-history");
const clearHistoryButton = document.querySelector("#clear-history");
const serviceStatus = document.querySelector("#service-status");

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
  requestState.textContent = text;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

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
    await requestJson("/health");
    serviceStatus.textContent = "服务在线";
  } catch {
    serviceStatus.textContent = "服务不可用";
  }
}

async function loadHistory() {
  try {
    const turns = await requestJson("/history/recent?limit=5");
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
        title.textContent = `Turn ${turn.turn_id}`;

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

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();
  if (!message) {
    messageInput.focus();
    return;
  }

  appendMessage("user", message);
  messageInput.value = "";
  setBusy(true, "生成中");

  try {
    const result = await requestJson("/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    const retrieved = result.retrieved_turn_ids.length
      ? `参考 Turn：${result.retrieved_turn_ids.join(", ")}`
      : "未召回额外历史";
    appendMessage("assistant", result.answer, `当前 Turn：${result.turn_id}；${retrieved}`);
    await loadHistory();
  } catch (error) {
    appendMessage("error", error.message);
  } finally {
    setBusy(false);
    messageInput.focus();
  }
});

refreshHistoryButton.addEventListener("click", loadHistory);

clearHistoryButton.addEventListener("click", async () => {
  clearHistoryButton.disabled = true;
  try {
    await requestJson("/history", { method: "DELETE" });
    chatStream.innerHTML = "";
    await loadHistory();
  } catch (error) {
    appendMessage("error", error.message);
  } finally {
    clearHistoryButton.disabled = false;
  }
});

loadHealth();
loadHistory();
