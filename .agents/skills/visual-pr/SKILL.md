---
name: visual-pr
description: Create or update a pull request.
---

# Describe a Pull Request

Create or update the pull request for the current task with a concise description that helps a reviewer understand why the change exists and the outline of the implementation.

Resolve `{SKILLBASE}` to the directory containing this file and `{REPO_ROOT}` to the repository root.

## Workflow

1. Read the description template:

   `{REPO_ROOT}/.github/pull_request_template.md`

2. Identify or create the pull request:
   - Check the current branch for a PR with `gh pr view --json url,number,title,state,baseRefName,headRefName 2>/dev/null`.
   - If no PR exists, inspect `git status --short --branch` and the commits on the current branch.
   - Commit task-related changes when needed, push the branch with an upstream, and create a PR for it. Follow the repository's git safety protocol.
   - Ask the user to select a PR only when the current branch has no relevant work and there is no safe current-branch PR to create.

3. Gather only the context needed to explain the change:
   - Read the ticket and any relevant task artifacts.
   - Read the complete PR diff and enough surrounding code to understand behavior and ownership.
   - Use `gh pr view` to collect PR metadata and changed files.
   - Read `{SKILLBASE}/references/change_outline.md` for the visual-outline conventions used in the PR body.

4. Write the PR description using the template:
   - Start the PR body with `## Description`.
   - End every PR description with a horizontal rule and the exact footer: `🤖 This PR description was generated with an LLM.`
   - When the PR resolves a known issue, put `Resolves [#N](issue-url)` first within **Description**, followed by a blank line and exactly one sentence explaining the problem and resulting benefit. Omit the Resolves line when no issue is resolved; do not invent a link.
   - Put any other relevant links within **Description**, after the summary; do not add a link header above it.
   - Use this section order: **Description**, **Diff summary**, **Change outline**, **Special things to note**, **Validation**.
   - Write in plain, human-friendly language. Explain concrete behavior and avoid formal or obscure wording.
   - Give **Diff summary** its own level-two section. Show the changed-file count and overall additions/deletions above a simple Markdown table with exactly `Category`, `🟩 Added`, and `🟥 Removed` columns. Use rows for shared code and affected runtimes, plus Tests, Docs, Config, and Lockfile where applicable. Do not prefix service names with “Source”. Show `+N` additions, `−N` deletions, and `0` for zero changes, followed by a bold Total row. Calculate counts from the current PR diff, count each line once, and keep generated lockfiles separate from Config. Count all test and documentation files under Tests and Docs, including service-local files. Do not add charts, images, or custom HTML for the diff summary.
   - Keep **Special things to note** to 1-3 bullets. Prioritize reviewer warnings, migrations, compatibility constraints, deliberate omissions, or surprising decisions. Write `- None.` when there are no special considerations.
   - Make **Change outline** a structural view with enough detail to explain the changed behavior, inputs, outputs, decisions, and service boundaries. Use short, plain-language annotations; avoid a file-by-file changelog.
   - Include only the views that help explain this PR:
     - A shallow file tree showing changed responsibilities.
     - CLI, schema, or storage contract changes.
     - A data flow or sequence showing which component owns each recovery step.
   - Prefer `diff` blocks when showing changes to an existing shape. Show the complete target shape when most of it is new or diff notation would obscure ownership or order.
   - Keep each view focused on what a reviewer needs. Omit categories that did not change.
   - Give **Validation** its own final section. Summarize the checks and results in one or two short paragraphs. Highlight failures, warnings, and anything unverified. Include relevant commands only when useful or required by the repository; avoid a bullet list of every routine test command. Do not mix validation results into **Change outline**.

5. Publish the description:
   - Do not save PR-description Markdown files inside the repository, including ignored directories such as `.humanlayer` or `.agent`.
   - Write the exact UTF-8 description to a uniquely named temporary file in the operating system's temporary directory, outside the repository, using `mktemp` or an equivalent temporary-file API.
   - Update the PR with `gh pr edit {number} --body-file {temporary-path}`; use the same approach with `gh pr create` when creating the PR.
   - Read the PR body back with `gh pr view` to confirm the description was saved correctly on GitHub.
   - Remove the temporary file after successful verification. If publishing fails, retain it only as needed to retry and report the failure; do not move it into the repository.

6. Report completion:
   - Report the PR URL, the material changes, and any remaining validation. Do not include a local saved-description link; the description lives on GitHub.

Always read and follow `{REPO_ROOT}/.github/pull_request_template.md`. Do not expand the PR body beyond that template.

Write as one human talking to another: avoid jargon and slang, and use simple, coherent, concise language.

## Reference

This skill was originally taken from [HumanLayer’s visual-pr skill](https://github.com/humanlayer/skills/blob/main/plugins/visual-pr/skills/visual-pr/SKILL.md) and adapted for this repo.
