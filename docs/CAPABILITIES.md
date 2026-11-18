# OROS capability setup

## Mandatory local integrations

## OROS orbital identity

The `frontend/oros-core.html` view embeds the Sinaptic-Orbital SVG supplied for
OROS. It is reused in the home banner and chat welcome state, with the four
cognitive states synchronized by `postMessage`: idle, listening, processing,
and speaking.

## Hands-free voice

OROS uses continuous browser speech recognition after the first explicit
microphone activation. Saying `OROS`, `Jarvis` or `Oros` enters listening mode.
The recognized Portuguese text is sent to the normal chat endpoint and replies
are spoken with the browser's local speech-synthesis voices.

The current backend prefers Ollama `qwen3:8b`. When that model is still
downloading, `qwen2.5:3b` is used automatically if installed. The configured
model can be changed with `OROS_OLLAMA_MODEL`.

### Active context

`GET /api/context/active` combines the focused Hyprland window, open-window
inventory, clipboard text, inferred project and stack-trace locations. Clipboard
access is read-only and is transmitted only through the local OROS API.

### Guardian Gate

`GET /api/guardian` lists pending actions and audit records.
`POST /api/guardian` creates a risk classification. Risk 0 is read-only, risk 1
is reversible, and risk 2 is external or destructive and requires approval.
`POST /api/guardian/<id>/approve` approves a pending request.

### War Room

`POST /api/war-room` focuses or launches the VS Code project window, starts a
terminal in the project directory, opens an optional Obsidian note and pauses
notifications.

### Arch Sentinel

`GET /api/sentinel/status` reports disk usage, failed services, recent warning
journal entries, package updates and orphaned packages. It does not modify the
system.

### Obsidian graph and garden

- `GET /api/vault/graph` builds a local wikilink graph.
- `GET /api/vault/garden` creates today's daily note and proposes backlinks.
- `GET /api/vault/frontmatter?path=...` separates YAML frontmatter from Markdown.

### Browser and research

`POST /api/browser/navigate` opens or reuses an HTTP(S) browser session.
`POST /api/research` searches DuckDuckGo, extracts pages and optionally writes
the report into `05 Recursos/OROS/Pesquisas` in the vault.

### Code tasks and Google

`POST /api/code/task` runs an inferred test command inside an allowlisted
project. It does not silently execute destructive commands.

`GET /api/google/status` reports the locally configured OpenJarvis Google
connectors. Account setup remains OAuth-based and credentials stay outside Git.

## Obsidian vault

The primary vault is `/home/borges/minha-mente`, configured in
`config/oros.json`. OROS can list, search, read, create, overwrite, append,
move, and trash notes.

Before broad vault synchronization:

```bash
cd /home/borges/dev/OpenJarvis
uv run jarvis connect obsidian --path /home/borges/minha-mente
```

The OROS endpoints provide direct vault operations without depending on
Obsidian's desktop plugin. Obsidian remains the source of truth for local
Markdown files.

## Screen vision

OROS uses `grim` to capture the Wayland/Hyprland screen and Hyprland's
`hyprctl` API to identify active windows. The capture endpoint returns a
temporary PNG and the active-window inventory. The image is intentionally
private to the local machine.

For multimodal understanding, install or select a vision-capable local model.
The model should receive the PNG through OpenJarvis's future vision adapter
and return OCR/layout/element descriptions. Do not send screen captures to a
cloud provider unless the user explicitly chooses that provider.

## Browser

OROS first looks for an existing browser window through Hyprland. It focuses
the matching window before opening or navigating. Playwright automation is
available through the vendored OpenJarvis browser tools for deterministic
page interaction. For existing Chrome sessions, prefer a Chrome remote-debug
port or an explicit browser profile.

## Terminal and projects

The shell API uses a minimal environment and allows execution only inside
`/home/borges/dev` and `/home/borges/minha-mente`. For project work:

- read and patch files through OpenJarvis file tools;
- inspect and modify Git through OpenJarvis Git tools;
- execute tests and builds through the policy-gated shell tool;
- use a sandbox or container for untrusted code.

## Web research

Use OpenJarvis `web_search`, `deep_research`, browser, and knowledge tools.
Every report should carry source URLs, retrieval dates, and confidence levels.
Contradictory evidence should be listed rather than silently merged.

## Account connectors

Google and account connectors are covered in
[GOOGLE_ACCOUNTS.md](GOOGLE_ACCOUNTS.md). Credentials must use OAuth and remain
outside Git. Calendar writes, email sends, and destructive account actions
require explicit approval.
