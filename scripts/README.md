# scripts/

Dev tooling only — not application logic. E.g. once sops+age is set up (see
`docs/security.md`), a `decrypt-env.sh`/`.ps1` helper that runs a command with secrets injected
into env for that process only (never writing plaintext to disk) would live here.
