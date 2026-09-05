# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An MCP (Model Context Protocol) server, built with `mcp[cli]` (FastMCP), that exposes document-conversion and utility tools to AI assistants. Package name is `app`; the MCP server itself is named `"docs"` (see [main.py](main.py)).

## Commands

```bash
# Create and activate the virtual env
uv venv
source .venv/bin/activate

# Install the package in editable/dev mode
uv pip install -e .

# Start the MCP server (long-running; talks over stdio)
uv run main.py

# Run the full test suite
uv run pytest

# Run a single test file / test
uv run pytest tests/test_document.py
uv run pytest tests/test_document.py::TestBinaryDocumentToMarkdown::test_binary_document_to_markdown_with_pdf
```

There is no separate lint/build step configured in [pyproject.toml](pyproject.toml).

## Architecture

- [main.py](main.py) is the MCP server entry point. It creates a `FastMCP("docs")` instance and registers tool functions onto it with `mcp.tool()(fn)`. Running the file (`uv run main.py`) starts the server via `mcp.run()`.
- `tools/` holds plain Python functions that implement tool logic, independent of MCP registration:
  - [tools/math.py](tools/math.py) — `add(a, b)`, currently the only tool wired up in `main.py`.
  - [tools/document.py](tools/document.py) — `binary_document_to_markdown(binary_data, file_type)`, converts binary document bytes (PDF, DOCX, etc.) to markdown text using `markitdown`. **Not yet registered in `main.py`** — it exists and is tested but isn't exposed as an MCP tool yet.
- Tool logic is deliberately decoupled from MCP: a function in `tools/` is a normal, independently testable Python function. Wiring it into the server is a one-line addition in `main.py` (`mcp.tool()(function_name)`).
- `tests/` mirrors `tools/` (e.g., `tests/test_document.py` tests `tools/document.py`) and uses fixture files under `tests/fixtures/` (sample `.docx`/`.pdf`) for real-content conversion tests rather than mocks.

## Conventions

- Always apply appropriate type hints to function arguments (and return types), including in tool implementations under `tools/` — see the pydantic `Field`-typed params in `tools/math.py` and the plain type hints in `tools/document.py` as the expected style.

## Defining new MCP tools

This is the pattern the codebase follows for adding a tool, per [README.md](README.md):

1. **Write the function in `tools/`** as a standalone Python function (see `tools/math.py` / `tools/document.py` for examples). Keep it free of MCP-specific code so it stays independently testable.
2. **Type and document parameters with pydantic `Field`**, not plain defaults — this is what populates the tool's schema for the calling model:
   ```python
   from pydantic import Field

   def my_tool(
       param1: str = Field(description="Detailed description of this parameter"),
       param2: int = Field(description="Explain what this parameter does"),
   ) -> ReturnType:
       """Comprehensive docstring here"""
       # Implementation
   ```
3. **Write the docstring as the tool description** the model sees. It should:
   - Begin with a one-line summary
   - Provide a detailed explanation of functionality
   - Explain when to use (and not use) the tool
   - Include usage examples with expected input/output (see `add`'s docstring in `tools/math.py` for the expected shape — one-liner, "When to use" section, `>>> ` doctest-style examples)
4. **Register the function on the server** in [main.py](main.py):
   ```python
   mcp.tool()(my_function)
   ```
5. **Add tests** under `tests/`, mirroring the module layout in `tools/`. For tools that operate on real files (documents, binaries), prefer real fixture files under `tests/fixtures/` over mocking, matching the existing `test_document.py` approach.
