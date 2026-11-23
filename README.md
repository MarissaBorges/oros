<!-- BADGES -->

[PYTHON_BADGE]: https://img.shields.io/badge/Python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[DJANGO_BADGE]: https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white
[OLLAMA_BADGE]: https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white
[WHISPER_BADGE]: https://img.shields.io/badge/Faster--Whisper-412991?style=for-the-badge
[RAG_BADGE]: https://img.shields.io/badge/RAG-8A2BE2?style=for-the-badge
[WIP_BADGE]: https://img.shields.io/badge/Status-Em%20Desenvolvimento-blue?style=for-the-badge

<!-- PROJECT -->
<h1 align="center" style="font-weight: bold;">OROS — Assistente Técnico & Voice Command Deck 🧠🎙️ (Em Desenvolvimento)</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Em%20Desenvolvimento-blue?style=for-the-badge" alt="Status Em Desenvolvimento">
  <img src="https://img.shields.io/badge/Python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python Badge">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django Badge">
  <img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama Badge">
  <img src="https://img.shields.io/badge/Faster--Whisper-412991?style=for-the-badge" alt="Faster-Whisper Badge">
  <img src="https://img.shields.io/badge/RAG-8A2BE2?style=for-the-badge" alt="RAG Badge">
</p>

<p align="center">
  <a href="#-descrição">Descrição</a> •
  <a href="#-funcionalidades">Funcionalidades</a> •
  <a href="#-destaques-técnicos">Destaques</a> •
  <a href="#-como-executar">Como Executar</a> •
  <a href="#-endpoints-principais">API</a> •
  <a href="#-documentação">Documentação</a> •
  <a href="#-roadmap-futuro">Roadmap Futuro</a>
</p>

---

## 📌 Descrição

O **OROS** é um assistente técnico pessoal *local-first* em português com interface estilo JARVIS, projetado para Arch Linux (Hyprland + PipeWire). Ele combina um orquestrador local ultrarrápido baseado em **OpenJarvis** + **Ollama**, pipeline completo de voz cross-browser, **RAG** sobre documentações locais e repositórios públicos do GitHub, memória autônoma de aprendizado e delegação de tarefas complexas de código via **Antigravity CLI (`agy`)**.

A arquitetura divide responsabilidades em três camadas:

```text
OROS Web UI (Synaptic Core SVG + FFT) / Wake Daemon PipeWire
  -> OROS Django API + SSE Stream
  -> Orquestrador OROS (OpenJarvis OrchestratorAgent + OllamaEngine)
     -> Roteamento Dinâmico de Ferramentas + Grounding ao Vivo
     -> Pipeline RAG + Memória Autônoma (SQLite FTS5 + Markdown)
     -> Delegação de Código (`agy`) + Vault + Hyprland + Guardian + Arch Sentinel
```

---

## 🚀 Funcionalidades

### Orquestração, Voz e Inteligência Local

- **Orquestrador Local-First:** Utiliza o runtime vendored do [OpenJarvis](vendor/OpenJarvis) (`OrchestratorAgent` + `OllamaEngine`) com modelos locais do Ollama (seleção automática de modelos com tool-calling como `qwen2.5:3b` e `qwen3:8b`, ajustados com `OROS_NUM_CTX=4096` para GPUs de 4 GB VRAM).
- **Voz Cross-Browser (Zen, Firefox e Chrome):**
  - **STT Local:** `FasterWhisperBackend` (`faster-whisper` `base` em CPU `int8`) via `POST /api/voice/transcribe` com `MediaRecorder` e Web Audio VAD.
  - **TTS Neural e Offline:** Português brasileiro neural via `edge-tts` (`pt-BR-AntonioNeural`), suporte a `piper-tts` local / ElevenLabs e fallback offline via `speechSynthesis` do navegador.
  - **Wake Word Always-On:** Daemon de sistema em PipeWire (`oros-wake.service`) ouvindo “OROS” mesmo com o navegador fechado, além do atalho `Alt+V` e sincronização FFT em tempo real no núcleo orbital (`frontend/oros-core.svg`).
- **Memória Autônoma de Aprendizado:** Persiste conhecimentos pesquisados em Markdown e SQLite FTS5 (`data/learned_memory/` e `data/learned-memory.sqlite3`) para consultas futuras instantâneas.

### Integrações Locais, RAG e Automação

- **RAG de Documentação e Repositórios:** Filas de ingestão e indexação de arquivos locais, documentações web e repositórios públicos do GitHub.
- **Delegação de Programação (`agy`):** Disparo e acompanhamento de jobs assíncronos de geração, depuração e refatoração via Antigravity CLI (`POST /api/code/agy`).
- **Obsidian Vault:** Leitura, busca, grafo de wikilinks, frontmatter, criação, edição, movimentação e notas diárias no vault configurado.
- **Desktop Hyprland & Visão de Tela:** Captura local via `grim`, inventário de janelas (`hyprctl`), foco/abertura de aplicativos, contexto ativo e **War Room** (VS Code + terminal + nota + pausa de notificações).
- **Guardian Gate & Arch Sentinel:** Classificação de risco e fila de aprovação para comandos de shell com política restrita, além de monitoramento read-only de disco, serviços, logs e atualizações do Arch Linux.

---

## 🔒 Destaques Técnicos

- **Grounding ao Vivo (< 40 ms):** O orquestrador injeta contexto real de saúde do sistema (Sentinel), pendências do Guardian, projetos locais, janelas ativas do Hyprland e memória FTS5 diretamente no prompt estruturado, permitindo respostas precisas em um único turno mesmo em modelos 3B/4B.
- **Streaming em Tempo Real (SSE):** O endpoint `POST /api/chat/stream` transmite eventos de progresso (`step`, `tool_start`, `tool_done`, `done`) ao vivo para a interface.
- **Integração Nativa com OpenJarvis:** Reutiliza as primitivas do runtime vendored em `vendor/OpenJarvis` (agentes, ferramentas, barramento de eventos, conectores Google OAuth e backends de voz) em vez de duplicar infraestrutura.
- **Segurança por Política:** Comandos de terminal são restritos aos diretórios permitidos e ações destrutivas ou externas (risco 2) exigem aprovação explícita no Guardian Gate.

---

## 📍 Como Executar

### Pré-requisitos

- [Python 3.12 ou 3.13](https://www.python.org/downloads/) (`>=3.12,<3.14`)
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) com modelo local instalado (ex.: `qwen2.5:3b` ou `qwen3:8b`)
- [Git](https://git-scm.com/)

### Clonando o Repositório

```bash
# Clone o projeto para a sua máquina local
git clone https://github.com/MarissaBorges/oros.git

# Entre no diretório do projeto
cd oros
```

### Instale as Dependências e Inicie

```bash
# Instale as dependências (incluindo ferramentas de desenvolvimento/testes)
uv sync --extra dev

# Opcional: suporte a automação de navegador via Playwright
uv sync --extra dev --extra browser

# Inicie o servidor OROS
./scripts/start-oros.sh
```

Abra `http://127.0.0.1:8000` (utilize `127.0.0.1` ou `localhost` para que o navegador libere permissões de microfone no Zen Browser, Firefox e Chrome).

### Executando os Testes

```bash
uv run pytest
```

---

## 🔌 Endpoints Principais

- **Chat e Status:** `GET /api/status`, `GET /api/capabilities/status`, `POST /api/chat`, `POST /api/chat/stream`
- **Voz:** `GET /api/voice/status`, `POST /api/voice/warmup`, `POST /api/voice/transcribe`, `POST /api/voice/speak`
- **Ingestão RAG:** `POST /api/ingest/docs`, `POST /api/ingest/repo`
- **Código (`agy`):** `POST /api/code/agy`, `GET /api/code/jobs`, `GET /api/code/jobs/<id>`
- **Desktop & Tela:** `POST /api/capabilities/screen/capture`, `GET /api/capabilities/screen/image`, `GET /api/capabilities/windows`, `POST /api/capabilities/open`
- **Obsidian Vault:** `GET /api/vault/notes`, `GET /api/vault/note?path=...`, `POST /api/vault/note`, `PUT /api/vault/note`, `DELETE /api/vault/note?path=...`
- **Terminal & Guardian:** `POST /api/terminal/run`, `GET /api/guardian`, `POST /api/guardian/<id>/approve`

---

## 📚 Documentação

- [Índice da Documentação (`docs/README.md`)](docs/README.md)
- [Arquitetura do OROS (`docs/ARCHITECTURE.md`)](docs/ARCHITECTURE.md)
- [Capacidades e Integrações Locais (`docs/CAPABILITIES.md`)](docs/CAPABILITIES.md)
- [Integração com Contas Google (`docs/GOOGLE_ACCOUNTS.md`)](docs/GOOGLE_ACCOUNTS.md)
- [Roadmap de Expansão (`docs/ROADMAP.md`)](docs/ROADMAP.md)
- [Especificação de Produto (`PRODUCT.md`)](PRODUCT.md) e [Diretrizes Visuais (`DESIGN.md`)](DESIGN.md)
- [Avisos de Terceiros (`THIRD_PARTY_NOTICES.md`)](THIRD_PARTY_NOTICES.md) e [Licença MIT](LICENSE)

---

## 🗺️ Roadmap Futuro

- [ ] **Curto Prazo:** Adaptador de visão multimodal para análise de tela em tempo real, fila de aprovação persistente com auditoria, registro de sessões de navegador e interface de setup OAuth do Google.
- [ ] **Operações Autônomas:** Briefing matinal diário, monitor contínuo de projetos/CI/Git, triagem autônoma de bugs com patch/testes e preparação automática de reuniões.
- [ ] **Longo Prazo:** Workspaces multi-agente, grafo de proveniência, roteamento ciente de energia/telemetria via OpenJarvis, integrações MCP e gateways móveis opcionais.

*(Detalhes completos em [docs/ROADMAP.md](docs/ROADMAP.md).)*

---

## 🤝 Colaboradores

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/MarissaBorges">
        <img src="https://github.com/MarissaBorges.png?size=100" width="100px;" alt="Foto de Marissa Borges"/><br>
        <sub>
          <b>Marissa Borges</b>
        </sub>
      </a>
    </td>
  </tr>
</table>

---

## 📫 Como Contribuir

Contribuições são muito bem-vindas!

1. Faça um **Fork** do projeto.
2. Crie uma nova branch para sua Feature (`git checkout -b feature/AmazingFeature`).
3. Faça o **Commit** de suas mudanças (`git commit -m 'Add some AmazingFeature'`).
4. Faça o **Push** da sua branch (`git push origin feature/AmazingFeature`).
5. Abra um **Pull Request**.
