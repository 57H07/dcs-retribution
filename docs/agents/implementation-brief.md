# Implementation brief for sub-agents

You implement one or more GitHub issues of the fork `57H07/dcs-retribution` (remote `origin`). An orchestrator merges your PR; you never merge.

## Before coding

1. Read your issue(s): `gh issue view <n> -R 57H07/dcs-retribution --comments`. Read the parent epic too.
2. Read the matching section of `docs/dev/design/specification-fonctionnelle.md` (grep for the ID, e.g. `PER-02`), plus §1 (rules) and §9 (decisions D1-D16). The spec wins over your own preferences; where it is silent, choose the simplest option consistent with the existing code and say so in the PR.
3. Work on a branch named `<type>/<issue-id>-<slug>` (e.g. `fix/bug-03-strike-div-zero`), created from an up-to-date `origin/dev` (`git fetch origin && git switch -c <branch> origin/dev`).

## Upstream PR takeovers (label `from-upstream-pr`)

- `git fetch upstream pull/<N>/head:upstream-pr-<N>`, then bring its commits onto your branch with their original authorship (cherry-pick or rebase), resolve conflicts, then finish what the issue requires.
- Never push, comment or open anything on `dcs-retribution/dcs-retribution`. In text, write upstream references as `` `upstream#N` `` (code span), never as a link or bare `#N`.

## Environment

- Python: use `F:/_Projets/Jeux/DcsRetribution/venv/Scripts/python.exe` (3.11, all deps installed). Do not create another venv. If the issue changes `requirements.txt`, install into that venv and say so in your report.
- Client (`client/`, React/TS): run `npm ci` in your worktree's `client/` only if you touch the client; `npm test` (Vitest, single run), `npm run lint` and `npm run build` must pass.

## Web UI work (label `web`)

- Spec: `docs/dev/design/specification-interface-web.md`; its §6 decisions (W1-W19) win over everything else. ADR: `docs/adr/0001-interface-web-locale.md`.
- Visual reference: `docs/dev/design/mockups/*.dc.html` (direction A). Read them as HTML for layout, colors and copy; their `<x-dc>`/`{{accent}}` markup is a mockup format, not code to reuse. Accent = `#E8A33D`.
- The engine stays the source of truth: no game rule in the client. Commands are REST per resource (W3) and mutate `Game` under the global lock once WEB-00.4 is merged.
- A migrated screen deletes its Qt equivalent in the same PR (W9). Keep old saves loadable.
- Client checks: the Vitest/Vite scripts of `client/package.json` (`npm test`, `npm run lint`, `npm run build`). After WEB-00.5, regenerate the API client offline with the script it adds; before, start the server only if you must.
- Do not ask for in-game DCS tests: manual testing is suspended (W19). List DCS-only checks under `## Flight test` as usual.

## Done means

- Tests first where practical (`tests/`), covering every automated acceptance criterion.
- All green, run from your worktree root:
  - `<python> -m pytest tests -q`
  - `<python> -m black .` (then `--check` clean)
  - `<python> -m mypy game` and `<python> -m mypy tests`
- Add a line to `changelog.md` in the section for the version under development, following its existing style.
- Criteria that need DCS (in-flight tests) cannot be run here: list them as an unchecked checklist under `## Flight test` in the PR body.
- Investigation issues: post your findings as a comment on the issue (`gh issue comment`). If you find the cause, fix it with a regression test. If it cannot be reproduced without DCS, add a defensive fix plus test only when the cause is clear from code, and document the rest.

## Shipping

1. Conventional Commits messages. Keep upstream authors' commits intact.
2. `git fetch origin && git rebase origin/dev` (only before your first push), re-run the checks, then `git push -u origin <branch>`. Force-push is not allowed: to update a branch already pushed (e.g. conflicts with `dev`), `git merge origin/dev`, resolve, re-run the checks and push normally.
3. `gh pr create -R 57H07/dcs-retribution --base dev --title "<ID>: ..." --body-file <file>`; the body has `Closes #<n>` for each issue it completes, a short summary, decisions taken, test results, the `## Flight test` checklist if any, and ends with:
   `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
4. Do not merge, do not close issues by hand, do not edit other issues.

## Report back (max 15 lines)

PR URL, what changed (files/modules), decisions you took that the spec did not settle, check results, and anything left undone or risky. If you are truly blocked, stop and say exactly what blocks you.
