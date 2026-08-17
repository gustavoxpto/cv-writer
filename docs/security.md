# Security posture

## Secrets: no plaintext at rest

Decision (2026-08-17): credentials are never stored unencrypted, and never persisted longer
than needed. Two mechanisms, layered:

1. **Encrypted-at-rest for anything that must live in the repo.** Use
   [sops](https://github.com/getsops/sops) with [age](https://github.com/FiloSottile/age) keys
   (or an equivalent — 1Password CLI, git-crypt) for any secret that genuinely needs to be
   versioned (e.g. an encrypted `.env` for a shared dev environment). Encrypted files live in
   `secrets/`, named `*.enc.yaml` / `*.enc.env`. The age/sops private key itself is **never**
   committed — it lives outside this repo (password manager, local keychain).
2. **Ephemeral decryption, not persistent plaintext.** Secrets get decrypted into the running
   process's environment only, at the moment they're needed (e.g. `sops exec-env`), and are
   never written to disk unencrypted. Shell history and `.bash_history`-style leakage should be
   avoided by using files/env, not inline command-line arguments, for secret values.

**Status: documented target, not yet wired up.** `secrets/` currently just holds this doc and a
placeholder. Setting up actual sops+age keys is a deliberate next step — do it explicitly
(generate a key, add `.sops.yaml` config) rather than assuming it's already configured.

## What must never happen

- A raw credential (API key, password, token, private key) committed in plaintext, even in a
  branch that gets squashed later — git history is effectively permanent once pushed.
- A secret pasted into a spec, ADR, pairing note, or PR description.
- A `.env` (unencrypted) committed. `.gitignore` blocks this by pattern, but treat that as a
  backstop, not the actual control — think before `git add`.

## AI execution & deletion

See `CLAUDE.md`'s hard rules. In short: full local execution is trusted, deletion of anything
is not — it always requires fresh explicit permission, no matter how routine the task looks.

This is backed by a technical control, not just the instruction: `.claude/settings.json` sets
`permissions.ask` on `rm`, `del`, `Remove-Item`, `git clean`, `git reset --hard`, and force-push
patterns, so the harness prompts for confirmation on those specifically, even in a session that
otherwise runs commands freely. Note this is a prefix-match safety net, not a sandbox — it
doesn't catch every way a destructive command could be composed (e.g. buried in a chained
command); the actual rule is behavioral (see `CLAUDE.md`), this just backstops the common cases.

## CI / GitHub

- Actions workflows in `.github/workflows/` should not have write access to secrets they don't
  need — scope `GITHUB_TOKEN` and any repo secrets to least privilege per workflow.
- Branch protection on `main` (set up in GitHub repo settings once the remote exists): require
  the CI check and at least one review before merge, matching the approval-gate decision in
  `CLAUDE.md`.

## Open questions (revisit as the harness grows)

- Dependency/SAST scanning tool (e.g. `npm audit`/`pip-audit`/Dependabot/Snyk) — not chosen yet,
  depends on what language(s) end up in `src/`.
- Whether AI-run code should ever execute in a container/sandbox rather than directly on host —
  deferred; revisit if a project here starts running untrusted or generated code more heavily.
