# Connecting Claude to Roblox Studio (MCP)

Roblox Studio has a built-in MCP server, and Roblox publishes an official plugin that wires Claude Code to it.
It runs **on your own computer**, so it works from Claude Code installed locally (macOS or Windows), not from
claude.ai on the web or a cloud session. Once connected, Claude can read your open place, run Luau, playtest and
read the Output window, which is what's needed to debug the things I can't see from the repo.

## Setup (about 3 minutes)

1. Install **Claude Code** on your computer and open it in this project folder (`cd SBR-Game && claude`).
2. In Claude Code run `/plugin`, search for **Roblox Studio**, and install it
   ([Roblox/roblox-studio-agent-plugin](https://github.com/Roblox/roblox-studio-agent-plugin)).
3. In Studio, open **Assistant**, then **... > Settings > MCP Servers** (older Studio: *Manage MCP Servers*),
   and turn on **Enable Studio as MCP server**. Keep your place SBR open.
4. In Claude Code run `/mcp`. You should see `plugin:roblox-studio:windows` / `...:macos`. Only the one for
   your OS connects, so the other showing as failed is normal.
5. Test it: ask "list my open Roblox Studio windows".

Notes
- The older standalone server ([Roblox/studio-rust-mcp-server](https://github.com/Roblox/studio-rust-mcp-server))
  is archived/legacy. Use the built-in one above.
- Claude can edit your place directly, and not every change can be undone. **Save/publish a version first.**
- What Claude reads (scripts, Output, screenshots) is sent to Anthropic as part of the chat.

## Working with Rojo at the same time

The scripts in `src/` are owned by Rojo: `rojo serve` overwrites them in Studio. So:
- Make code changes in the files in this repo (Claude Code does this normally), not by editing scripts through MCP.
- Use MCP for what Rojo can't do: reading the Output window and errors, inspecting the Explorer, running the
  game, taking screenshots, tweaking properties.
- Keep `rojo serve` running and connected while you test.
