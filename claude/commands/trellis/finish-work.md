Finish the active Trellis task. Load the trellis-finish-work skill and execute the finish-work workflow: verify implementation complete, `trellis-check` PASS, selected reviews PASS, explicit Finish Approval recorded, Spec Update Decision recorded, Observable Outcomes recorded, Delivery Sync Check recorded, required merge-review PASS, code committed or explicitly not needed, and final validation recorded. Then run `python3 ./.trellis/scripts/finalize_task_archive.py <task-dir>` to archive and sync the workspace journal/index.

Do NOT write new code. Do NOT fix bugs. Do NOT bypass failed gates.
