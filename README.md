# OROS

OROS is a Portuguese-first technical assistant with a RAG interface for local
documentation and public GitHub repositories.

## What it contains

- A Django backend with chat, ingestion, status, and static asset endpoints.
- A RAG pipeline that indexes local text and source files.
- Hugging Face Inference API integration.
- A JARVIS-style web interface.
- Repository and documentation ingestion queues.

## Run locally

```bash
python -m pip install django requests
export HF_TOKEN="your-hugging-face-token"
python backend/manage.py runserver
```

Open `http://127.0.0.1:8000`.

## API

- `GET /api/status`
- `POST /api/chat`
- `POST /api/ingest/docs`
- `POST /api/ingest/repo`

The chat model is configured with `HF_MODEL` and defaults to
`meta-llama/Llama-3.2-3B-Instruct`.

## OpenJarvis integration

[OpenJarvis](https://github.com/open-jarvis/OpenJarvis) can serve as the agent
runtime beneath OROS. The recommended integration is to replace the
single-call Hugging Face chat path with OpenJarvis agents while keeping OROS
as the visual and indexing layer.

OpenJarvis brings:

- Local-first models through Ollama and other inference backends.
- Tool-calling orchestrator and ReAct agents.
- Scheduled briefs and continuous monitoring.
- Skills, memory, MCP tools, connectors, and sandbox execution.
- REST and GUI interfaces, plus energy, cost, latency, and accuracy telemetry.

A practical architecture is:

```text
OROS web UI
  -> OROS Django API
  -> retrieval and ingestion
  -> OpenJarvis agent runtime
  -> local models/tools/connectors
```

The first integration milestone should expose an `/api/agent` bridge and
preserve OROS source citations. Next milestones can add:

1. Deep-research agents for indexed repositories and documentation.
2. Code-assistant execution with approval and sandbox policies.
3. Scheduled repository change summaries.
4. Voice input and text-to-speech.
5. Email, calendar, chat, and browser connectors.
6. Hardware-aware model selection using OpenJarvis telemetry.

## License

MIT License. See [LICENSE](LICENSE).

## OROS autonomous capabilities

The implementation uses the vendored OpenJarvis runtime at
[`vendor/OpenJarvis`](vendor/OpenJarvis). It is intended to share OpenJarvis
primitives instead of recreating agents, tools, connectors, memory, routing,
scheduling, or sandbox logic.

Current capability endpoints:

- `GET /api/capabilities/status`
- `POST /api/capabilities/screen/capture`
- `GET /api/capabilities/screen/image`
- `GET /api/capabilities/windows`
- `POST /api/capabilities/open`
- `GET /api/vault/notes`
- `GET /api/vault/note?path=...`
- `POST /api/vault/note`
- `PUT /api/vault/note`
- `DELETE /api/vault/note?path=...`
- `POST /api/terminal/run`

Read [the architecture](docs/ARCHITECTURE.md), [capability setup](docs/CAPABILITIES.md),
[Google accounts](docs/GOOGLE_ACCOUNTS.md), and [the expansion roadmap](docs/ROADMAP.md).
