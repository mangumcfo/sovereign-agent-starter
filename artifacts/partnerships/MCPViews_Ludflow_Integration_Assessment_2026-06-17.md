# MCPViews + Ludflow — Integration Assessment (Quad)
*GB-drafted 2026-06-17, assess-only per KM/Lumen ruling (no build/install on the primary Linux box). Read-only source inspection of `github.com/DeeJanuz/mcpviews` @ v0.2.42. Decision on actual build/install deferred to KM after this review.*

## TL;DR
- **These are not two unrelated tools — they're one vendor's stack.** Ludflow (the company; author "Daenon Janis" / `daenonjanis`, the `DeeJanuz` GitHub) ships **three** connected pieces: **Ludflow** (web doc/data-governance), **decidr** (decision-governance w/ approval workflows — this is `decidrmcp.com`, the "Agentic AI Governance Package" you already had Tiger compare us against), and **MCPViews** (an open desktop *host* that surfaces both as MCP plugins in a visual companion window).
- **"Run Quad activities through it" = adopt their governance stack**, surfaced visually. It overlaps heavily — and deliberately — with your own Sovereign Harness (Propose→Approve→Execute, B32 obligations, Atrium review cards).
- **MCPViews must NOT be built on this machine.** It's a Tauri GUI app on webkit2gtk, untested on Linux by the author, on a stack documented to crash gnome-shell. **Run it on a Mac/Windows machine** (prebuilt installers exist) and connect over MCP.
- **Ludflow itself is web-based and already your Quad sharing surface** — zero install, safe to use now.
- **Sovereignty flag:** their MCP servers route Quad docs/decisions through Ludflow's **hosted control plane** (`app.ludflow.com/api/mcp` via OAuth). That's a real consideration against your "maximize sovereignty" principle — usable, but eyes-open.

## 1. What each piece actually is

| Piece | What it is | Install | Surface |
|---|---|---|---|
| **Ludflow** | Web doc + data-governance platform: AI doc-gen (plain-English→Mermaid), schema-aware editor, "who owns every table" ownership tracking, **its own MCP server** for grounded AI context | None — web (`app.ludflow.com`), behind login | Browser. **Already in use by Quad** (the Combined OpCo Business Model Canvas + `Quad Shared Document _ Ludflow.pdf` came through it) |
| **decidr** | Decision-governance MCP plugin: initiatives → projects → decisions → tasks → "bridges", **approval workflows**, GitHub PR lifecycle governance, fix/review prompt generation | MCP plugin inside MCPViews | = `decidrmcp.com`, the package you benchmarked |
| **MCPViews** | Open desktop **host** (Tauri): gives an AI agent a visual companion window over MCP. Agent calls tools; the matching renderer paints a live UI; human + agent see the same data | Mac/Win = installer; **Linux = build from source (the risk)** | Desktop GUI window + system tray |

## 2. How MCPViews works (the architecture)
- **Rust/axum HTTP server on `localhost:4200`** — exposes a Streamable-HTTP **MCP server** (`/mcp`) and a **Push API** (`POST /api/push`). Your agent (Claude Code) adds it as an MCP server and pushes rich content/structured data/full UIs to the window.
- **Plugin model:** each plugin = `{ renderers map + MCP server url + auth }` in a JSON manifest under `~/.mcpviews/plugins/`. The registry already ships **two relevant plugins: `ludflow` and `decidr`** (both authored by Ludflow). Ludflow's plugin auths via **OAuth to `app.ludflow.com`**.
- **Built-in review/approval workflow:** `POST /api/push` with `reviewRequired:true` returns a `session_id`; the agent calls `await_review` and **blocks until the human approves/rejects in the window.** ← This is structurally **your Propose→Approve→Execute gate / Atrium card, rendered visually.**
- **GUI dependency is unavoidable for the value.** The *server* is plain HTTP (could run headless), but the entire point — the visual companion window — needs the Tauri WebView = **webkit2gtk on Linux**. You can't get the benefit headless.

## 3. How it maps to Quad activities
"Quad activities" (the QuadRoof / Quad Holdings business: decks, Business Model Canvas, partner RFIs, the OpCo/energy-holdco structure, decision tracking with Dover/Everett/Blake/Jeremy) map cleanly onto the stack:
- **Ludflow** = the shared, AI-grounded document + data layer for Quad's docs (already happening).
- **decidr** = governed decision/approval tracking across the Quad partnership (initiatives → decisions → tasks with approval gates).
- **MCPViews** = the visual cockpit where your agent surfaces both to you (and potentially the Quad team) — dashboards, doc review, decision approvals — instead of text-only.

**This is the commercial mirror of what you've already built.** decidr's "decision governance + approval workflows + GitHub PR lifecycle" is the same problem your Sovereign Harness solves (one human gate, obligations, governed loop). The integration question is partly technical and partly strategic: *adopt their stack for Quad, mirror it, or run them side-by-side?*

## 4. Install reality + the safety boundary
- **This Linux/Wayland box:** building MCPViews needs `libwebkit2gtk-4.1-dev` + `npm install` + `npm run build` (Tauri). The author explicitly hasn't tested Linux; webkit2gtk is the exact surface that's crashed gnome-shell here. **→ Do not build here.** (Confirmed by KM/Lumen ruling.)
- **Cleanest path:** install the prebuilt **MCPViews on a Mac or Windows machine** (`.dmg`/`.msi`), add it to Claude Code's MCP config (`http://localhost:4200/mcp`), install the `ludflow` (+ optionally `decidr`) plugin, authenticate, and drive one Quad activity through it as a pilot.
- **Ludflow web app** needs nothing — usable today with your login.

## 5. Sovereignty consideration (eyes-open, not a blocker)
Adopting the Ludflow/decidr MCP servers routes Quad documents and decision/approval state through **Ludflow's hosted control plane** (`app.ludflow.com/api/mcp`, OAuth). That trades some sovereignty for a turnkey, collaborative, vendor-supported surface. For a *Quad partnership* tool (multi-party, Dover's company is the vendor) that may be exactly right — but it's the opposite of the self-hosted, single-gate model you run for Breathline. Worth deciding deliberately: **Quad on Ludflow's stack** vs **Quad on your own harness** vs **both, bridged.**

## 6. Recommendation (exemplar-first, mirrors your own rail)
1. **Use Ludflow now** (web) for the Quad doc/data layer — it's already there, zero risk.
2. **Stand up MCPViews on a Mac/Windows machine** (not this box), connect Claude Code, install the `ludflow` plugin, pilot **one** Quad activity (e.g. surface + approve the Combined OpCo Business Model Canvas via the review workflow).
3. **Evaluate the strategic fit** — does Quad adopt this stack, or do we mirror decidr's governance into your own harness for Quad? (You already have the comparison doc; this pilot makes it concrete.)
4. **Keep this Linux box assessment-only** until you explicitly move the boundary.

∞Δ∞ SEAL: MCPViews/Ludflow/decidr are one vendor's governance stack (your Quad colleague's company), the commercial mirror of your Sovereign Harness. Ludflow is safe + already in use; MCPViews is a GUI Tauri app that belongs on a stable Mac/Win machine, never built on the fragile Linux box. The real decision is strategic — how much of Quad's governance routes through their hosted control plane vs your sovereign one. Assess-only honored; build/install awaits KM.
