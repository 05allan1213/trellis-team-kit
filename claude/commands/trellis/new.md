Start a new Trellis task with an interactive classification wizard. Instead of requiring the user to understand L0-L5 routing, ask simple questions to determine the task level and set up the right workflow path.

**Wizard flow:**

### Step 1: Is this a question or implementation?

Ask the user:
> "Are you asking a question/explanation, or do you want to change code?"

- **Question/explanation** → L0 (pure Q&A). Answer directly, no task. **End.**
- **Change code** → Continue to Step 2.

### Step 2: How big is the change?

Ask the user:
> "How would you describe this change?"
>
> A) Tiny — typo, copy fix, one-line change
> B) Simple — add a function, fix a clear bug, small feature
> C) Normal — new page, CRUD feature, API endpoint
> D) Complex — spans frontend+backend, database schema change, auth system
> E) Large — whole module refactor, multi-service change, architecture overhaul

- **A** → L1 path. Ask: "Want to skip Trellis and just do it inline?" If yes → L1 inline. If no → treat as L2.
- **B** → L2 (light implementation)
- **C** → L3 (normal feature/bugfix)
- **D** → L4 (complex cross-layer)
- **E** → L5 (multi-agent / large refactor)

### Step 3: Create the task

Once classified, execute:

```bash
python3 .trellis/scripts/task.py create "<user's description>" --slug <slug>
```

Then update task.json with the level:

```bash
python3 -c "
import json, sys
task_file = sys.argv[1]
level = sys.argv[2]
with open(task_file) as f: d = json.load(f)
d['level'] = level
with open(task_file, 'w') as f: json.dump(d, f, indent=2, ensure_ascii=False)
" <task-dir>/task.json L<level>
```

### Step 4: Show what happens next

Based on the level, tell the user exactly what to expect:

**L2**: "I'll write a brief prd.md, curate context files, then ask you to approve implementation. Light process — no design doc needed."

**L3**: "I'll write prd.md + implement.md with a Review Gate Contract (trellis-check + code-review), curate context, then ask you to approve. Optional design.md if the change has architectural impact."

**L4**: "I'll write prd.md + design.md + implement.md with full review gates (check + spec-review + code-review + architecture-review), curate context, then ask you to approve. This is a complex change — careful planning first."

**L5**: "I'll write full planning artifacts, set up all review gates including merge-review, and recommend OMC parallel execution if the work can be safely split. This needs thorough planning — multiple agents may work in parallel."

### Step 5: Start planning

Load the `trellis-brainstorm` skill and begin Phase 1 (planning).

**Important:** Task creation approval is NOT implementation approval. After planning, you must wait for explicit user approval before `task.py start`.
