document.addEventListener("DOMContentLoaded", () => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = { view: "home", conversationId: null, currentNote: null, projects: [], notes: [], windows: [], voiceReply: false, coreState: "idle" };

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[char]));

  const toast = (message, icon = "check-circle") => {
    const item = document.createElement("div");
    item.className = "toast";
    item.innerHTML = `<i class="ph ph-${icon}"></i><span>${escapeHtml(message)}</span>`;
    $("#toast-region").appendChild(item);
    setTimeout(() => item.remove(), 3200);
  };

  const setView = (view) => {
    const names = { home: "Começo", chat: "Conversas", vault: "Meu vault", projects: "Projetos", desktop: "Desktop", settings: "Personalização" };
    state.view = view;
    document.body.classList.toggle("chat-immersive", view === "chat");
    document.body.classList.toggle("module-mode", view !== "home");
    $$(".view").forEach((item) => item.classList.toggle("active", item.id === `view-${view}`));
    $$(".rail-button[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
    $$(".context-nav button").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
    const activeView = $(`#view-${view}`);
    if (activeView) {
      activeView.querySelectorAll(".panel,.project-card,.continue-item,.module-header,.home-hero,.command-card").forEach((item, index) => {
        item.classList.remove("fx-enter-up");
        void item.offsetWidth;
        item.classList.add("fx-enter-up");
        item.style.animationDelay = `${Math.min(index * 35, 280)}ms`;
      });
    }
    $("#breadcrumbs").innerHTML = `<span>Workspace</span><i class="ph ph-caret-right"></i><strong>${names[view]}</strong>`;
    if (view === "chat") loadConversations();
    if (view === "vault") loadVaultNotes();
    if (view === "projects") loadProjects();
    if (view === "desktop") loadDesktop();
  };

  function setOrosCoreState(cognitiveState) {
    const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
    const accent2 = getComputedStyle(document.documentElement).getPropertyValue("--accent-2").trim();
    $$(".oros-core-frame,.oros-chat-core,#chat-oros-core").forEach((frame) => {
      frame.contentWindow?.postMessage(
        { type: "OROS_COGNITIVE_STATE", state: cognitiveState, accent, accent2 },
        "*",
      );
    });
  }

  function setChatLiveCaption(text, mode = "") {
    const caption = $("#chat-live-caption");
    if (!caption) return;
    const clean = String(text || "").replace(/[#*_`]/g, "").trim();
    caption.textContent = clean;
    caption.classList.toggle("visible", Boolean(clean));
    caption.dataset.mode = mode;
  }

  $$("[data-view]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));

  const sidebarCollapse = $("#sidebar-collapse");
  const restoreSidebar = localStorage.getItem("oros-sidebar-collapsed") === "true";
  if (restoreSidebar) document.querySelector(".app-shell").classList.add("sidebar-collapsed");
  sidebarCollapse?.addEventListener("click", () => {
    const shell = document.querySelector(".app-shell");
    shell.classList.toggle("sidebar-collapsed");
    localStorage.setItem("oros-sidebar-collapsed", String(shell.classList.contains("sidebar-collapsed")));
  });

  const defaultPreferences = {
    theme: "midnight",
    font: "dm",
    intensity: 72,
    accent: "#a6f4c5",
    background: "",
  };
  let preferences;
  try {
    preferences = { ...defaultPreferences, ...JSON.parse(localStorage.getItem("oros-preferences") || "{}") };
  } catch {
    preferences = { ...defaultPreferences };
  }

  const savePreferences = () => localStorage.setItem("oros-preferences", JSON.stringify(preferences));
  const applyPreferences = () => {
    document.documentElement.dataset.theme = preferences.theme;
    document.documentElement.style.setProperty("--effect-intensity", preferences.intensity / 100);
    document.documentElement.style.setProperty("--holo-opacity", String(Math.max(.18, preferences.intensity / 100)));
    document.documentElement.style.setProperty("--accent", preferences.accent);
    const hex = preferences.accent.replace("#", "");
    const rgb = hex.length === 6
      ? `${parseInt(hex.slice(0, 2), 16)}, ${parseInt(hex.slice(2, 4), 16)}, ${parseInt(hex.slice(4, 6), 16)}`
      : "166, 244, 197";
    document.documentElement.style.setProperty("--accent-rgb", rgb);
    document.documentElement.style.setProperty("--custom-bg", preferences.background ? `url("${preferences.background}")` : "none");
    const fontRules = {
      dm: '"DM Sans", sans-serif',
      inter: 'Inter, sans-serif',
      mono: '"JetBrains Mono", monospace',
      system: 'ui-sans-serif, system-ui, sans-serif',
    };
    document.documentElement.style.setProperty("--sans", fontRules[preferences.font] || fontRules.dm);
    $$(".theme-card").forEach((card) => card.classList.toggle("active", card.dataset.theme === preferences.theme));
    setTimeout(() => setOrosCoreState(state.view === "chat" ? "idle" : "idle"), 0);
  };

  applyPreferences();
  $$(".theme-card").forEach((card) => card.addEventListener("click", () => {
    preferences.theme = card.dataset.theme;
    savePreferences();
    applyPreferences();
    toast("Tema atualizado", "palette");
  }));
  $("#theme-button").addEventListener("click", () => {
    const themes = ["midnight", "singularity", "titanium", "aurora", "ember", "paper"];
    const next = themes[(themes.indexOf(preferences.theme) + 1) % themes.length];
    preferences.theme = next;
    savePreferences();
    applyPreferences();
    toast(`Tema ${next}`, "palette");
  });
  $("#font-family").value = preferences.font;
  $("#font-family").addEventListener("change", (event) => {
    preferences.font = event.target.value;
    savePreferences();
    applyPreferences();
  });
  $("#effect-intensity").value = preferences.intensity;
  $("#effect-intensity").addEventListener("input", (event) => {
    preferences.intensity = Number(event.target.value);
    applyPreferences();
  });
  $("#effect-intensity").addEventListener("change", savePreferences);
  $("#accent-color").value = preferences.accent;
  $("#accent-color").addEventListener("input", (event) => {
    preferences.accent = event.target.value;
    applyPreferences();
  });
  $("#accent-color").addEventListener("change", savePreferences);
  $("#background-image").addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      toast("Use PNG, JPEG ou WebP", "warning-circle");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast("Imagem maior que 5 MB", "warning-circle");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      preferences.background = reader.result;
      savePreferences();
      applyPreferences();
      toast("Fundo personalizado ativado", "image");
    };
    reader.readAsDataURL(file);
  });
  $("#clear-background").addEventListener("click", () => {
    preferences.background = "";
    savePreferences();
    applyPreferences();
    toast("Fundo restaurado", "broom");
  });

  setTimeout(() => $("#boot").classList.add("done"), 1800);

  const now = new Date();
  const day = now.toLocaleDateString("pt-BR", { weekday: "long" });
  const time = now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const greeting = now.getHours() < 12 ? "Bom dia" : now.getHours() < 18 ? "Boa tarde" : "Boa noite";
  const homeHero = $(".home-hero h1");
  if (homeHero) {
    homeHero.classList.add("terminal-title");
    const fullText = `${greeting}, Marissa.`;
    homeHero.innerHTML = `<em></em>`;
    const target = homeHero.querySelector("em");
    let typed = 0;
    const typeGreeting = () => {
      if (typed >= fullText.length) {
        target.textContent = fullText;
        return;
      }
      const character = fullText[typed];
      target.textContent += character;
      typed++;
      setTimeout(typeGreeting, 35 + (typed % 4) * 18);
    };
    setTimeout(typeGreeting, 350);
  }
  const homeEyebrow = $(".home-hero .eyebrow");
  if (homeEyebrow) homeEyebrow.innerHTML = `<span></span> ${day} · ${time}`;

  async function api(path, options = {}) {
    const response = await fetch(path, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Falha na operação");
    return payload;
  }

  async function loadStatus() {
    try {
      const [status, notes, projects, windows] = await Promise.all([
        api("/api/capabilities/status"),
        api("/api/vault/notes"),
        api("/api/projects"),
        api("/api/capabilities/windows"),
      ]);
      state.notes = notes.notes || [];
      state.projects = projects.projects || [];
      state.windows = windows.windows || [];
      if (status.ollama?.installed_models?.length) {
        const model = status.ollama.active_model || status.ollama.installed_models[0];
        $("#chat-status").textContent = `Local · ${model}`;
      }
      $("#note-count").textContent = state.notes.length;
      $("#project-count").textContent = state.projects.length;
      $("#window-count").textContent = state.windows.length;
      renderRecentNotes();
      renderRecentProjects();
      renderContinue();
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  }

  function renderRecentNotes() {
    $("#recent-notes").innerHTML = state.notes.slice(0, 7).map((note) => `
      <button class="recent-note" data-note="${escapeHtml(note.path)}">
        <i class="ph ph-file-text"></i><span>${escapeHtml(note.name)}</span>
      </button>
    `).join("") || `<div class="recent-note"><i class="ph ph-files"></i><span>Nenhuma nota</span></div>`;
    $$(".recent-note[data-note]").forEach((button) => button.addEventListener("click", () => openNote(button.dataset.note)));
  }

  function renderRecentProjects() {
    $("#recent-projects").innerHTML = state.projects.slice(0, 4).map((project) => `
      <button class="project-mini" data-project="${escapeHtml(project.path)}">
        <i class="ph ph-code"></i>
        <strong>${escapeHtml(project.name)}</strong>
        <span>${escapeHtml(project.language || "Projeto")} · ${project.git ? escapeHtml(project.branch || "git") : "local"}</span>
      </button>
    `).join("");
  }

  function renderContinue() {
    const items = [
      state.notes[0] ? { icon: "notebook", title: state.notes[0].name, meta: "Vault · Markdown", note: state.notes[0].path } : null,
      state.projects[0] ? { icon: "code", title: state.projects[0].name, meta: `${state.projects[0].language || "Projeto"} · ${state.projects[0].branch || "local"}`, project: state.projects[0].path } : null,
      { icon: "chat-circle-dots", title: "Nova conversa com OROS", meta: "Assistente local" },
    ].filter(Boolean);
    $("#continue-list").innerHTML = items.map((item, index) => `
      <button class="continue-item" data-index="${index}">
        <span class="continue-icon"><i class="ph ph-${item.icon}"></i></span>
        <span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.meta)}</small></span>
        <i class="ph ph-arrow-right"></i>
      </button>
    `).join("");
    $$(".continue-item").forEach((button, index) => button.addEventListener("click", () => {
      const item = items[index];
      if (item.note) openNote(item.note);
      else if (item.project) setView("projects");
      else setView("chat");
    }));
  }

  async function loadConversations() {
    try {
      const payload = await api("/api/chat/history");
      const conversations = payload.conversations || [];
      $("#chat-count").textContent = conversations.length;
      $("#conversation-list").innerHTML = conversations.map((item) => `
        <button class="conversation-item ${item.id === state.conversationId ? "active" : ""}" data-conversation="${item.id}">
          <i class="ph ph-chat-circle"></i><span>${escapeHtml(item.title)}</span>
        </button>
      `).join("") || `<div class="conversation-item"><i class="ph ph-chats"></i><span>Sem conversas</span></div>`;
      $$(".conversation-item[data-conversation]").forEach((button) => button.addEventListener("click", () => openConversation(Number(button.dataset.conversation))));
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  }

  async function createConversation() {
    const payload = await api("/api/chat/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Nova conversa" }),
    });
    state.conversationId = payload.conversation_id;
    $("#chat-title").textContent = "Nova conversa";
    $("#chat-messages").innerHTML = welcomeHtml();
    $("#chat-messages").insertAdjacentHTML("afterbegin", `<iframe id="chat-oros-core" class="chat-oros-core" src="/oros-core.svg" title="Núcleo orbital do OROS"></iframe>`);
    $("#chat-messages").classList.remove("conversation-active");
    setChatLiveCaption("", "idle");
    setTimeout(() => setOrosCoreState("idle"), 80);
    bindSuggestions();
    await loadConversations();
  }

  function welcomeHtml() {
    return `<div class="welcome-state"><div id="chat-live-caption" class="chat-live-caption"></div></div>`;
  }

  function bindSuggestions() {
    $$(".suggestions button").forEach((button) => button.addEventListener("click", () => {
      $("#chat-input").value = button.dataset.prompt;
      sendMessage();
    }));
  }

  async function openConversation(id) {
    const payload = await api(`/api/chat/history/${id}`);
    state.conversationId = id;
    $("#chat-title").textContent = payload.conversation.title;
    $("#chat-messages").innerHTML = `<iframe id="chat-oros-core" class="chat-oros-core" src="/oros-core.svg" title="Núcleo orbital do OROS"></iframe>${payload.messages.map(renderMessage).join("") || welcomeHtml()}`;
    $("#chat-messages").classList.toggle("conversation-active", payload.messages.length > 0);
    const lastAssistant = [...payload.messages].reverse().find((message) => message.role === "assistant");
    setChatLiveCaption(lastAssistant?.content || "", "oros");
    setTimeout(() => setOrosCoreState(payload.messages.length ? "idle" : "idle"), 80);
    await loadConversations();
    bindSuggestions();
    $("#chat-messages").scrollTop = $("#chat-messages").scrollHeight;
  }

  function renderMessage(message) {
    const user = message.role === "user";
    const assistant = message.role === "assistant";
    let body = escapeHtml(message.content).replace(/\n/g, "<br>");
    if (assistant) {
      const data = message.payload || {};
      if (data.answer) body = renderMarkdown(data.answer);
      else body = renderMarkdown(message.content);
      const sources = (data.sources || []).map((source) => `<a href="${escapeHtml(source.url || "#")}" target="_blank" rel="noreferrer"><i class="ph ph-link"></i>${escapeHtml(source.title)}</a>`).join("");
      if (sources) body += `<div class="sources-inline">${sources}</div>`;
    }
    return `<article class="message ${user ? "user" : "assistant"}"><div class="message-avatar"><i class="ph ${user ? "ph-user" : "ph-sparkle"}"></i></div><div class="message-body"><div class="message-meta"><strong>${user ? "Você" : "OROS"}</strong><span>Agora</span></div><div class="message-content">${body}</div></div></article>`;
  }

  function renderMarkdown(content) {
    if (!window.marked || !window.DOMPurify) return escapeHtml(content).replace(/\n/g, "<br>");
    marked.setOptions({ breaks: true, gfm: true });
    return DOMPurify.sanitize(marked.parse(content));
  }

  async function sendMessage() {
    const input = $("#chat-input");
    const message = input.value.trim();
    if (!message) return;
    if (!state.conversationId) {
      await createConversation();
    }
    setChatLiveCaption(message, "you");
    const messages = $("#chat-messages");
    messages.querySelector(".welcome-state")?.remove();
    messages.classList.add("conversation-active");
    messages.insertAdjacentHTML("beforeend", renderMessage({ role: "user", content: message }));
    messages.insertAdjacentHTML("beforeend", `<article class="message assistant" id="typing-message"><div class="message-avatar"><i class="ph ph-sparkle"></i></div><div class="message-body"><div class="message-meta"><strong>OROS</strong></div><div class="typing"><i></i><i></i><i></i></div></div></article>`);
    input.value = "";
    input.style.height = "42px";
    messages.scrollTop = messages.scrollHeight;
    $("#send-message").disabled = true;
    $("#chat-status").textContent = "Pensando";
    setOrosCoreState("processing");
    try {
      const payload = await api("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, conversation_id: state.conversationId, history: [] }),
      });
      $("#typing-message")?.remove();
      messages.insertAdjacentHTML("beforeend", renderMessage({ role: "assistant", content: payload.answer, payload }));
      setChatLiveCaption(payload.answer, "oros");
      if (state.voiceReply && "speechSynthesis" in window) {
        setOrosCoreState("speaking");
        const spoken = payload.answer.replace(/[#*_`\[\]]/g, " ").slice(0, 1200);
        const utterance = new SpeechSynthesisUtterance(spoken);
        utterance.lang = "pt-BR";
        utterance.rate = 1.04;
        utterance.onend = () => setOrosCoreState("idle");
        utterance.onerror = () => setOrosCoreState("idle");
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
        state.voiceReply = false;
      } else {
        setOrosCoreState("idle");
      }
      if (payload.conversation_id) state.conversationId = payload.conversation_id;
      await loadConversations();
    } catch (error) {
      $("#typing-message")?.remove();
      messages.insertAdjacentHTML("beforeend", renderMessage({ role: "assistant", content: `Não consegui concluir a ação: ${error.message}` }));
      setOrosCoreState("idle");
    } finally {
      $("#send-message").disabled = false;
      $("#chat-status").textContent = "OROS 1.0";
      messages.scrollTop = messages.scrollHeight;
    }
  }

  $("#send-message").addEventListener("click", sendMessage);
  $("#chat-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); }
  });
  $("#chat-input").addEventListener("input", (event) => {
    event.target.style.height = "42px";
    event.target.style.height = `${Math.min(event.target.scrollHeight, 160)}px`;
  });
  $("#new-chat").addEventListener("click", createConversation);
  bindSuggestions();

  $("#home-command-send").addEventListener("click", () => {
    const command = $("#home-command").value.trim();
    if (!command) return;
    setView("chat");
    $("#chat-input").value = command;
    sendMessage();
  });
  $("#home-command").addEventListener("keydown", (event) => {
    if (event.key === "Enter") $("#home-command-send").click();
  });

  async function loadVaultNotes(query = "") {
    try {
      const payload = await api(`/api/vault/notes${query ? `?query=${encodeURIComponent(query)}` : ""}`);
      state.notes = payload.notes || [];
      renderVaultTree();
      $("#note-count").textContent = state.notes.length;
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  }

  function renderVaultTree() {
    const folders = new Map();
    state.notes.forEach((note) => {
      const parts = note.path.split("/");
      const folder = parts.length > 1 ? parts.slice(0, -1).join("/") : "Raiz";
      if (!folders.has(folder)) folders.set(folder, []);
      folders.get(folder).push(note);
    });
    $("#vault-tree").innerHTML = [...folders.entries()].map(([folder, notes], index) => `
      <div class="tree-group">
        <button class="tree-folder ${index < 3 ? "open" : ""}" data-folder="${escapeHtml(folder)}">
          <i class="ph ph-caret-right"></i><i class="ph ph-folder"></i><span>${escapeHtml(folder)}</span>
        </button>
        <div class="tree-children ${index < 3 ? "open" : ""}">
          ${notes.slice(0, 80).map((note) => `<button class="tree-note ${state.currentNote === note.path ? "active" : ""}" data-note="${escapeHtml(note.path)}"><i class="ph ph-file-text"></i><span>${escapeHtml(note.name)}</span></button>`).join("")}
        </div>
      </div>
    `).join("");
    $$(".tree-folder").forEach((button) => button.addEventListener("click", () => {
      button.classList.toggle("open");
      button.nextElementSibling.classList.toggle("open");
    }));
    $$(".tree-note").forEach((button) => button.addEventListener("click", () => openNote(button.dataset.note)));
  }

  async function openNote(path) {
    setView("vault");
    try {
      const payload = await api(`/api/vault/note?path=${encodeURIComponent(path)}`);
      state.currentNote = path;
      $("#note-path").textContent = path;
      $("#note-editor").value = payload.content;
      updatePreview();
      $$(".tree-note").forEach((item) => item.classList.toggle("active", item.dataset.note === path));
      toast("Nota aberta", "file-text");
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  }

  function updatePreview() {
    $("#note-preview").innerHTML = renderMarkdown($("#note-editor").value);
  }

  $("#note-editor").addEventListener("input", updatePreview);
  $("#note-editor").addEventListener("input", () => {
    $("#save-note").classList.add("pending");
  });
  $("#vault-search").addEventListener("input", (event) => {
    clearTimeout(window.vaultSearchTimer);
    window.vaultSearchTimer = setTimeout(() => loadVaultNotes(event.target.value.trim()), 220);
  });
  $("#save-note").addEventListener("click", saveNote);
  async function saveNote() {
    if (!state.currentNote) { toast("Selecione uma nota", "warning-circle"); return; }
    try {
      await api("/api/vault/note", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: state.currentNote, content: $("#note-editor").value, mode: "write" }),
      });
      $("#save-note").classList.remove("pending");
      toast("Nota salva", "check-circle");
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  }
  $("#preview-toggle").addEventListener("click", () => $(".editor-layout").classList.toggle("preview-off"));
  $("#delete-note").addEventListener("click", async () => {
    if (!state.currentNote) return;
    if (!confirm(`Mover "${state.currentNote}" para a lixeira?`)) return;
    try {
      await api(`/api/vault/note?path=${encodeURIComponent(state.currentNote)}`, { method: "DELETE" });
      state.currentNote = null;
      $("#note-editor").value = "";
      $("#note-preview").innerHTML = "";
      $("#note-path").textContent = "Nenhuma nota selecionada";
      await loadVaultNotes();
      toast("Nota movida para a lixeira", "trash");
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  });

  async function newVaultNote() {
    setView("vault");
    const name = prompt("Nome da nota", "Nova nota");
    if (!name) return;
    const safeName = name.replace(/[\/\\]/g, "-").replace(/\.md$/i, "");
    const path = `00 Entrada/${safeName}.md`;
    try {
      await api("/api/vault/note", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, content: `# ${safeName}\n\n`, mode: "write" }),
      });
      await loadVaultNotes();
      await openNote(path);
      toast("Nota criada", "file-plus");
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  }
  $("#new-vault-note").addEventListener("click", newVaultNote);
  $("#new-note").addEventListener("click", newVaultNote);

  async function loadProjects() {
    const grid = $("#project-grid");
    grid?.classList.add("fx-loading");
    grid?.setAttribute("aria-busy", "true");
    try {
      const payload = await api("/api/projects");
      state.projects = payload.projects || [];
      $("#git-project-count").textContent = state.projects.filter((project) => project.git).length;
      $("#ready-project-count").textContent = state.projects.filter((project) => project.language).length;
      $("#project-count").textContent = state.projects.length;
      setTimeout(() => {
        renderProjectGrid();
        grid?.classList.remove("fx-loading");
        grid?.setAttribute("aria-busy", "false");
      }, 420);
    } catch (error) {
      grid?.classList.remove("fx-loading");
      grid?.setAttribute("aria-busy", "false");
      toast(error.message, "warning-circle");
    }
  }

  function renderProjectGrid() {
    const grid = $("#project-grid");
    const layout = $$("#project-layout button.active")[0]?.dataset.layout || "grid";
    if (!grid) return;

    const cardMarkup = (project, extraClass = "") => `
      <article class="project-card ${extraClass}" data-project="${escapeHtml(project.path)}">
        <div class="project-card-head">
          <span class="project-code"><i class="ph ph-code"></i></span>
          ${project.git ? `<span class="git-status"><i></i>Git</span>` : ""}
        </div>
        <h3>${escapeHtml(project.name)}</h3>
        <p>${escapeHtml(project.path)}</p>
        <div class="project-card-foot">
          <span>${escapeHtml(project.language || "Projeto")} · ${escapeHtml(project.branch || "local")}</span>
          <button title="Abrir projeto"><i class="ph ph-arrow-square-out"></i></button>
        </div>
      </article>
    `;

    grid.className = `project-grid ${layout}`;
    if (layout === "kanban") {
      const columns = [
        { title: "Planejado", icon: "circle", items: state.projects.filter((_, index) => index % 3 === 0) },
        { title: "Em desenvolvimento", icon: "pulse", items: state.projects.filter((_, index) => index % 3 === 1) },
        { title: "Ativo", icon: "check-circle", items: state.projects.filter((_, index) => index % 3 === 2) },
      ];
      grid.innerHTML = columns.map((column) => `
        <section class="kanban-column">
          <header class="kanban-column-header"><span><i></i>${column.title}</span><b>${column.items.length}</b></header>
          ${column.items.map((project) => cardMarkup(project, "kanban-card")).join("")}
        </section>
      `).join("");
    } else if (layout === "gallery") {
      grid.innerHTML = state.projects.map((project) => cardMarkup(project, "gallery-card")).join("");
    } else {
      grid.innerHTML = state.projects.map((project) => cardMarkup(project)).join("");
    }
    $$(".project-card", grid).forEach((card, index) => {
      card.classList.add("fx-enter-scale");
      card.style.animationDelay = `${Math.min(index * 28, 280)}ms`;
    });
  }

  $$(".segmented button").forEach((button) => button.addEventListener("click", () => {
    $$(".segmented button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    renderProjectGrid();
  }));
  $("#open-terminal").addEventListener("click", () => toast("Terminal integrado disponível no Desktop", "terminal"));

  async function loadDesktop() {
    try {
      const payload = await api("/api/capabilities/windows");
      state.windows = payload.windows || [];
      $("#window-count").textContent = state.windows.length;
      $("#window-list").innerHTML = state.windows.map((window) => `
        <div class="window-item">
          <span class="window-icon"><i class="ph ${window.class?.toLowerCase().includes("chrome") ? "ph-browser" : "ph-window"}"></i></span>
          <span><strong>${escapeHtml(window.title || "Sem título")}</strong><small>${escapeHtml(window.class || "Janela")} · Workspace ${escapeHtml(window.workspace || "?")}</small></span>
          <button data-address="${escapeHtml(window.address)}" title="Focar janela"><i class="ph ph-crosshair"></i></button>
        </div>
      `).join("") || `<div class="screen-empty"><i class="ph ph-monitor"></i><span>Nenhuma janela detectada</span></div>`;
      const [contextPayload, sentinelPayload] = await Promise.all([
        api("/api/context/active"),
        api("/api/sentinel/status"),
      ]);
      const activeTitle = contextPayload.active_window?.title || "Nenhuma janela ativa";
      $("#active-context-title").textContent = activeTitle;
      const traceCount = contextPayload.trace?.locations?.length || 0;
      $("#active-context").innerHTML = `
        <div><strong>Janela:</strong> ${escapeHtml(contextPayload.active_window?.class || "desconhecida")}</div>
        <div><strong>Projeto:</strong> ${escapeHtml(contextPayload.project?.name || "não identificado")}</div>
        <div><strong>Clipboard:</strong> ${contextPayload.clipboard?.available ? `${traceCount ? "trace detectado" : "conteúdo disponível"}` : "indisponível"}</div>
      `;
      const diskPercent = sentinelPayload.disk?.percent || "0%";
      $("#sentinel-title").textContent = sentinelPayload.warnings?.length ? `${sentinelPayload.warnings.length} alertas` : "Sistema saudável";
      $("#sentinel-status").innerHTML = `
        <div><strong>Disco:</strong> ${escapeHtml(diskPercent)}</div>
        <div><strong>Pacotes:</strong> ${sentinelPayload.packages?.updates?.length || 0} atualizações</div>
        ${sentinelPayload.warnings?.length ? `<div class="warning">${sentinelPayload.warnings.map(escapeHtml).join("<br>")}</div>` : "<div>Sem warnings críticos</div>"}
      `;
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  }

  async function captureScreen() {
    try {
      toast("Capturando tela", "camera");
      await api("/api/capabilities/screen/capture", { method: "POST" });
      $("#screen-frame").innerHTML = `<img src="/api/capabilities/screen/image?t=${Date.now()}" alt="Captura atual da tela">`;
      await loadDesktop();
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  }
  $("#capture-button").addEventListener("click", () => { setView("desktop"); captureScreen(); });
  $("#desktop-capture").addEventListener("click", captureScreen);
  $("#desktop-refresh").addEventListener("click", loadDesktop);
  $("#warroom-project")?.addEventListener("click", async () => {
    const project = state.projects[0];
    if (!project) {
      await loadProjects();
    }
    const target = state.projects[0];
    if (!target) {
      toast("Nenhum projeto disponível", "warning-circle");
      return;
    }
    try {
      const result = await api("/api/war-room", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project: target.path }),
      });
      toast(result.ok ? "War Room organizado" : "War Room iniciou parcialmente", result.ok ? "scan" : "warning-circle");
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  });
  $("#notifications-toggle")?.addEventListener("click", async () => {
    try {
      await api("/api/terminal/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "dunstctl set-paused true", working_dir: "/home/borges/dev", approved: false }),
      });
      toast("Notificações silenciadas", "bell-slash");
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  });
  $("#attach-screen").addEventListener("click", async () => {
    setView("chat");
    await captureScreen();
    $("#chat-input").value = "Analise a captura atual da minha tela e explique o que está acontecendo.";
  });
  $("#focus-oros").addEventListener("click", () => toast("OROS já está em foco neste workspace", "crosshair"));

  $("#quick-search").addEventListener("click", () => toast("Busca rápida em desenvolvimento", "magnifying-glass"));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.view === "chat") {
      setView("home");
      return;
    }
    if (event.metaKey || event.ctrlKey) {
      if (event.key.toLowerCase() === "h") { event.preventDefault(); setView("home"); }
      if (event.key.toLowerCase() === "v") { event.preventDefault(); setView("vault"); }
    }
  });

  function initHolographicCanvas() {
    const canvas = $("#holo-canvas");
    if (!canvas) return;
    const context = canvas.getContext("2d");
    let width = 0;
    let height = 0;
    let particles = [];
    const pointer = { x: innerWidth * .72, y: innerHeight * .28 };

    const resize = () => {
      const ratio = Math.min(devicePixelRatio || 1, 2);
      width = innerWidth;
      height = innerHeight;
      canvas.width = width * ratio;
      canvas.height = height * ratio;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      particles = Array.from({ length: Math.min(110, Math.floor(width * .07)) }, (_, index) => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - .5) * .12,
        vy: (Math.random() - .5) * .12,
        r: index % 11 === 0 ? 1.4 : .55 + Math.random() * .7,
        phase: Math.random() * Math.PI * 2,
      }));
    };
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", (event) => {
      pointer.x += (event.clientX - pointer.x) * .08;
      pointer.y += (event.clientY - pointer.y) * .08;
    });
    resize();

    const draw = (time) => {
      context.clearRect(0, 0, width, height);
      const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#a6f4c5";
      const theme = document.documentElement.dataset.theme;

      if (theme === "titanium") {
        context.font = "11px JetBrains Mono";
        const columns = Math.ceil(width / 22);
        for (let column = 0; column < columns; column++) {
          const seed = (column * 47 + Math.floor(time * .018)) % 83;
          const x = column * 22 + 8;
          for (let row = 0; row < 14; row++) {
            const y = ((seed * 19 + row * 24 + time * .055) % (height + 100)) - 50;
            const glyph = "01アイウエオカキクケコサシスセソ"[((seed + row + column) % 34)];
            context.globalAlpha = .08 + (row / 14) * .13;
            context.fillStyle = row > 11 ? "#d9fff5" : accent;
            context.fillText(glyph, x, y);
          }
        }
      } else if (theme === "ember") {
        context.globalCompositeOperation = "lighter";
        for (let i = 0; i < 46; i++) {
          const x = (i * 197.3 + time * (.018 + (i % 5) * .005)) % (width + 40) - 20;
          const y = height - ((i * 83.7 + time * (.08 + (i % 7) * .01)) % height);
          context.beginPath();
          context.fillStyle = i % 3 ? "#ffb36b" : "#ff6e40";
          context.globalAlpha = .10 + (i % 5) * .025;
          context.arc(x, y, .5 + (i % 4) * .55, 0, Math.PI * 2);
          context.fill();
        }
        context.globalCompositeOperation = "source-over";
      } else if (theme === "singularity") {
        const nodes = state.notes.length ? state.notes.slice(0, 42) : particles.slice(0, 42);
        for (let i = 0; i < nodes.length; i++) {
          const node = nodes[i];
          const x = width * (.18 + ((i * 67 + i * i * 13) % 74) / 100);
          const y = height * (.12 + ((i * 41 + i * i * 7) % 74) / 100);
          const pulse = 1 + Math.sin(time * .0012 + i) * .18;
          for (let j = i + 1; j < nodes.length; j++) {
            if ((i * 7 + j * 3) % 13 !== 0) continue;
            const jx = width * (.18 + ((j * 67 + j * j * 13) % 74) / 100);
            const jy = height * (.12 + ((j * 41 + j * j * 7) % 74) / 100);
            context.beginPath();
            context.strokeStyle = accent;
            context.globalAlpha = .055;
            context.moveTo(x, y);
            context.quadraticCurveTo((x + jx) / 2 + Math.sin(time * .0003) * 40, (y + jy) / 2, jx, jy);
            context.stroke();
          }
          context.beginPath();
          context.fillStyle = i % 9 === 0 ? "#74d8ff" : accent;
          context.globalAlpha = i % 9 === 0 ? .55 : .24;
          context.arc(x, y, (i % 9 === 0 ? 2.2 : 1.2) * pulse, 0, Math.PI * 2);
          context.fill();
        }
      } else {
        for (const particle of particles) {
          particle.x += particle.vx * (theme === "aurora" ? 1.7 : 1);
          particle.y += particle.vy * (theme === "aurora" ? 1.7 : 1);
          if (particle.x < 0) particle.x = width;
          if (particle.x > width) particle.x = 0;
          if (particle.y < 0) particle.y = height;
          if (particle.y > height) particle.y = 0;
          const dx = particle.x - pointer.x;
          const dy = particle.y - pointer.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          const glow = distance < 220 ? (1 - distance / 220) * .34 : 0;
          context.beginPath();
          context.fillStyle = accent;
          context.globalAlpha = (theme === "paper" ? .06 : .12) + glow;
          context.arc(particle.x, particle.y, particle.r + glow * 2, 0, Math.PI * 2);
          context.fill();
        }
        if (theme === "aurora") {
          context.save();
          context.globalCompositeOperation = "lighter";
          for (let ribbon = 0; ribbon < 4; ribbon++) {
            context.beginPath();
            for (let x = -50; x <= width + 50; x += 18) {
              const y = height * (.22 + ribbon * .11) + Math.sin(x * .007 + time * .00045 + ribbon) * (24 + ribbon * 5);
              if (x === -50) context.moveTo(x, y); else context.lineTo(x, y);
            }
            context.strokeStyle = ribbon % 2 ? "#70a7ff" : accent;
            context.globalAlpha = .055;
            context.lineWidth = 18 - ribbon * 3;
            context.filter = "blur(12px)";
            context.stroke();
          }
          context.restore();
        }
        const halo = Math.min(width, height) * .11;
        context.save();
        context.translate(pointer.x, pointer.y);
        context.rotate(time * .00008);
        for (let ring = 0; ring < 3; ring++) {
          context.beginPath();
          context.setLineDash([5 + ring * 3, 14 + ring * 8]);
          context.lineDashOffset = -time * (.018 + ring * .006);
          context.strokeStyle = accent;
          context.globalAlpha = .08 - ring * .012;
          context.lineWidth = ring === 0 ? 1.2 : .7;
          context.ellipse(0, 0, halo + ring * 31, (halo + ring * 31) * (.48 + ring * .08), ring * .42, 0, Math.PI * 2);
          context.stroke();
        }
        context.restore();
      }
      context.globalAlpha = 1;
      requestAnimationFrame(draw);
    };
    requestAnimationFrame(draw);
  }

  function initVoiceInterface() {
    const voiceButton = $("#voice-button");
    const voiceConsole = $("#voice-console");
    const voiceState = $("#voice-state");
    const voiceTranscript = $("#voice-transcript");
    const voiceStop = $("#voice-stop");
    const bars = $("#voice-bars");
    bars.innerHTML = Array.from({ length: 24 }, (_, index) =>
      `<i style="animation-delay:${(index % 7) * -.09}s"></i>`
    ).join("");

    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let recognitionActive = false;
    let mediaStream = null;
    let audioContext = null;
    let analyser = null;
    let animationFrame = null;

    const stopAudioAnalysis = () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
      if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());
      if (audioContext && audioContext.state !== "closed") audioContext.close().catch(() => {});
      mediaStream = null;
      audioContext = null;
      analyser = null;
    };

    const stopVoice = () => {
      handsFree = false;
      localStorage.setItem("oros-hands-free", "false");
      recognitionActive = false;
      if (recognition) {
        try { recognition.stop(); } catch {}
      }
      stopAudioAnalysis();
      voiceConsole.classList.remove("active", "listening");
      voiceButton.classList.remove("listening");
      voiceState.textContent = "Voz disponível";
      voiceTranscript.textContent = "Toque no microfone para falar";
      setOrosCoreState("idle");
    };

    const startAudioAnalysis = async () => {
      if (!navigator.mediaDevices?.getUserMedia) return;
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioContext = new AudioContext();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 64;
        const source = audioContext.createMediaStreamSource(mediaStream);
        source.connect(analyser);
        const values = new Uint8Array(analyser.frequencyBinCount);
        const animateBars = () => {
          analyser.getByteFrequencyData(values);
          $$("#voice-bars i").forEach((bar, index) => {
            const level = values[index % values.length] / 255;
            bar.style.height = `${4 + level * 27}px`;
            bar.style.opacity = String(.35 + level * .65);
          });
          animationFrame = requestAnimationFrame(animateBars);
        };
        animateBars();
      } catch (error) {
        voiceTranscript.textContent = "Permissão de microfone recusada";
        toast("Permita o microfone para ativar a voz", "microphone-slash");
      }
    };

    let wakeActive = false;
    let wakeArmed = false;
    let handsFree = false;

    const startVoice = async (automatic = false) => {
      if (!Recognition) {
        voiceConsole.classList.add("active");
        voiceState.textContent = "Recurso indisponível";
        voiceTranscript.textContent = "Seu navegador não oferece reconhecimento de voz";
        toast("Reconhecimento de voz não suportado", "warning-circle");
        return;
      }
      if (automatic) wakeArmed = true;
      localStorage.setItem("oros-hands-free", "true");
      recognition = new Recognition();
      recognition.lang = "pt-BR";
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.onstart = () => {
        recognitionActive = true;
        handsFree = true;
        setOrosCoreState("listening");
        voiceConsole.classList.add("active", "listening");
        voiceButton.classList.add("listening");
        voiceState.textContent = "Escutando pelo wake word";
        voiceTranscript.textContent = 'Diga "OROS"';
        startAudioAnalysis();
      };
      recognition.onresult = (event) => {
        let finalText = "";
        let interimText = "";
        for (let index = event.resultIndex; index < event.results.length; index++) {
          if (event.results[index].isFinal) finalText += event.results[index][0].transcript;
          else interimText += event.results[index][0].transcript;
        }
        const heard = (finalText || interimText || "").trim();
        voiceTranscript.textContent = heard || 'Diga "OROS"';
        if (heard) setChatLiveCaption(heard, "you");
        if (finalText) {
          const normalized = finalText.toLowerCase();
          const wakeMatch = normalized.match(/\b(?:oros|joros|óros|jarvis)\b/i);
          if (!wakeActive && wakeMatch) {
            wakeActive = true;
            const rest = finalText.slice(normalized.indexOf(wakeMatch[0]) + wakeMatch[0].length).trim();
            voiceState.textContent = "OROS ativado";
            voiceTranscript.textContent = rest || "Pode falar";
            state.voiceReply = true;
            if (rest) {
              $("#chat-input").value = rest;
              setTimeout(sendMessage, 180);
              wakeActive = false;
            }
          } else if (wakeActive) {
            $("#chat-input").value = finalText.trim();
            voiceTranscript.textContent = finalText.trim();
            state.voiceReply = true;
            setTimeout(sendMessage, 180);
            wakeActive = false;
          }
        }
      };
      recognition.onerror = (event) => {
        if (event.error === "no-speech" || event.error === "aborted") return;
        voiceState.textContent = "Reconhecimento interrompido";
        voiceTranscript.textContent = event.error === "not-allowed" ? "Permissão de microfone recusada" : `Erro: ${event.error}`;
      };
      recognition.onend = () => {
        if (!handsFree) return;
        setTimeout(() => {
          if (!handsFree) return;
          try { recognition.start(); } catch {}
        }, 250);
      };
      recognition.start();
    };

    voiceButton.addEventListener("click", () => {
      if (handsFree) {
        handsFree = false;
        localStorage.setItem("oros-hands-free", "false");
        stopVoice();
      }
      else {
        setView("chat");
        startVoice();
      }
    });
    voiceStop.addEventListener("click", stopVoice);
    $("#global-voice-button")?.addEventListener("click", () => {
      setView("chat");
      if (handsFree) {
        localStorage.setItem("oros-hands-free", "false");
        stopVoice();
      }
      else startVoice();
    });
    if (localStorage.getItem("oros-hands-free") === "true") {
      setTimeout(() => startVoice(true), 1800);
    }
  }

  initHolographicCanvas();
  initVoiceInterface();
  setTimeout(() => setOrosCoreState("idle"), 2000);

  loadStatus();
  loadConversations();
  setView("home");
});
