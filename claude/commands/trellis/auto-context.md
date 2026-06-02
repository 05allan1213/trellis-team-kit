Auto-generate implement.jsonl and check.jsonl entries from existing task artifacts (prd.md, design.md, research files, specs). User only confirms.

These JSONL files tell sub-agents which context files to read. Currently manual and error-prone — this command makes it one-click.

**Steps:**

1. **Find the active task**:
   ```bash
   python3 .trellis/scripts/task.py current --source
   ```

2. **Scan for relevant files** — Find files that sub-agents would need as context:

   a. **Spec files**: List all files under `.trellis/spec/` that match the task's domain:
      ```bash
      find .trellis/spec/ -name "*.md" -type f
      ```

   b. **Research files**: List all files under the task's `research/` directory:
      ```bash
      find <task-dir>/research/ -name "*.md" -type f
      ```

   c. **Task artifacts**: Include prd.md, design.md, implement.md (these are always injected by hooks, so don't duplicate — skip these)

   d. **Pattern-matched specs**: For each file in the task's declared scope (from implement.md "Files / Areas Likely Touched"), find matching spec files under `.trellis/spec/`

3. **Generate implement.jsonl** — For each relevant file, create a JSONL entry:
   ```json
   {"file": ".trellis/spec/frontend/index.md", "reason": "Frontend spec relevant to UI changes"}
   {"file": "<task-dir>/research/grill-me.md", "reason": "PRD challenge results"}
   {"file": ".trellis/spec/api/index.md", "reason": "API spec for endpoint changes"}
   ```

4. **Generate check.jsonl** — Same format but emphasize verification specs:
   ```json
   {"file": ".trellis/spec/testing/index.md", "reason": "Testing standards for check verification"}
   {"file": ".trellis/spec/api/index.md", "reason": "API contract to verify against"}
   ```

5. **Present to user for confirmation**:
   ```
   📦 Auto-generated context files

   implement.jsonl (4 entries):
     1. .trellis/spec/frontend/index.md — Frontend spec
     2. .trellis/spec/api/index.md — API spec
     3. <task>/research/grill-me.md — PRD challenge
     4. .trellis/spec/guides/index.md — Team guides

   check.jsonl (2 entries):
     1. .trellis/spec/testing/index.md — Testing standards
     2. .trellis/spec/api/index.md — API contract

   Reply 'ok' to write, or edit the list.
   ```

6. **Write the files** using task.py add-context:
   ```bash
   python3 .trellis/scripts/task.py add-context "<task-dir>" implement "<file>" "<reason>"
   python3 .trellis/scripts/task.py add-context "<task-dir>" check "<file>" "<reason>"
   ```

**Rules:**
- Never include code files that will be modified (sub-agents already see those via git diff)
- Never include task artifacts already injected by hooks (prd.md, design.md, implement.md)
- Prefer spec files over research files for check.jsonl (verification focus)
- If implement.jsonl or check.jsonl already has entries, append rather than overwrite
- If no spec directory exists, note this and suggest creating one
