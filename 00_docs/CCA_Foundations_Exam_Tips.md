# CCA Foundations — Exam Tips & Decision Patterns

Consolidated from analysis of `Claude_Certified_Architect_–_Foundations_Certification_Exam_Guide (1).pdf` (v0.1, Feb 10 2025).

---

## 1. Exam Mechanics

- **Format:** multiple choice — 1 correct + 3 distractors per question.
- **Scoring:** scaled 100–1000. **Pass = 720**.
- **No penalty for guessing** — never leave blanks.
- **4 of 6 fixed scenarios** appear on exam day, randomly drawn:
  1. Customer Support Resolution Agent
  2. Code Generation with Claude Code
  3. Multi-Agent Research System
  4. Developer Productivity with Claude
  5. Claude Code for Continuous Integration
  6. Structured Data Extraction

### Domain weightings

| Domain | Weight | Focus |
|---|---|---|
| 1. Agentic Architecture & Orchestration | **27%** | Loops, coordinator-subagent, hooks, Task tool |
| 2. Tool Design & MCP Integration | 18% | Tool descriptions, MCP scope, errors, tool_choice |
| 3. Claude Code Configuration & Workflows | 20% | CLAUDE.md hierarchy, rules, skills, commands |
| 4. Prompt Engineering & Structured Output | 20% | Few-shot, JSON schema, validation-retry, batch |
| 5. Context Management & Reliability | 15% | Token mgmt, error propagation, provenance |

**Where to spend extra prep time:** D1 (largest), then D3+D4 (combined 40%).

---

## 2. Recurring Correct-Answer Rules

These patterns repeat across many sample questions. When in doubt, default to whichever option matches one of these:

1. **Programmatic enforcement beats prompt instructions for hard rules.** Hooks, prerequisite gates, `tool_choice` forced selection — for any rule with financial / compliance / correctness consequences. *(Q1)*
2. **Fix root cause at the smallest level first.** Misrouted tools → fix descriptions before adding routers/classifiers. *(Q2)* Bad escalation → explicit criteria + few-shot before deploying ML models. *(Q3)*
3. **Coordinator decomposition is where multi-agent failures originate.** When subagents each "succeed" but final output misses coverage → blame the coordinator's task decomposition. *(Q7)*
4. **Errors propagate as structured context, never generic statuses.** `errorCategory` + `isRetryable` + partial results + attempted query. Generic "search unavailable" is an anti-pattern. *(Q8)*
5. **Match API to latency requirement.** Synchronous API for blocking workflows; Message Batches API for overnight (50% cheaper but 24h SLA-less). *(Q11)*
6. **Plan mode for architectural / multi-file / multiple-valid-approaches; direct execution for single-file clear-scope.** Don't "start direct and switch later" if complexity is already stated. *(Q5)*
7. **Path-scoped rules (`.claude/rules/` with `paths:`) beat directory-bound CLAUDE.md** when conventions span multiple directories (e.g., test files everywhere). *(Q6)*
8. **`.claude/...` (project) is version-controlled and shared. `~/.claude/...` (user) is personal.** "Every developer when they clone" → project-scope.
9. **Multi-pass review beats single-pass on large PRs.** Per-file pass + cross-file integration pass. Independent review instance > self-review. *(Q12)*
10. **`tool_choice` vocabulary:**
    - `"auto"` — model may text instead of calling a tool.
    - `"any"` — must call SOME tool (use to guarantee structured output).
    - `{"type":"tool","name":"..."}` — must call THAT specific tool (forced).

---

## 3. Anti-Patterns (Always Wrong)

If a distractor matches one of these, it's almost certainly wrong:

- Parsing natural-language signals to terminate an agent loop.
- Setting arbitrary iteration caps as the **primary** stopping mechanism.
- Checking assistant-text content as a completion indicator.
- Self-reported confidence scores from LLMs as a routing input.
- Sentiment-based escalation ("if user is frustrated, escalate").
- Generic error messages ("Operation failed", "search unavailable").
- Returning empty results as success when an error occurred.
- Suppressing errors silently / catching subagent timeouts and marking success.
- Terminating an entire workflow on a single subagent failure.
- Giving an agent 18 tools when 4–5 will do.
- Cross-specialization tool access (synthesis agent doing web searches).
- Assuming subagents inherit coordinator context (they don't).
- Sequentializing parallel-safe `Task` calls across multiple turns.

---

## 4. Domain 1 Deep Dive — Agentic Architecture & Orchestration (27%)

### Task 1.1 — Agentic loops

**The loop:** send request → inspect `stop_reason` → if `"tool_use"`, execute tools and append results to history → repeat. Terminate ONLY on `"end_turn"`.

```python
while True:
    response = client.messages.create(model=..., tools=tools, messages=messages)
    messages.append({"role": "assistant", "content": response.content})
    if response.stop_reason == "end_turn":
        break
    if response.stop_reason == "tool_use":
        tool_results = [
            {"type": "tool_result", "tool_use_id": b.id, "content": execute_tool(b.name, b.input)}
            for b in response.content if b.type == "tool_use"
        ]
        messages.append({"role": "user", "content": tool_results})
```

### Task 1.2 — Coordinator-subagent

- **Hub-and-spoke**, not mesh. All inter-agent comms via coordinator.
- **Coordinator owns:** decomposition, delegation, aggregation, iterative refinement, error routing.
- **Subagents:** isolated context (do NOT inherit), specialized scope, bounded tools.
- **Most tested failure:** narrow decomposition. Subagents succeed within their assignment but final output misses coverage.

### Task 1.3 — Subagent invocation

- `allowedTools` **must include `"Task"`** for coordinator to spawn subagents.
- Subagents start with **empty conversation** — pass context explicitly in the prompt.
- **Parallel spawning = multiple `Task` calls in ONE coordinator response**, never across separate turns.
- Pass structured data with provenance: `{ claim, evidence, source_url, source_doc, page, publication_date }`.
- Coordinator prompts should specify **goals + quality criteria**, not step-by-step procedures.

### Task 1.4 — Multi-step workflows with enforcement

- **Programmatic prerequisite gates** for hard rules (e.g., block `process_refund` until `get_customer` returns verified ID).
- **Multi-concern decomposition:** parse a request like "return X, dispute Y, update Z" into parallel investigations.
- **Structured handoff for human escalation:** customer ID, root cause, refund amount, recommended action, attempted resolution.

### Task 1.5 — Hooks for tool-call interception

- **`PostToolUse`** — normalize heterogeneous data formats (Unix→ISO 8601, status codes→names) before model sees results.
- **`PreToolUse`** — intercept outgoing calls to enforce compliance (block refunds > $500, redirect to human).
- **Hooks for guaranteed compliance; prompts for soft preferences.** Non-zero failure rate of prompt instructions is unacceptable for financial operations.

### Task 1.6 — Task decomposition

- **Prompt chaining (fixed pipelines)** for predictable workflows: per-file analysis → cross-file integration pass.
- **Dynamic adaptive decomposition** for open-ended tasks: map structure → identify high-impact areas → prioritized adaptive plan.
- **Anti-pattern:** single-pass review on 14 files at once → attention dilution → inconsistent results. Fix is multi-pass, NOT a larger context window.

### Task 1.7 — Session state

- **`--resume <session-name>`** — continue a specific prior conversation (linear).
- **`fork_session`** — copy conversation history into a new session ID for divergent branches (e.g., compare two refactor strategies).
- **Stale-tool-results gotcha:** if files have changed since the prior session, prefer **new session + injected summary** over resume with stale results.

---

## 5. Domain 2 — Tool Design & MCP (18%)

### Tool descriptions are the primary selection signal

Include: input formats, example queries, edge cases, "use this vs that" boundaries. **Minimal descriptions = unreliable selection.** Fix description before reaching for routers/classifiers.

### Structured error metadata

```json
{
  "isError": true,
  "errorCategory": "transient | validation | business | permission",
  "isRetryable": true | false,
  "message": "<human-readable>",
  "details": { "attemptedQuery": "...", "retryAfter": 5 },
  "suggestedAction": "..."
}
```

| Category | Retryable? | Agent action |
|---|---|---|
| `transient` (timeout, unavailable) | yes | Retry with backoff |
| `validation` (bad input) | no | Correct input, retry with fix |
| `business` (policy violation) | no | Explain to user, escalate or offer alternative |
| `permission` (auth gap) | no | Escalate, never retry |

**Don't conflate empty results with errors:** successful query that found nothing → `isError: false, results: []`. Failed query → structured error.

### Tool distribution & `tool_choice`

- **Scope each agent to 4–5 tools.** 18 tools degrades selection.
- **Specialized scoping:** synthesis agent gets `verify_fact`, NOT full web search (Q9).
- **`tool_choice: "any"`** to guarantee structured output across multiple extraction schemas.
- **Forced** (`{"type":"tool","name":"..."}`) to ensure a specific tool runs first.

### MCP server config

- **Project:** `.mcp.json` — shared via VC, use `${ENV_VAR}` for secrets.
- **User:** `~/.claude.json` — personal/experimental.
- All tools from all configured servers are discovered at connection time and available simultaneously.

### Built-in tools (Read, Write, Edit, Bash, Grep, Glob)

- **Grep** — content search (function names, error messages, imports).
- **Glob** — file path search (by name/extension pattern).
- **Read + Write fallback** when Edit fails on non-unique anchor text.

---

## 6. Domain 3 — Claude Code Configuration & Workflows (20%)

### CLAUDE.md hierarchy

- **User:** `~/.claude/CLAUDE.md` — personal, NOT shared.
- **Project:** `.claude/CLAUDE.md` or root `CLAUDE.md` — shared via VC.
- **Directory:** subdirectory `CLAUDE.md` — area-specific.
- **`@import`** — modularize content (always loaded — NOT conditional).
- **`.claude/rules/`** — path-conditional via YAML `paths:` glob.

### `.claude/rules/` for path-scoped rules

```yaml
---
description: Test file conventions
paths:
  - "**/*.test.{ts,tsx}"
  - "**/*.spec.{ts,tsx}"
---
# rules content here
```

Negation: `"!**/*.test.tsx"` excludes test files.

### Skills (`.claude/skills/<name>/SKILL.md`)

Frontmatter knobs:

| Knob | Purpose |
|---|---|
| `name` | Identifier |
| `description` | Auto-invocation match signal — write like a tool description with trigger phrases, edge cases, boundaries |
| `context: fork` | Run skill in isolated subagent — main convo only sees summary |
| `allowed-tools: [Read, Grep]` | Restrict tool scope (least privilege) |
| `argument-hint: <arg> [opt] — e.g., "..."` | Surface required parameters |

**Skills ≠ slash commands:** `.claude/commands/<name>.md` for explicit `/command`-typed; `.claude/skills/<name>/SKILL.md` for auto-invoked rich workflows.

**Skills do NOT have `paths:`.** For "apply only when editing X-type files," use `.claude/rules/` — NOT skills.

### Plan mode vs direct execution

- **Plan mode** — architectural changes, multi-file modifications, multiple valid approaches.
- **Direct execution** — single-file, clear-scope, well-understood.
- **Explore subagent** — for verbose discovery output that would otherwise pollute context.

### CI integration

- **`-p` / `--print`** — non-interactive mode (CRITICAL for CI; without it the job hangs).
- **`--output-format json --json-schema`** — parseable structured output.
- **CLAUDE.md** provides project context (testing standards, fixtures, criteria) to CI-invoked Claude Code.
- **Independent review instance > self-review** — model retains generation context, less likely to question its own output.

---

## 7. Domain 4 — Prompt Engineering & Structured Output (20%)

### Explicit criteria > vague instructions

"Flag comments only when claimed behavior contradicts actual behavior" >> "Be conservative" or "Only high-confidence findings."

### Few-shot prompting

- **2–4 targeted examples** for ambiguous scenarios.
- Show **reasoning** for why one option was chosen over plausible alternatives.
- Demonstrate **format consistency** (location, issue, severity, suggested fix).
- Reduce false positives without sacrificing generalization.

### Structured output via tool_use + JSON schema

- **Most reliable approach** — eliminates JSON syntax errors.
- Does NOT eliminate **semantic** errors (values in wrong fields, sums that don't match).
- Make fields **nullable** when source may not contain info — prevents fabrication.
- Use **`"other" + detail`** enum pattern for extensibility.
- Add `"unclear"` enum for ambiguous cases.

### Validation-retry loops

- Send retry with: original document + failed extraction + specific validation error.
- **Limits:** retries fix format/structural errors; won't help when info is genuinely **absent**.
- Add `detected_pattern` field for systematic false-positive analysis.
- Self-correction validation: extract `calculated_total` alongside `stated_total`; flag mismatches.

### Message Batches API

- **50% cost savings, up to 24h window, no SLA.**
- Fit: overnight reports, weekly audits, nightly test generation.
- Misfit: blocking workflows (pre-merge checks).
- **NO multi-turn tool calling** within a batch request.
- Use **`custom_id`** for request/response correlation.
- Refine prompts on a sample before batching at scale.

### Multi-pass review

- Per-file local analysis pass + separate cross-file integration pass.
- Independent review instance for catching subtle issues.
- Verification passes with self-reported confidence for routing.

---

## 8. Domain 5 — Context Management & Reliability (15%)

### Conversation context preservation

- **API is stateless** — every request must include the full `messages` array.
- **"Lost in the middle" effect** — put critical findings at start/end.
- Trim verbose tool outputs (40+ fields → 5 relevant ones) before they enter context.
- Maintain a **"case facts" block** outside summarized history (amounts, dates, IDs, statuses).
- Place **key findings summaries at the start** of aggregated inputs.

### Escalation patterns

- **Escalation triggers:** customer requests human, policy gaps (not just complex cases), inability to make progress.
- Honor explicit human-agent requests **immediately**.
- Acknowledge frustration but offer resolution if within capability; escalate only if customer reiterates preference.
- Escalate when policy is **ambiguous or silent** (e.g., competitor price match when policy only addresses own-site).
- Multiple matches → **ask for additional identifiers**, never heuristic-pick.

### Error propagation

- Subagents implement **local recovery** for transient failures.
- Propagate to coordinator only **errors that can't be resolved locally** + partial results + what was attempted.
- Distinguish access failures (need retry decisions) from valid empty results.
- Annotate synthesis output with **coverage gaps** when sources are unavailable.

### Large codebase exploration

- **Scratchpad files** for persisting findings across context boundaries.
- **Subagent delegation** to isolate verbose exploration; main agent coordinates.
- **`/compact`** when context fills with discovery output.
- Crash recovery: agents export structured state (manifests); coordinator re-injects on resume.

### Human review workflows

- **Aggregate accuracy can hide poor performance** on specific document types/fields.
- **Stratified random sampling** for measuring error rates and detecting novel patterns.
- Field-level confidence scores calibrated against labeled validation sets.
- Validate accuracy by document type AND field segment before reducing human review.

### Information provenance

- Subagents output structured **claim-source mappings** (URL, doc, excerpt).
- Synthesis preserves and merges mappings — don't compress them away.
- Conflicting statistics from credible sources → **annotate with attribution**, don't arbitrarily pick.
- Require **publication/collection dates** to prevent temporal differences from being misinterpreted as contradictions.

---

## 9. Critical Distinctions (Common Traps)

### `fork_session` vs `context: fork` (skill)

| | `fork_session` | `context: fork` |
|---|---|---|
| What's forked | Conversation history (full inheritance) | Execution context (no inheritance) |
| Where set | SDK option / `fork_session()` | SKILL.md frontmatter |
| Trigger | Explicit, user/code initiated | Skill firing |
| Persistence | New session ID, persistent, resumable | Ephemeral, runs and returns summary |
| Purpose | Diverge FROM shared baseline | Isolate verbose work, return summary |
| Mental model | `git branch` from a commit | Sandboxed function call |

### Parallel tool calls vs Message Batches API

| | Parallel tool calls | Message Batches API |
|---|---|---|
| Scope | Within one conversation turn | Across many independent requests |
| Correlation ID | `tool_use_id` (`toolu_...`) | `custom_id` (you assign) |
| Latency | Real-time | Up to 24h, no SLA |
| Cost | Standard | ~50% off |
| Multi-turn tools | Yes | **No** — single-shot only |
| Use case | Multi-step agent workflows | Overnight bulk processing |

### Skills vs Slash Commands vs Rules vs CLAUDE.md

| Mechanism | When loaded | Purpose |
|---|---|---|
| `CLAUDE.md` (root/project/user) | Always (per directory) | Universal standards, project context |
| `@import` inside CLAUDE.md | Always (inlined into CLAUDE.md) | Modularize CLAUDE.md content |
| `.claude/rules/<name>.md` with `paths:` | Conditionally on file path match | Conventions for specific file types |
| `.claude/skills/<name>/SKILL.md` | When skill fires (auto by description match or explicit) | Reusable workflows |
| `.claude/commands/<name>.md` | When user types `/<name>` | Explicit shortcuts |

### IDs to keep separate

- **`tool_use_id`** (`toolu_...`) — one tool call inside one turn.
- **`custom_id`** — one batch request inside a Batches submission.
- **session ID** — one whole conversation; used by `--resume` and `fork_session`.

---

## 10. YAML & Code Snippets to Recognize on Sight

### `.claude/rules/` path-scoped

```yaml
---
description: Test conventions
paths:
  - "**/*.test.{ts,tsx}"
  - "!**/__tests__/fixtures/**"
---
```

### Skill frontmatter (full)

```yaml
---
name: refactor-explore
description: Use when the user wants to plan a refactor — "refactor X", "split this monolith", "extract module"...
context: fork
allowed-tools: [Read, Grep, Glob]
argument-hint: <target-symbol-or-path> — e.g., "src/auth/login.ts"
---
```

### MCP server config (`.mcp.json`)

```json
{
  "mcpServers": {
    "github": {
      "command": "github-mcp",
      "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" }
    }
  }
}
```

### Tool definition for API request

```json
{
  "name": "lookup_order",
  "description": "Retrieves order details by ID. Use when customer references an order number (e.g., '#12345'). Do NOT use for account questions — use get_customer.",
  "input_schema": {
    "type": "object",
    "properties": { "order_id": { "type": "string" } },
    "required": ["order_id"]
  }
}
```

### Parallel subagent spawning in one coordinator turn

```json
{
  "stop_reason": "tool_use",
  "content": [
    { "type": "tool_use", "id": "toolu_a", "name": "Task", "input": { "agent": "web_searcher", "prompt": "..." } },
    { "type": "tool_use", "id": "toolu_b", "name": "Task", "input": { "agent": "doc_analyst", "prompt": "..." } },
    { "type": "tool_use", "id": "toolu_c", "name": "Task", "input": { "agent": "synthesizer", "prompt": "..." } }
  ]
}
```

---

## 11. Out-of-Scope Topics (Skip These)

The guide explicitly states these will NOT appear:

- Fine-tuning Claude / training custom models
- Constitutional AI, RLHF, safety training internals
- Model weights, internal architecture
- Claude API authentication, billing, account management
- API key rotation, OAuth, auth protocol details
- Rate limiting, quotas, pricing calculations
- Streaming API / server-sent events implementation
- Token counting algorithms, tokenization specifics
- Prompt caching internals (knowing it exists is enough)
- Embeddings / vector DB implementation
- Vision / image analysis
- Computer use / browser automation
- Cloud provider configs (AWS, GCP, Azure)
- Performance benchmarking, model comparison metrics
- Detailed implementation of specific languages/frameworks (beyond tool/schema config)
- Deploying or hosting MCP servers (infrastructure, networking, containers)

---

## 12. Question-Pattern Recognition (Cheat Sheet)

When you see this phrase | Reach for this answer
---|---
"Files spread throughout the codebase" / "regardless of location" | `.claude/rules/` with `paths:` glob
"Every developer when they clone" | Project-scoped (`.claude/...`)
"Personal experimental" / "without affecting teammates" | User-scoped (`~/.claude/...`)
"Each subagent succeeds but final output misses..." | Coordinator decomposition is too narrow
"How should errors flow back to the coordinator?" | Structured error context (failure type, attempted query, partial results, alternatives)
"X% simple Y, 15% complex Z" | Scoped tool for common case, delegate complex via coordinator
"Job hangs indefinitely / waiting for input" in CI | Add `-p` / `--print` flag
"Reduce API costs / overnight reports" | Message Batches API
"Blocking pre-merge check / developers wait" | Synchronous API only, NOT batch
"Architectural / multi-file / multiple approaches" | Plan mode
"Single-file bug fix with clear stack trace" | Direct execution
"Compare two refactor strategies from same baseline" | `fork_session`
"Skill should explore without flooding main convo" | `context: fork`
"Agent skips required verification step" | Programmatic prerequisite gate (hook), NOT prompt
"Refunds over $500 must require approval" | `PreToolUse` hook to block + redirect
"Tool descriptions are too similar / model misroutes" | Improve descriptions FIRST (not router/classifier)
"Self-reported confidence" / "sentiment-based escalation" | Both wrong — explicit criteria + few-shot
"Single-pass review on 14 files inconsistent" | Multi-pass: per-file + cross-file integration
"Resume yesterday's session but files changed" | New session + injected summary
"Need machine-parseable CI output" | `--output-format json --json-schema`
"Skill needs explicit parameters" | `argument-hint: <required> [optional] — e.g., "..."`
"Restrict skill to read-only" | `allowed-tools: [Read, Grep, Glob]`

---

## 13. Final-Mile Prep (Last 60 Minutes)

Highest-ROI study order if time is short:

1. **(20 min)** Re-read Domain 1 of the exam guide (pages 5–9). Knowledge points are written like multiple-choice answers almost verbatim.
2. **(20 min)** Work through sample questions Q1, Q2, Q3, Q7, Q8, Q9 with explanations. They cover the most-tested patterns.
3. **(10 min)** Memorize the table in section 12 above.
4. **(10 min)** Memorize section 9 (critical distinctions) — these are the trap-detector cheat sheet.

---

*Generated from analysis of the official exam guide on 2026-04-25.*
