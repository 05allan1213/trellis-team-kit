# Gate System

## Gate Types

### 1. Task Creation Consent
- **Trigger**: AI recommends a standard task path (usually L2-L5)
- **Rule**: AI must ask for task creation consent before `task.py create`
- **Not**: Implementation approval

### 2. Implementation Consent
- **Trigger**: Planning artifacts complete
- **Rule**: AI must wait for user to explicitly say "start implementation" / "approve implementation" / "begin coding"
- **Blocks**: Source editing, implementer spawn, `task.py start`

### 3. Planning Artifact Gate
- **L2**: `prd.md` with testable AC + minimal `implement.md`
- **L3**: `prd.md` + `research/grill-me.md` + `implement.md` + JSONLs + `design.md` (optional)
- **L4/L5**: `prd.md` + `research/grill-me.md` + `design.md` + `implement.md` + JSONLs
- **Blocks**: Missing required artifact → no `task.py start`

### 4. Before-Dev Gate
- **Trigger**: After `task.py start`
- **Rule**: Must read all task artifacts and specs
- **Blocks**: No source editing before reading

### 5. Check Gate
- **Trigger**: After implementation
- **Rule**: lint + typecheck + tests + spec compliance
- **Output**: PASS/FAIL
- **Blocks**: FAIL → return to IMPLEMENTING

### 6. Review Gates
- **Trigger**: After check PASS
- **Rule**: Run selected review gates per Review Gate Contract
- **Output**: Each reviewer outputs PASS/FAIL
- **Blocks**: Any FAIL → return to IMPLEMENTING

### 7. Spec Update Decision Gate
- **Trigger**: After all check/review PASS
- **Rule**: Must record whether spec update is needed, with reason
- **Blocks**: Missing decision → no finish

### 8. Observable Outcomes Gate
- **Trigger**: After all check/review PASS, before finish
- **Rule**: `finish.md` must record concrete user- or operator-visible outcomes with verification evidence
- **Blocks**: Missing or placeholder-only outcomes → no finish

### 9. Build/Test Gate
- **Trigger**: After commit
- **Rule**: Run build/test, or explicitly record why not executable
- **Blocks**: Missing without explanation → no finish

### 10. Finish Gate
- **Trigger**: All preconditions met
- **Rule**: archive task + update journal + mark done
- **Blocks**: Any precondition missing → refuse execution

## Failed Gate Handling

```
gate FAIL
  → record blocking issues
  → return to IMPLEMENTING
  → fix
  → re-CHECKING
  → re-REVIEWING (if review gate failed)
  → re-check that gate
  → until PASS
```

**Forbidden**:
- Skip a failed gate
- Claim done while gate is FAIL
- Lower standards to make a gate "pass"
