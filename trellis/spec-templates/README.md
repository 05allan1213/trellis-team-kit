# Spec Templates

Installable specs are sourced from `marketplace/specs/web-app/` and copied by
`bootstrap/init.sh` according to `trellis/spec-manifest.txt`.

This directory is kept only for plan-facing template references and mirrored
examples that should not drift from the marketplace source.

trellis-team-kit specs regulate AI workflow behavior only: when to create a
task, how to review code, how to make architecture decisions, how to handle
parallel execution, and how to avoid repeated workflow mistakes. They do not
define personal coding style.

When adding or changing installable specs:

1. Update `marketplace/specs/web-app/`.
2. Update `trellis/spec-manifest.txt`.
3. Update the relevant `index.md`.
4. Keep any mirrored file in this directory byte-for-byte identical.
