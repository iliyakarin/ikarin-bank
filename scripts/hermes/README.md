# Hermes Scripts — Toolbelt for Efficient Context Management

Three complementary scripts for managing agent context with Ollama/llama.cpp (and any LLM backend).

**Goal:** Get ~70% more context into prompts by aggressively managing what goes in and where.

## Scripts

### 1. `scratchpad.py` — Context Scratchpad Engine

Persistent state file that tracks session history across runs.

```
python3 scripts/hermes/scratchpad.py init
python3 scripts/hermes/scratchpad.py update --status "Working on X" --add-task "Fix bug" "Add tests"
python3 scripts/hermes/scratchpad.py update --done-task "Fix bug"
python3 scripts/hermes/scratchpad.py add-file --file "src/lib/routingUtils.ts" --summary "Fixed validation"
python3 scripts/hermes/scratchpad.py log --errors test_output.txt
python3 scripts/hermes/scratchpad.py status
python3 scripts/hermes/scratchpad.py compact
```

Stores in `.hermes_scratchpad.md`:
- **Status** — current work description (overwritten each update)
- **Task Backlog** — growing task list, max 50 items
- **Error Log** — compressed terminal output, max 30 entries
- **File States** — code change tracker, max 20 entries

### 2. `skeletonize.py` — AST Code Skeletonizer

Strips function/method bodies from source files, keeping signatures, imports, types, interfaces, and docstrings.

```
python3 scripts/hermes/skeletonize.py frontend/lib/routingUtils.ts            # output skeleton
python3 scripts/hermes/skeletonize.py --ratio frontend/lib/routingUtils.ts    # show reduction stats
cat file.ts | python3 scripts/hermes/skeletonize.py                           # stdin mode
```

Tested languages: TypeScript, JavaScript, Python
Typical reduction: 30-50% character/line count

### 3. `compile_prompt.py` — Structural Prompt Builder

Assembles a cache-optimized prompt with sections ordered by stability:

```
python3 scripts/hermes/compile_prompt.py \
    --system "Your system prompt..." \
    --scratchpad .hermes_scratchpad.md \
    --file frontend/lib/routingUtils.ts \
    --skeletonize \
    --errors test_output.txt \
    --stats
```

Prompt layout (top to bottom):
| Section | Stability | Cache Hit |
|---|---|---|
| System Instructions | Static | 100% |
| Scratchpad State | Semi-static | ~90% |
| Target File / Skeleton | Semi-static | ~80% |
| Volatile Data (errors, output) | Always new | 0% (bottom) |

This ordering ensures Ollama/llama.cpp gets near-100% prefix cache hits on the static sections across repeated API calls.

## Workflow Example

```bash
# 1. Initialize scratchpad for new session
python3 scripts/hermes/scratchpad.py init

# 2. Update status before each major step
python3 scripts/hermes/scratchpad.py update --status "Fixing routing validation" --add-task "Fix regex" "Write tests"

# 3. When a file changes, record it
python3 scripts/hermes/scratchpad.py add-file --file "frontend/src/lib/routingUtils.ts" --summary "Fixed regex"

# 4. Run tests, capture errors
pnpm test > test_output.txt 2>&1

# 5. Log the errors
python3 scripts/hermes/scratchpad.py log --errors test_output.txt

# 6. Build cache-optimized prompt for agent call
python3 scripts/hermes/compile_prompt.py \
    --system "You are a frontend engineer..." \
    --scratchpad .hermes_scratchpad.md \
    --file frontend/src/lib/routingUtils.ts \
    --skeletonize \
    --errors test_output.txt \
    --stats

# 7. Mark tasks done
python3 scripts/hermes/scratchpad.py update --done-task "Fix regex"
```

## Design Principles

1. **Compression without loss** — skeletonizer preserves structure, only strips implementation details
2. **KV cache optimization** — static content at top, volatile at bottom
3. **Persistent across sessions** — scratchpad survives agent termination
4. **Backpressure** — all sections have max sizes to prevent unbounded growth

## Why Three Scripts?

Separation of concerns:
- **scratchpad.py** manages *state* (what's happened so far)
- **skeletonize.py** manages *compression* (reduce file sizes)
- **compile_prompt.py** manages *assembly* (build the final prompt)

Each can be used independently or chained together.
