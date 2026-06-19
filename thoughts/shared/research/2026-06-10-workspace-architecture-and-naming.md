---
date: 2026-06-10T19:01:51+07:00
researcher: i.gorvier
git_commit: 28a1d1686c7065c1bfa6538603a070efb60a0e35
branch: main
repository: smart-accounting-hub
topic: "Better workspace architecture & naming — replacing packages/shared_py + shared_ts"
tags: [research, architecture, monorepo, naming, uv-workspace, turborepo, refactor]
status: complete
last_updated: 2026-06-10
last_updated_by: i.gorvier
decision: "Option A — rename packages/shared_py→core, shared_ts→api-types; keep apps/+packages/ (Turborepo layout). Executed 2026-06-10."
last_updated_note: "Decision made and executed — see Decision & Outcome section."
---

# Research: Better Workspace Architecture & Naming

**Date**: 2026-06-10T19:01:51+07:00
**Researcher**: i.gorvier
**Git Commit**: 28a1d1686c7065c1bfa6538603a070efb60a0e35
**Branch**: main
**Repository**: smart-accounting-hub

## Research Question

The current workspace uses `packages/shared_py` (the entire Python backend domain) and `packages/shared_ts` (generated API types). The owner finds these names wrong: the `_py`/`_ts` suffixes look awkward, and "shared" undersells `shared_py` — it's really the backend's **single source of truth**, not a shared-utilities bin. Research a better architecture/naming, including the floated idea of a top-level `server/` directory.

> This is design research **with recommendations** (the owner asked for "better arc"), not the documentation-only mode used previously.

## Summary / Recommendation

The owner's instinct is **correct and backed by industry practice**:

- Naming a central domain package `shared` is a recognized anti-pattern (the "shared/ junk drawer"). `shared_py` holds all models, repositories, services, auth, and FX logic — it is the domain **core**, the thing everything depends on.
- Appending a language suffix (`_py` / `_ts`) to directory names is **not a recognized convention** anywhere; the information ("what language") is already in the package's manifest (`pyproject.toml` vs `package.json`).

**Two key facts make this the ideal moment to fix it:**

1. **Directory names are already decoupled from import names.** Code imports `smart_accounting` (the dir under `src/`), never `shared_py`. The TS side imports via the `@shared/*` alias and the npm name `@smart-accounting/shared`, never the `shared_ts` path. Renaming the *directories* touches **no import statement**.
2. **Nothing is implemented yet.** Every `.py`/`.tsx` file is a comment-only stub (see `2026-06-10-current-implementation-state.md`). The only build-breaking references to the directory names live in ~8 config lines; the rest are prose in docs and comment-stubs.

**Recommended direction: rename to purpose-based names, keep the conventional `apps/` + `packages/` split.**

- `packages/shared_py` → **`packages/core`** (import name `smart_accounting` unchanged)
- `packages/shared_ts` → **`packages/api-types`**

This directly resolves both complaints, matches the dominant Turborepo/uv convention, and is near-zero cost today. The owner's `server/`-grouping idea (Option B below) is also viable and is presented fairly — it's a taste call between "JS-ecosystem familiarity" and "backend cohesion." A decision is requested at the end.

## Detailed Findings

### What `shared_py` and `shared_ts` actually are today

| Package | Dir | Distribution / npm name | Import name (what code uses) | Role | Consumers |
|---|---|---|---|---|---|
| Python domain | `packages/shared_py` | `smart-accounting` | `smart_accounting` | Models, repos, services, auth, fx, i18n, config, ioc — **the whole backend domain** | `apps/api`, `apps/bot` (direct imports, Q4/D22) |
| TS contract | `packages/shared_ts` | `@smart-accounting/shared` | via `@shared/*` alias | Generated OpenAPI types + `Money` helper | `apps/miniapp` only |

The critical nuance: **three names are independent** in both ecosystems — directory name, distribution name, and importable name (confirmed by [uv workspace docs](https://docs.astral.sh/uv/concepts/projects/workspaces/)). `shared_py/` already maps to import `smart_accounting`. So the dir name is essentially a filesystem label; renaming it is a config + docs change, not a code change.

### Migration-cost inventory (verified via grep)

**`shared_py` — build-breaking references (must change): ~5**
- `pyproject.toml:25` — uv workspace `members`
- `pyproject.toml:48` — ruff `src`
- `pyproject.toml:64` — pytest `testpaths`
- `Makefile:71` — `mypy packages/shared_py ...`
- the directory move itself (+ `packages/shared_py/pyproject.toml` location)

**`shared_ts` — build-breaking references (must change): ~4**
- `pnpm-workspace.yaml:6`
- `package.json:15` — `types:gen` output path
- `apps/miniapp/tsconfig.json:20` — `@shared/*` alias target
- `.oxlintrc.json:62` — ignore path for `api.d.ts`

**Everything else is prose** (docs + comment-stubs): `STRUCTURE.md` (~8 spots), `CLAUDE.md` (2), `README.md`, `docs/*`, `THIRD_PARTY_NOTICES.md`, `migrations/env.py`, the MVP plan (~20 spots), and stub comments in `apps/*`. These update with a find/replace and don't break anything if missed.

> Note: several stub comments write `shared_py.auth.initdata`, `shared_py.services.invites`, etc. — using the **directory** name as if it were the **import** path. The real import root is `smart_accounting`, so these comments are already slightly wrong and will be rewritten when code lands regardless of any rename.

### Industry best practices (from web research, with sources)

1. **`apps/` + `packages/` is the dominant 2025-2026 layout** (Turborepo/Vercel). `apps/` = deployables (terminal nodes of the dep graph), `packages/` = libraries/tooling. Turborepo does **not** support recursive nested globs like `apps/**`; one level of depth is expected. ([Turborepo — Structuring a repository](https://turborepo.dev/docs/crafting-your-repository/structuring-a-repository), [Package types](https://turborepo.dev/docs/core-concepts/package-types))
2. **Organize by role (app vs library), not by language.** Polyglot repos treat the language as a per-member implementation detail; Nx explicitly calls top-level language grouping "a bad idea... provides no actual meaning." ([Nx — Folder Structure](https://nx.dev/docs/concepts/decisions/folder-structure), [Python+TS monorepo — J. Barbay](https://medium.com/@julien.barbay/python-and-typescript-in-a-monorepo-c862a3bacddb))
3. **`shared` for the central domain is a junk-drawer anti-pattern.** Prefer `core` (inner-hexagon / "everything depends on this"), `domain` (DDD-explicit), or the product name. ([Mindful Chase — Structuring Your Monorepo](https://www.mindfulchase.com/deep-dives/monorepo-fundamentals-deep-dives-into-unified-codebases/structuring-your-monorepo-best-practices-for-directory-and-code-organization.html), [Clean DDD structure & naming](https://medium.com/unil-ci-software-engineering/clean-ddd-lessons-project-structure-and-naming-conventions-00d0b9c57610))
4. **Language suffixes are not a convention.** Disambiguate by purpose instead: `smart-accounting` (Python domain) + `api-types`/`openapi-client` (TS). ([uv monorepo guide](https://medium.com/@naorcho/building-a-python-monorepo-with-uv-the-modern-way-to-manage-multi-package-projects-4cbcc56df1b4))
5. **Domain core + multiple Python entrypoints (API + bot/worker) is a known clean/hexagonal pattern.** A `server/`-style grouping that contains the core + several entrypoints is "less common, generally only seen with language-based top-level directories." ([LSST SQR-075 vertical monorepo](https://sqr-075.lsst.io/), [Clean DDD](https://medium.com/unil-ci-software-engineering/clean-ddd-lessons-project-structure-and-naming-conventions-00d0b9c57610))
6. **uv has no naming opinion**, but watch two gotchas: the workspace **root `[project].name` must be unique** vs members (else "Two workspace members are both named X"), and multi-package test suites want `--import-mode=importlib`. ([uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/), [3 things about uv workspaces](https://dev.to/aws/3-things-i-wish-i-knew-before-setting-up-a-uv-workspace-30j6))

## The Options

### Option A — Rename only, keep `apps/` + `packages/` (RECOMMENDED)

```
apps/        api · bot · miniapp            (unchanged)
packages/    core · api-types               (was shared_py · shared_ts)
```

- **Pros:** Fixes both complaints. Matches the dominant convention (Turborepo already orchestrates the TS side). Lowest cost (~9 config lines + docs). Zero import changes. Familiar to any future contributor.
- **Cons:** Doesn't visually group the Python backend together — `core`, `api`, `bot` sit in two dirs.
- **Cost now:** ~1 hour, mostly find/replace + a `git mv`.
- **Locked-decision impact:** none. Q4/D22 (bot imports `smart_accounting.services.*`), the two-container Dockerfile, and the uv/pnpm dual workspace all unchanged.

### Option B — Tier grouping `server/` + `web/` (owner's floated idea)

```
server/      core · api · bot               (all Python; core = source of truth)
web/         app · contracts                (Next.js + generated types; app was miniapp)
migrations/  ops/  docs/                     (unchanged)
```

- uv workspace members → `["server/core", "server/api", "server/bot"]`; pnpm workspace → `["web/app", "web/contracts"]`. Both use one-level globs/paths, so the Turborepo nested-glob limit is not actually hit (Turborepo only manages the two `web/*` packages).
- **Pros:** Matches the owner's mental model exactly — "this is the server, with one core and two entrypoints." Strong backend cohesion. Arguably more intuitive for a small Python-primary team with a single frontend. `core` as source of truth is front-and-center.
- **Cons:** Diverges from the ubiquitous `apps/`+`packages/` convention (mild onboarding cost for JS devs). Blends "deployable" (`api`, `bot`) and "library" (`core`) under one `server/` roof, losing the apps-vs-packages distinction that marks what's independently shipped. More churn (every app dir moves; Dockerfile CMDs, `STRUCTURE.md`, `docs/*` rewritten).
- **Cost now:** ~2-3 hours (still cheap because all code is stubs).
- **Locked-decision impact:** none functionally, but `STRUCTURE.md` §2-§4 and the architecture diagrams need a substantial rewrite.

### Option C — Status quo (keep `shared_py` / `shared_ts`)

- **Pros:** Zero work.
- **Cons:** Preserves the two issues the owner (correctly) dislikes; perpetuates the non-convention suffix and the "shared" misnomer into every file written from M1 onward — which is the most expensive time to change it.

### Naming sub-decisions (apply to A or B)

**Domain package:**
| Name | Dir → import | Signal | Note |
|---|---|---|---|
| `core` (rec.) | `core` → `smart_accounting` | "inner hexagon / source of truth" | short; dir ≠ import (same situation as today) |
| `smart-accounting` | `smart-accounting` → `smart_accounting` | "the product is the domain" | dir == distribution == import; most self-consistent; longer |
| `domain` | `domain` → `smart_accounting` | DDD-explicit | may confuse devs who read "domain" as DB term |

**TS contract package:** `api-types` (rec., literal) or `contracts` (broader; room for zod schemas + `Money`). npm name could move to `@smart-accounting/api-types` or stay `@smart-accounting/shared`.

## Architecture Documentation (current patterns, for reference)

- Dual workspace: uv (`apps/api`, `apps/bot`, `packages/shared_py`) + pnpm/Turborepo (`apps/miniapp`, `packages/shared_ts`). Two separate `packages/` members, one per language — the source of the `_py`/`_ts` disambiguation.
- Strict layering inside the domain package: models ← repositories ← services ← presentation (`STRUCTURE.md` §3).
- Q4/D22: `apps/bot` imports `smart_accounting.services.*` directly; CI grep-guard forbids `models`/`repositories` imports in `apps/bot`. **This rule keys off the import name `smart_accounting`, not the directory** — so it survives any directory rename untouched.

## Historical Context (from thoughts/)

- `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md:152-153` — the scaffold tree explicitly names `shared_py/` and `shared_ts/`; D-decisions D1-D32 don't lock the *directory names*, only the stack and the two-surfaces-one-service-layer rule (plan:128).
- `2026-06-10-current-implementation-state.md` — confirms all source is comment-only stubs, so a rename now costs almost nothing in code.
- `THIRD_PARTY_NOTICES.md:12-23` references `packages/shared_py/...` paths for MIT-derived files; these path citations would update with the rename.

## Related Research

- `thoughts/shared/research/2026-06-10-current-implementation-state.md`
- `thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md`
- `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md`

## Decision & Outcome (2026-06-10)

**Chosen: Option A** — keep the Turborepo `apps/` + `packages/` layout, rename only the two packages. Option B (`server/`+`web/`) was rejected because it disrupts the conventional Turborepo structure. Names: **`core`** (domain) and **`api-types`** (TS contract).

**Executed the same day** (the change is import-name-safe and all code is pre-implementation stubs):

- `packages/shared_py` → `packages/core` · `packages/shared_ts` → `packages/api-types` (plain `mv`; files untracked so no `git mv`).
- Config edits: root `pyproject.toml` (workspace members, ruff `src`, pytest `testpaths`), `Makefile` (mypy), `pnpm-workspace.yaml`, root `package.json` (`types:gen` + description), `apps/miniapp/tsconfig.json` (`@shared/*` alias), `.oxlintrc.json` (ignore path).
- npm package renamed `@smart-accounting/shared` → `@smart-accounting/api-types`.
- `uv.lock` editable path patched (`packages/shared_py` → `packages/core`), preserving pinned versions.
- Doc + stub-comment sweep across `STRUCTURE.md`, `CLAUDE.md`, `README.md`, `THIRD_PARTY_NOTICES.md`, `docs/*`, the MVP plan, and `apps/**` / `packages/**` stub comments (`shared_py.x` import shorthand corrected to `smart_accounting.x`).
- **Not touched:** the Python import name `smart_accounting`, all `import` statements, `turbo.json`, console scripts/distribution names, `apps/` directories, and this file's + `2026-06-10-current-implementation-state.md`'s before/after narrative (left as historical record).

**Verified:** `uv sync --all-packages` resolves `smart-accounting` from `packages/core`; `import smart_accounting, smart_accounting_api, smart_accounting_bot` all succeed; `pnpm install` relinks; `@smart-accounting/api-types` `tsc --noEmit` passes.

### Deferred naming notes (not adopted)
- Domain package kept distribution name `smart-accounting`, so no workspace-root rename was needed (the uv "two members named X" gotcha only applies if the domain package's *distribution* name had become a bare collision — it did not).
- `api-types` chosen over `contracts`; revisit only if zod schemas + `Money` outgrow the "just generated types" framing.
