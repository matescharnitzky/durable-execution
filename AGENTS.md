# Working on the durable execution lab

- Use `make setup` and `make check` locally and in Codex Cloud.
- Keep runtime integrations in separate packages. Share report inputs and fixtures. Use each runtime's own storage to recover unfinished runs.
- Keep real provider credentials out of Git, tests, and logs. Use the local 1Password setup described in the README.
- Use [create-issue](.agents/skills/create-issue/SKILL.md) for issue descriptions, [visual-pr](.agents/skills/visual-pr/SKILL.md) for pull requests, and [recovery-demo](.agents/skills/recovery-demo/SKILL.md) for recovery evidence.
- Use one branch and PR per issue. Record the checks run and any unverified behavior in the PR.
