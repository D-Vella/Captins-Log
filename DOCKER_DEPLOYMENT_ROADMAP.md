# Captain's Log — Docker Deployment Pipeline Roadmap

> Replace the manual `docker save` → copy → `docker load` tar shuffle with a registry-based push/pull pipeline, then progressively automate the build and the deploy.
> Each phase leaves you with a working way to get code onto the mini PC — never a half-migrated broken state.

---

## How To Use This Roadmap

Work top to bottom. **Phase 1 solves roughly 90% of your current pain** (slow iteration) in a single session — do it first and stop there if you like. Phases 2–4 are progressively more automation and progressively more optional. Do not start a phase until the previous one's exit criteria all tick.

Registry choice throughout: **GHCR (`ghcr.io`)**, GitHub's own container registry, because your code already lives on GitHub, private repos are free, and CI auth later is basically handed to you. Everything below works the same with Docker Hub if you ever prefer it — only the login host and image path change.

---

## Phase 1 — Registry Round-Trip (Replace The Tarball)
**Goal:** Get one code change from dev PC to mini PC via push/pull, by hand, with no `.tar` file and no per-iteration compose edits.
**Estimated effort:** 1 session

> **Why this is the big win:** `docker push`/`docker pull` transfer only the layers that changed, not the whole image. After the first push, a code-only change moves a few MB in seconds instead of copying the entire tarball every time. This single change is what makes iteration fast.

### Tasks
- [ ] Create a GitHub Personal Access Token (classic) with `write:packages` and `read:packages` scopes — this is the password Docker uses to authenticate to GHCR. Treat it like any other secret (it goes in a password manager, never in a repo).
- [ ] On the **dev PC**: `docker login ghcr.io` — username is your GitHub username, password is the token.
- [ ] Add a `.dockerignore` file **before building** (see Phase 2 for the full list — at minimum: `.env`, `.git/`, `data/`, `__pycache__/`, `.venv/`). This stops secrets and junk being copied into the image.
- [ ] Tag the image with the full registry path:
  `docker build -t ghcr.io/d-vella/captains-log:latest .`
- [ ] Push it: `docker push ghcr.io/d-vella/captains-log:latest`
- [ ] On the **mini PC**: `docker login ghcr.io` (one-time), then edit `docker-compose.yml` so the service uses `image: ghcr.io/d-vella/captains-log:latest`. Delete the local-image workaround you currently use.
- [ ] Deploy: `docker compose pull && docker compose up -d`
- [ ] Confirm the container reads its secrets from a `.env` **on the mini PC** via `env_file:` in compose — and that there is no `.env` baked inside the image.

### Exit Criteria
A code change reaches the mini PC through `push` → `pull` with no tarball and no compose editing. A second push after a small code change visibly transfers only a small layer, not the whole image.

---

## Phase 2 — Lean, Cache-Friendly Dockerfile
**Goal:** Understand layer caching well enough to make every rebuild fast and the shipped image small.
**Estimated effort:** 1 session

> **Why order matters:** Docker caches layers and only rebuilds from the first changed instruction downward. If you `COPY` your app code *before* installing dependencies, then every code change invalidates the dependency layer and reinstalls everything. Copy `requirements.txt` and install deps **first**, then copy code — so a code change only rebuilds the tiny final layer.

### Tasks
- [ ] Reorder the Dockerfile: `COPY requirements.txt` → `RUN pip install ...` → *then* `COPY . .` for the app code.
- [ ] Fill out `.dockerignore` properly: `.env`, `.git/`, `data/`, `__pycache__/`, `.venv/`, `notebooks/`, `*.tar`, any local cache dirs.
- [ ] Pin the base image to an explicit tag (e.g. `python:3.12-slim`) rather than `latest`, so builds are reproducible and small.
- [ ] Consider a multi-stage build only if build-time tooling doesn't need to ship in the final image (be honest — for a Streamlit app this may be unnecessary; don't add it just because it's a "best practice").
- [ ] After a code-only change, run `docker push` and watch the output: most layers should report *already exists*, and only the small code layer should upload.

### Exit Criteria
A code-only change rebuilds using cached dependency layers (fast) and pushes in seconds. The final image contains only what the app needs to run — no build junk, no secrets, no `data/`.

---

## Phase 3 — Automated Build & Push (GitHub Actions)
**Goal:** Stop building and pushing by hand — let CI do it when you `git push`.
**Estimated effort:** 1–2 sessions

> **Why CI here:** A GitHub Actions "runner" is just a throwaway machine GitHub spins up to run your build. It removes the "did I remember to build and push?" step and guarantees the image always matches what's on `main`. For GHCR specifically, the runner already has a built-in `GITHUB_TOKEN`, so you don't manage any registry credentials yourself.

### Tasks
- [ ] Add `.github/workflows/build.yml`, triggered on push to `main`.
- [ ] Use `docker/build-push-action` to build and push to `ghcr.io`.
- [ ] Authenticate with the built-in `GITHUB_TOKEN` (no secret to create).
- [ ] Tag each image with both `:latest` and the git short SHA (e.g. `:a1b2c3d`) so you can trace exactly which commit a running image came from.
- [ ] Push a trivial change to `main` and confirm a new image appears in GHCR without you building anything locally.

### Exit Criteria
Pushing to `main` publishes a new image to GHCR automatically. Your dev PC is no longer in the build loop.

---

## Phase 4 — Automated Deploy To The Mini PC
**Goal:** Close the loop so new images reach the running container without a manual pull.
**Estimated effort:** 1 session

> **Honest note:** This is convenience, not necessity. A manual `docker compose pull && docker compose up -d` when *you* decide to deploy is a perfectly good permanent stopping point — and it's the safest, because you control exactly when things change. Only automate this if the manual step genuinely annoys you.

### Options (pick one)
- [ ] **Manual (recommended default):** SSH into the mini PC and pull/up when you want a new version. Most control, least magic.
- [ ] **Scheduled:** a Windows Task Scheduler job that runs `docker compose pull && docker compose up -d` on a timer.
- [ ] **Watchtower:** a small container that watches the registry and auto-updates your services. Least effort, least control — it'll pull changes whether or not you're ready for them.

### Exit Criteria
Your chosen mechanism updates the mini PC from the registry, and you can explain in a sentence why you picked it over the other two.

---

## Field Notes
*Running log of discoveries, quirks, and decisions. Engineer's notebook, not polished docs.*

- [Date] — Migrated from `docker save`/`load` tar shuffle to GHCR push/pull. Iteration time dropped from [X] to [Y].
- [Date] — [Any GHCR auth / token-scope gotchas]
- [Date] — [Dockerfile layer-ordering observation]

---

## Dependencies Reference

| Thing | Purpose | Notes |
|-------|---------|-------|
| Docker + Docker Compose | Build, run, push, pull | Already installed both machines |
| GitHub account (GHCR) | Private image registry | Free private packages |
| GitHub PAT (`write:packages`) | Docker → GHCR auth | Phase 1; store in password manager |
| GitHub Actions | Automated build/push | Phase 3; uses built-in `GITHUB_TOKEN` |
| Watchtower (optional) | Auto-deploy on mini PC | Phase 4 only if you choose it |

---

## Principles To Keep In Mind

**Secrets never enter the image.** Image layers are permanent — a secret copied in and deleted later still lives in an earlier layer. Secrets stay on the host in `.env`, injected at runtime via `env_file:`. This is the same discipline you already use for source code, applied to a second artifact.

**Private by default.** No personal home-lab app needs to be a public image. Make something public only when you deliberately want to share it.

**Push/pull moves only the delta.** Order your Dockerfile so unchanged dependency layers stay cached. Fast iteration is a consequence of good layer ordering, not luck.

**Don't over-build for one node.** A single mini PC does not need Kubernetes, a self-hosted registry, or GitOps tooling. Compose + a private registry (+ optionally Actions) is the whole thing. If you find yourself reaching for those, that's scope creep talking.

**Manual is a legitimate stopping point.** Phases 3 and 4 are optional convenience. If Phase 1 makes iteration painless, you're allowed to stop there.
