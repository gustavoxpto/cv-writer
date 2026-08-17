# secrets/

Only encrypted files belong here (`*.enc.yaml`, `*.enc.env`, sops/age output). Never an
unencrypted credential. See `docs/security.md` for the full approach and its current status
(not yet wired up — this is the documented target).

`.gitignore` at the repo root blocks common unencrypted secret filenames as a backstop, but
that's not a substitute for actually setting up sops+age before anything real lands here.
