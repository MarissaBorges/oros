# OROS capability setup

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
