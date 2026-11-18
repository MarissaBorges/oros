document.addEventListener("DOMContentLoaded", () => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = { view: "home", conversationId: null, currentNote: null, projects: [], notes: [], windows: [], voiceReply: false };

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
    $$(".view").forEach((item) => item.classList.toggle("active", item.id === `view-${view}`));
    $$(".rail-button[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
    $$(".context-nav button").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
    $("#breadcrumbs").innerHTML = `<span>Workspace</span><i class="ph ph-caret-right"></i><strong>${names[view]}</strong>`;
    if (view === "chat") loadConversations();
    if (view === "vault") loadVaultNotes();
    if (view === "projects") loadProjects();
    if (view === "desktop") loadDesktop();
  };

  $$("[data-view]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));

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

  setTimeout(() => $("#boot").classList.add("done"), 900);

  const now = new Date();
  const day = now.toLocaleDateString("pt-BR", { weekday: "long" });
  const time = now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const greeting = now.getHours() < 12 ? "Bom dia" : now.getHours() < 18 ? "Boa tarde" : "Boa noite";
  const homeHero = $(".home-hero h1");
  if (homeHero) homeHero.innerHTML = `${greeting}, <em>Marissa.</em>`;
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
    bindSuggestions();
    await loadConversations();
  }

  function welcomeHtml() {
    return `<div class="welcome-state"><div class="oros-orb"><span></span></div><h2>Como posso ajudar?</h2><p>Posso navegar, escrever no vault, analisar projetos e controlar o ambiente.</p><div class="suggestions"><button data-prompt="Resuma os projetos que estou desenvolvendo e sugira prioridades">Resumir meus projetos</button><button data-prompt="Analise minha tela atual e diga o que você vê">Analisar minha tela</button><button data-prompt="Crie uma nota de planejamento na pasta 01 Projetos">Criar plano no vault</button></div></div>`;
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
    $("#chat-messages").innerHTML = payload.messages.map(renderMessage).join("") || welcomeHtml();
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
    const messages = $("#chat-messages");
    messages.querySelector(".welcome-state")?.remove();
    messages.insertAdjacentHTML("beforeend", renderMessage({ role: "user", content: message }));
    messages.insertAdjacentHTML("beforeend", `<article class="message assistant" id="typing-message"><div class="message-avatar"><i class="ph ph-sparkle"></i></div><div class="message-body"><div class="message-meta"><strong>OROS</strong></div><div class="typing"><i></i><i></i><i></i></div></div></article>`);
    input.value = "";
    input.style.height = "42px";
    messages.scrollTop = messages.scrollHeight;
    $("#send-message").disabled = true;
    $("#chat-status").textContent = "Pensando";
    try {
      const payload = await api("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, conversation_id: state.conversationId, history: [] }),
      });
      $("#typing-message")?.remove();
      messages.insertAdjacentHTML("beforeend", renderMessage({ role: "assistant", content: payload.answer, payload }));
      if (state.voiceReply && "speechSynthesis" in window) {
        const spoken = payload.answer.replace(/[#*_`\[\]]/g, " ").slice(0, 1200);
        const utterance = new SpeechSynthesisUtterance(spoken);
        utterance.lang = "pt-BR";
        utterance.rate = 1.04;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
        state.voiceReply = false;
      }
      if (payload.conversation_id) state.conversationId = payload.conversation_id;
      await loadConversations();
    } catch (error) {
      $("#typing-message")?.remove();
      messages.insertAdjacentHTML("beforeend", renderMessage({ role: "assistant", content: `Não consegui concluir a ação: ${error.message}` }));
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
    try {
      const payload = await api("/api/projects");
      state.projects = payload.projects || [];
      $("#git-project-count").textContent = state.projects.filter((project) => project.git).length;
      $("#ready-project-count").textContent = state.projects.filter((project) => project.language).length;
      $("#project-count").textContent = state.projects.length;
      renderProjectGrid();
    } catch (error) {
      toast(error.message, "warning-circle");
    }
  }

  function renderProjectGrid() {
    $("#project-grid").innerHTML = state.projects.map((project) => `
      <article class="project-card" data-project="${escapeHtml(project.path)}">
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
    `).join("");
  }

  $$(".segmented button").forEach((button) => button.addEventListener("click", () => {
    $$(".segmented button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    $("#project-grid").classList.toggle("timeline", button.dataset.layout === "timeline");
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
  $("#attach-screen").addEventListener("click", async () => {
    setView("chat");
    await captureScreen();
    $("#chat-input").value = "Analise a captura atual da minha tela e explique o que está acontecendo.";
  });
  $("#focus-oros").addEventListener("click", () => toast("OROS já está em foco neste workspace", "crosshair"));

  $("#quick-search").addEventListener("click", () => toast("Busca rápida em desenvolvimento", "magnifying-glass"));
  document.addEventListener("keydown", (event) => {
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
      for (const particle of particles) {
        particle.x += particle.vx;
        particle.y += particle.vy;
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
        context.globalAlpha = .12 + glow + Math.sin(time * .001 + particle.phase) * .03;
        context.arc(particle.x, particle.y, particle.r + glow * 2, 0, Math.PI * 2);
        context.fill();
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
      recognitionActive = false;
      if (recognition) {
        try { recognition.stop(); } catch {}
      }
      stopAudioAnalysis();
      voiceConsole.classList.remove("active", "listening");
      voiceButton.classList.remove("listening");
      voiceState.textContent = "Voz disponível";
      voiceTranscript.textContent = "Toque no microfone para falar";
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

    const startVoice = async () => {
      if (!Recognition) {
        voiceConsole.classList.add("active");
        voiceState.textContent = "Recurso indisponível";
        voiceTranscript.textContent = "Seu navegador não oferece reconhecimento de voz";
        toast("Reconhecimento de voz não suportado", "warning-circle");
        return;
      }
      state.voiceReply = true;
      recognition = new Recognition();
      recognition.lang = "pt-BR";
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.onstart = () => {
        recognitionActive = true;
        voiceConsole.classList.add("active", "listening");
        voiceButton.classList.add("listening");
        voiceState.textContent = "Escutando...";
        voiceTranscript.textContent = "Pode falar";
        startAudioAnalysis();
      };
      recognition.onresult = (event) => {
        let finalText = "";
        let interimText = "";
        for (let index = event.resultIndex; index < event.results.length; index++) {
          if (event.results[index].isFinal) finalText += event.results[index][0].transcript;
          else interimText += event.results[index][0].transcript;
        }
        voiceTranscript.textContent = finalText || interimText || "Pode falar";
        if (finalText) {
          $("#chat-input").value = finalText.trim();
          recognition.stop();
        }
      };
      recognition.onerror = (event) => {
        voiceState.textContent = "Reconhecimento interrompido";
        voiceTranscript.textContent = event.error === "not-allowed" ? "Permissão de microfone recusada" : `Erro: ${event.error}`;
      };
      recognition.onend = () => {
        if (recognitionActive) {
          recognitionActive = false;
          stopAudioAnalysis();
          voiceConsole.classList.remove("listening");
          voiceButton.classList.remove("listening");
          voiceState.textContent = "Transcrição concluída";
          const text = $("#chat-input").value.trim();
          if (text) setTimeout(sendMessage, 180);
        }
      };
      recognition.start();
    };

    voiceButton.addEventListener("click", () => {
      if (recognitionActive) stopVoice();
      else {
        setView("chat");
        startVoice();
      }
    });
    voiceStop.addEventListener("click", stopVoice);
  }

  initHolographicCanvas();
  initVoiceInterface();

  loadStatus();
  loadConversations();
  setView("home");
});
