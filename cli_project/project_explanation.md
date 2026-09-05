# cli_project — Function-by-Function Explanation

This project is a terminal chat client that talks to Claude (Anthropic API) and
extends it with tools/prompts/resources served over the **Model Context
Protocol (MCP)**. A local MCP server (`mcp_server.py`) exposes a small
in-memory "document store"; the CLI can also connect to additional MCP
servers passed as command-line arguments.

Note: `mcp_client.py` and `mcp_server.py` contain unfinished `TODO` stubs
(they currently return empty lists / `None`). This is called out inline
below wherever it applies.

---

## `main.py`

Entry point that wires everything together and starts the interactive CLI.

### `main()` (async)
1. Reads `CLAUDE_MODEL` and `ANTHROPIC_API_KEY` from the environment (loaded
   via `dotenv` at import time) and constructs a `Claude` service wrapper.
2. Reads any extra MCP server scripts passed as CLI arguments
   (`sys.argv[1:]`).
3. Decides whether to launch MCP servers with `uv run ...` or plain
   `python ...`, based on the `USE_UV` env var.
4. Uses an `AsyncExitStack` to open (and guarantee cleanup of):
   - a `doc_client` `MCPClient` connected to the built-in `mcp_server.py`
     (the document server),
   - one additional `MCPClient` per extra server script supplied on the
     command line (always launched via `uv run <script>`).
5. Builds a `CliChat` (the conversation/agent object) from those clients and
   the `Claude` service.
6. Builds a `CliApp` (the interactive terminal UI) around the `CliChat`,
   calls `cli.initialize()` to preload prompts/resources, then `cli.run()`
   to start the interactive loop.

### Module-level `if __name__ == "__main__":` block
On Windows, swaps in `WindowsProactorEventLoopPolicy` (required for subprocess
support with `asyncio`, which `MCPClient` needs for the stdio transport), then
runs `main()` with `asyncio.run`.

---

## `mcp_client.py` — `MCPClient`

A thin async wrapper around the MCP Python SDK's `ClientSession`, responsible
for launching an MCP server as a subprocess (via stdio) and talking to it.

- **`__init__(self, command, args, env=None)`** — stores the subprocess
  command/args/env needed to launch the server and prepares an
  `AsyncExitStack` to manage the connection's lifetime.
- **`connect(self)`** (async) — builds `StdioServerParameters`, opens the
  stdio transport (`stdio_client`), opens a `ClientSession` on top of it, and
  calls `session.initialize()` to perform the MCP handshake.
- **`session(self)`** — returns the active `ClientSession`, raising
  `ConnectionError` if `connect()` hasn't been called yet.
- **`list_tools(self)`** (async) — **TODO/stub**: intended to return the
  tools the connected MCP server exposes; currently always returns `[]`.
- **`call_tool(self, tool_name, tool_input)`** (async) — **TODO/stub**:
  intended to invoke a tool on the server and return its `CallToolResult`;
  currently always returns `None`.
- **`list_prompts(self)`** (async) — **TODO/stub**: intended to return the
  server's declared prompts; currently always returns `[]`.
- **`get_prompt(self, prompt_name, args)`** (async) — **TODO/stub**:
  intended to fetch/render a specific prompt with arguments; currently
  always returns `[]`.
- **`read_resource(self, uri)`** (async) — **TODO/stub**: intended to fetch
  and parse a resource by URI (e.g. `docs://documents`); currently always
  returns `[]`.
- **`cleanup(self)`** (async) — closes the `AsyncExitStack`, tearing down the
  session and subprocess, and clears `_session`.
- **`__aenter__` / `__aexit__`** — allow `MCPClient` to be used as an async
  context manager (`async with MCPClient(...) as client:`), calling
  `connect()` on enter and `cleanup()` on exit. This is how `main.py` uses it
  via `stack.enter_async_context(...)`.
- **`main()`** (async, bottom of file) — a small manual smoke test: connects
  to `mcp_server.py` via `uv run` and immediately exits. Only runs when the
  file is executed directly (`python mcp_client.py`), not on import.

---

## `mcp_server.py`

A `FastMCP` server named `"DocumentMCP"` holding an in-memory dict of fake
documents (`docs`, keyed by filename with placeholder text content).

Currently this file has **no implemented tools/resources/prompts** — only
`TODO` comments describing what should be added:
- a tool to read a document,
- a tool to edit a document,
- a resource returning all document IDs,
- a resource returning one document's contents,
- a prompt to rewrite a document as markdown,
- a prompt to summarize a document.

The only executable logic is the bottom guard, which starts the server over
stdio transport when run directly:
```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```
Because these are unimplemented, `CliChat.list_docs_ids`, `get_doc_content`,
`get_prompt`, etc. (see below) won't return real data until both this file
and the corresponding `MCPClient` methods are filled in.

---

## `core/claude.py` — `Claude`

Wraps the raw Anthropic SDK client with the message-formatting conventions
this app uses.

- **`__init__(self, model)`** — creates an `anthropic.Anthropic()` client
  (reads `ANTHROPIC_API_KEY` from env automatically) and stores the model
  name to use for all calls.
- **`add_user_message(self, messages, message)`** — appends a `{"role":
  "user", ...}` entry to `messages`. Accepts either a raw string/list of
  content blocks, or a full Anthropic `Message` object (in which case its
  `.content` is reused) — this lets you feed a tool-result list or a plain
  string interchangeably.
- **`add_assistant_message(self, messages, message)`** — same idea as above
  but appends with `"role": "assistant"`; used to record Claude's own
  responses back into the running conversation.
- **`text_from_message(self, message)`** — extracts and joins all `text`
  content blocks from a `Message`, ignoring any `tool_use`/`thinking`
  blocks. Used to print/return Claude's plain-text reply.
- **`chat(self, messages, system=None, temperature=1.0, stop_sequences=[], tools=None, thinking=False, thinking_budget=1024)`**
  — the actual API call. Builds a `params` dict (model, `max_tokens=8000`,
  messages, temperature, stop_sequences), conditionally adds `thinking`
  (extended-thinking mode with a token budget), `tools`, and `system` prompt
  if provided, then calls `self.client.messages.create(**params)` and
  returns the resulting `Message`.

---

## `core/chat.py` — `Chat`

The base "agent loop" — no document/prompt-specific behavior, just the
generic Claude ⇄ tools conversation loop.

- **`__init__(self, claude_service, clients)`** — stores the `Claude`
  wrapper and the dict of `MCPClient`s, and initializes an empty
  `messages` conversation history.
- **`_process_query(self, query)`** (async) — default implementation:
  simply appends the raw user query as a `"user"` message. Subclasses (like
  `CliChat`) override this to add context/resource injection.
- **`run(self, query)`** (async) — the core agentic loop:
  1. Calls `_process_query(query)` to record the user's turn.
  2. Loops: calls `claude_service.chat(...)` with the full message history
     and the combined tool list from every client
     (`ToolManager.get_all_tools`).
  3. Records Claude's reply via `add_assistant_message`.
  4. If Claude's `stop_reason == "tool_use"`, prints any text Claude produced
     alongside the tool call, executes the requested tool(s) via
     `ToolManager.execute_tool_requests`, feeds the results back in as a
     user message, and loops again (so Claude can see the tool output and
     continue).
  5. Otherwise (Claude gave a final answer), captures the text response and
     breaks out of the loop.
  6. Returns the final text response.

---

## `core/cli_chat.py`

### `CliChat(Chat)`
Subclass of `Chat` that adds document-awareness and slash-command support
on top of the generic agent loop.

- **`__init__(self, doc_client, clients, claude_service)`** — calls
  `Chat.__init__`, then keeps a dedicated reference to the `doc_client`
  (the MCP client for the document server) for convenience methods below.
- **`list_prompts(self)`** (async) — delegates to
  `doc_client.list_prompts()`; used by `CliApp` to populate tab-completion
  for `/command`s.
- **`list_docs_ids(self)`** (async) — reads the `docs://documents` resource
  from the doc server to get all known document IDs (for `@mention`
  autocompletion).
- **`get_doc_content(self, doc_id)`** (async) — reads the
  `docs://documents/{doc_id}` resource to fetch one document's text.
- **`get_prompt(self, command, doc_id)`** (async) — fetches a named prompt
  from the doc server, passing `doc_id` as its argument.
- **`_extract_resources(self, query)`** (async) — scans the user's query for
  `@word` mentions, checks which mentioned words are real document IDs
  (via `list_docs_ids`), fetches their content, and returns them formatted
  as `<document id="...">...</document>` XML-ish blocks to inject as
  context.
- **`_process_command(self, query)`** (async) — if the query starts with
  `/`, treats the first word as a prompt name and the second word as a
  `doc_id`, fetches that prompt from the server (`doc_client.get_prompt`),
  converts its messages into Anthropic message format, and appends them to
  the conversation. Returns `True` if a command was handled, `False`
  otherwise (so `_process_query` knows whether to fall through to normal
  chat handling).
- **`_process_query(self, query)`** (async, overrides `Chat._process_query`)
  — first tries `_process_command`; if that handled a `/command`, it stops
  there. Otherwise it calls `_extract_resources` to gather any `@mentioned`
  document content, wraps the user's query plus that context in an
  instruction template (telling Claude not to mention the injected context
  explicitly, and how to interpret `@name` mentions), and appends that as
  the user message.

### Module-level helper functions
- **`convert_prompt_message_to_message_param(prompt_message)`** — converts
  one MCP `PromptMessage` (with `role` + `content`, where content can be a
  dict, an object, or a list of blocks) into Anthropic's `MessageParam`
  shape. Normalizes the role to `"user"`/`"assistant"`, and pulls out
  `"text"`-typed content whether it's a single block or a list of blocks;
  falls back to an empty string content if nothing matches.
- **`convert_prompt_messages_to_message_params(prompt_messages)`** — maps
  the above conversion function over a whole list of `PromptMessage`s.

---

## `core/tools.py` — `ToolManager`

Static/class-method helper that bridges Claude's tool-calling protocol with
one or more MCP clients, since a given Claude turn might need to call a tool
hosted on any of several connected servers.

- **`get_all_tools(cls, clients)`** (async classmethod) — asks every
  `MCPClient` for its `list_tools()` and flattens the results into the
  `tools` schema Claude's API expects (`name`, `description`,
  `input_schema`). This combined list is passed to `Claude.chat(tools=...)`
  each turn.
- **`_find_client_with_tool(cls, clients, tool_name)`** (async classmethod)
  — searches through the given clients' tool lists to find which one
  actually hosts a tool with the requested name; returns `None` if no
  client has it.
- **`_build_tool_result_part(cls, tool_use_id, text, status)`** (classmethod)
  — builds the `ToolResultBlockParam` dict Anthropic expects for reporting a
  tool's result back to Claude (`tool_use_id`, `content`, `is_error` flag
  derived from `status`).
- **`execute_tool_requests(cls, clients, message)`** (async classmethod) —
  the main entry point used by `Chat.run`:
  1. Pulls every `tool_use` content block out of Claude's message.
  2. For each requested tool call, finds the right client
     (`_find_client_with_tool`); if none is found, records an error result
     ("Could not find that tool").
  3. Otherwise calls `client.call_tool(tool_name, tool_input)`, extracts any
     `TextContent` items from the result, JSON-encodes them as the tool
     result text, and marks it success/error based on
     `tool_output.isError`.
  4. Catches exceptions from the tool call itself, logs them, and returns an
     error result block instead of raising (so one bad tool call doesn't
     crash the whole chat loop).
  5. Returns the full list of result blocks to be sent back to Claude as a
     user turn.

---

## `core/cli.py`

The interactive terminal front-end, built on `prompt_toolkit`. Provides
slash-command (`/prompt`) and at-mention (`@document`) autocompletion plus
the main input loop.

### `CommandAutoSuggest(AutoSuggest)`
Provides *inline* ghost-text suggestions (not the dropdown menu) for slash
commands.
- **`__init__(self, prompts)`** — stores the list of available `Prompt`
  objects and an index by name.
- **`get_suggestion(self, buffer, document)`** — if the current line is a
  single `/command` (no arguments yet) and it matches a known prompt name,
  suggests appending a space plus the prompt's first argument name (e.g.
  typing `/summarize` suggests `/summarize doc_id`). Returns `None`
  otherwise.

### `UnifiedCompleter(Completer)`
Drives the dropdown completion menu for both `/commands` and `@resource`
mentions.
- **`__init__(self)`** — starts with empty prompt/resource lists.
- **`update_prompts(self, prompts)`** — replaces the known prompts (and
  name index) — called whenever prompts are (re)loaded from the server.
- **`update_resources(self, resources)`** — replaces the known
  document/resource ID list.
- **`get_completions(self, document, complete_event)`** — the main
  completion logic, branching on context:
  - If there's an `@` before the cursor, completes the text after the last
    `@` against known resource IDs (case-insensitive prefix match).
  - If the line starts with `/` and only the command itself is typed (no
    trailing space), completes against known prompt names, showing each
    prompt's description.
  - If exactly one `/command` is typed followed by a trailing space,
    suggests all resource IDs as the argument (assumes the argument is a
    doc ID).
  - If two or more words are typed after `/`, treats the last word as a
    partial doc ID and completes it against resources that have an `"id"`
    field.

### `CliApp`
The top-level app object that owns the `PromptSession` and the run loop.
- **`__init__(self, agent)`** — stores the `CliChat` agent; sets up the
  `UnifiedCompleter` and an initially-empty `CommandAutoSuggest`; registers
  custom key bindings:
  - Typing `/` at the start of an empty line auto-opens the completion menu.
  - Typing `@` always auto-opens the completion menu (for resource mentions).
  - Typing a space after a single `/command` opens the menu (to prompt for
    an argument); typing a space after `/command arg` re-opens it if the
    argument looks like it refers to a doc/file/id (heuristic string check).
  Then builds the `PromptSession` with history, key bindings, styling, and
  the completer/auto-suggester wired in.
- **`initialize(self)`** (async) — calls `refresh_resources()` and
  `refresh_prompts()` once at startup so completion works immediately.
- **`refresh_resources(self)`** (async) — fetches document IDs via
  `agent.list_docs_ids()` and pushes them into the completer; logs (doesn't
  raise) on failure.
- **`refresh_prompts(self)`** (async) — fetches prompts via
  `agent.list_prompts()`, pushes them into the completer, and rebuilds the
  `CommandAutoSuggest` (and rewires it into the active session) so inline
  suggestions reflect the latest prompts; logs on failure.
- **`run(self)`** (async) — the main REPL loop: prompts the user for input
  with `session.prompt_async("> ")`, skips blank input, otherwise passes the
  input to `agent.run(user_input)` (the `CliChat`/`Chat` agent loop
  described above) and prints the response. Exits cleanly on
  `KeyboardInterrupt` (Ctrl+C).

---

## Overall control flow

```
main.py:main()
  → builds Claude, launches MCP servers as subprocesses via MCPClient
  → builds CliChat (agent) and CliApp (terminal UI)
  → CliApp.initialize()   — preloads prompts & doc IDs for autocomplete
  → CliApp.run()          — REPL loop
       → user types a line
       → CliChat.run(query)                [Chat.run]
            → CliChat._process_query(query)  — handles "/cmd doc_id" or
              injects "@doc" content as context
            → loop:
                 Claude.chat(messages, tools=ToolManager.get_all_tools(...))
                 if tool_use: ToolManager.execute_tool_requests(...) → feed
                   results back in, loop again
                 else: return final text
       → print response
```

**Caveat:** `mcp_client.py`'s `list_tools`, `call_tool`, `list_prompts`,
`get_prompt`, and `read_resource` are currently stubs returning empty
values, and `mcp_server.py` has no tools/resources/prompts implemented yet
(only `TODO`s). Until those are filled in, the app will run but tool calls,
`@document` context injection, and `/prompt` commands won't have any real
data to work with.
