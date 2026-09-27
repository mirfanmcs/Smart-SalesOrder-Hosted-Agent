const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#send-button");
const resetButton = document.querySelector("#reset-button");
const suggestionButtons = document.querySelectorAll("[data-prompt]");

let previousResponseId = null;
let requestInProgress = false;

function scrollToLatestMessage() {
  messages.scrollTop = messages.scrollHeight;
}

function createMessage(role) {
  const article = document.createElement("article");
  article.className = `message ${role}-message`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role === "agent" ? "agent-avatar" : ""}`;
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = role === "user" ? "You" : "AI";

  const content = document.createElement("div");
  content.className = "message-content";

  const author = document.createElement("span");
  author.className = "message-author";
  author.textContent = role === "user" ? "You" : "Sales Order Assistant";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  content.append(author, bubble);
  article.append(avatar, content);
  messages.appendChild(article);
  scrollToLatestMessage();

  return { article, bubble };
}

function addMessage(role, text, isError = false) {
  const message = createMessage(role);
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  message.bubble.appendChild(paragraph);

  if (isError) {
    message.article.classList.add("message-error");
  }

  return message.article;
}

function addThinkingMessage() {
  const message = createMessage("agent");
  message.article.dataset.pending = "true";
  message.article.setAttribute("role", "status");

  const thinking = document.createElement("div");
  thinking.className = "thinking";

  const orb = document.createElement("span");
  orb.className = "thinking-orb";
  orb.setAttribute("aria-hidden", "true");

  const copy = document.createElement("span");
  copy.className = "thinking-copy";

  const title = document.createElement("strong");
  title.textContent = "Analyzing your request";

  const detail = document.createElement("small");
  detail.append("Preparing a response");

  const dots = document.createElement("span");
  dots.className = "thinking-dots";
  dots.setAttribute("aria-hidden", "true");
  for (let index = 0; index < 3; index += 1) {
    dots.appendChild(document.createElement("span"));
  }

  detail.append(dots);
  copy.append(title, detail);
  thinking.append(orb, copy);
  message.bubble.appendChild(thinking);

  return message.article;
}

function finishThinkingMessage(pending, text, isError) {
  const bubble = pending.querySelector(".bubble");
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.replaceChildren(paragraph);
  delete pending.dataset.pending;
  pending.removeAttribute("role");

  if (isError) {
    pending.classList.add("message-error");
  }
}

function setRequestState(isBusy) {
  requestInProgress = isBusy;
  messages.setAttribute("aria-busy", String(isBusy));
  sendButton.disabled = isBusy;
  resetButton.disabled = isBusy;
  input.disabled = isBusy;
  suggestionButtons.forEach((button) => {
    button.disabled = isBusy;
  });
}

function resizeInput() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
}

async function sendMessage(message) {
  addMessage("user", message);
  const pending = addThinkingMessage();
  setRequestState(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        previousResponseId,
      }),
    });
    const result = await response.json();

    if (response.ok) {
      previousResponseId = result.id;
      finishThinkingMessage(pending, result.message, false);
    } else {
      finishThinkingMessage(
        pending,
        result.error || "The request could not be completed.",
        true,
      );
    }
  } catch (error) {
    finishThinkingMessage(
      pending,
      "The client could not reach the hosted agent. Check the connection and try again.",
      true,
    );
  } finally {
    setRequestState(false);
    input.focus();
    scrollToLatestMessage();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || requestInProgress) {
    return;
  }

  input.value = "";
  resizeInput();
  await sendMessage(message);
});

input.addEventListener("keydown", (event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.isComposing
  ) {
    event.preventDefault();
    form.requestSubmit();
  }
});

input.addEventListener("input", resizeInput);

suggestionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    resizeInput();
    input.focus();
  });
});

resetButton.addEventListener("click", () => {
  previousResponseId = null;
  messages.replaceChildren();
  addMessage(
    "agent",
    "A new conversation is ready. What would you like to explore?",
  );
  input.focus();
});

resizeInput();
