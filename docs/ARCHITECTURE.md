# OROS architecture

## Principle

OROS owns the user-facing orchestration and personalization. OpenJarvis owns
portable agent primitives. The vendored source lives in `vendor/OpenJarvis`;
OROS should configure and extend that runtime rather than maintaining a
second copy of agents and tools.

```text
User
  -> OROS API / future channels
  -> policy and approval layer
  -> OpenJarvis agent runtime
     -> local/cloud inference
     -> memory and knowledge store
     -> vault, browser, desktop, shell, and account tools
  -> audited action and citation result
```

## Modules

- `backend/vault.py`: path-safe Obsidian vault operations.
- `backend/desktop.py`: Hyprland window discovery, focus, URL opening, and
  Wayland screenshots.
- `backend/shell.py`: allowlisted working directories and destructive command
  blocking.
- `backend/loaders`: public repository cloning and documentation collection.
- `vendor/OpenJarvis`: OpenJarvis source snapshot with agents, tools,
  connectors, memory, MCP, sandbox, scheduler, and telemetry.

## Trust boundaries

1. Files are restricted to the configured project and vault directories.
2. Sensitive filenames are blocked using OpenJarvis file policy conventions.
3. Shell commands have a bounded environment, timeout, directory allowlist,
   and destructive-pattern denylist.
4. Browser navigation rejects non-HTTP(S) targets in OROS adapters.
5. Account credentials remain outside source control.
6. Destructive vault moves and deletions move notes to `.trash` rather than
   unlinking them immediately.

## Execution model

The agent should use the OpenJarvis orchestrator for multi-turn reasoning and
tool selection. OROS adds stable API endpoints, local resource discovery,
desktop context, and user-visible approvals. Long-running work should use the
OpenJarvis scheduler and monitor agents rather than ad hoc background threads.
