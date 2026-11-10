---
name: create-issue
description: Draft, create, or rewrite GitHub issues.
---

# Create Issue

Write issues that make the purpose, proposed changes, and completion conditions easy to understand. Apply these standards when creating an issue or rewriting a description; change only the issues the user requests.

## Gather context and respect the requested scope

- Read the user's requirements and relevant repository guidance. When updating an existing issue, read its current title, full description, and comments first.
- Verify related issue titles, numbers, and relationships before linking them. Preserve agreed requirements and decisions, including later refinements. Read referenced design discussions when available; distinguish unresolved choices from decisions already made.
- If the user asks to align, iterate, or review a draft first, show it in the conversation and wait before publishing. If they explicitly authorize creation or an update, proceed within that scope without requesting the same approval again.
- This skill describes issues. It does not authorize implementation, commits, pull requests, project creation, or changes to unrelated issues.

## Writing standards

### Description

- Use plain, concrete language. Prefer actual names such as `package.json` or `pyproject.toml` over terms such as "manifest." Explain necessary unfamiliar terms briefly.
- Keep Description to a short paragraph explaining the problem and intended outcome. Use short sentences; split dense descriptions rather than packing into one sentence. Focus on the intended behavior rather than rejected proposals or editing history.

### Related issues

- Put Related issues immediately after Description, before Architecture and Implementation outline. Use a two-column table: `Relationship` and `Issue`.
- Use exactly three rows in Related issues, in this order: `Parent`, `Previous`, `Next`. Link to verified issue titles and leave cells blank when no relationship exists. For a feature in a phased roadmap, Parent links to the phase parent and must match its native GitHub parent; leave Parent blank only for phase parents or genuinely standalone issues.
- For feature sub-issues, Previous lists actual prerequisite issues and Next lists their direct dependents within the phase. Allow multiple links in a cell when work branches or joins; do not imply that parallel features depend on one another. Keep necessary cross-phase prerequisites explicit in the outline or acceptance criteria. For phase parents, Previous and Next show the phase order; explain work that can start in parallel.
- Do not add GitHub built-in blocking links or separate "Blocked by" or "Execution order" headings unless explicitly requested.

### Architecture

- Use a separate Architecture section for the relevant components, execution/data flow, and ownership boundaries. Keep it distinct from the implementation steps.

### Implementation outline

- Begin Implementation outline with a File tree subsection, followed by numbered steps for the proposed behavior. Keep the tree shallow and include only relevant paths and short responsibility comments.
- Use a `diff` fence for the file tree: prefix additions with `+`, actual removals with `-`, and leave modified files uncolored with comments describing the change. Do not mark modified files as removed and re-added. Keep color legends and formatting explanations out of the issue body.
- Give material code changes concrete sketches in the repository’s language, showing the relevant classes/functions, calls, and boundaries. Put the repository-relative file path in a comment at the top of each code block, without file-reading commands. Use a `text` fence for HTTP examples containing path comments.
- Ground sketches in the repository and installed library APIs. Identify proposed symbols and unresolved connections briefly; leave unverified integration points open instead of inventing helpers, defaults, policies, or lifecycle decisions. Show a complete target shape for new code and enough surrounding context for existing code to make ownership clear.
- Keep prose next to the sketch it explains.

### Acceptance criteria

- Write acceptance criteria as unchecked, observable conditions. Keep each criterion focused and verifiable. Do not mark criteria complete merely because a description was generated or edited.
- End the description with a horizontal rule and this exact attribution: `🤖 This issue description was generated with an LLM.`

## Issue structure

Use the following section order. Adapt the outline to the work; omit Architecture or the file tree only when there is no meaningful architecture or file-layout change to show.

````markdown
## Description

{A short paragraph describing the problem and intended outcome in short sentences.}

## Related issues

| Relationship | Issue |
|---|---|
| Parent | [{Verified phase parent title}]({Parent issue URL}) |
| Previous | [{Verified prerequisite title}]({Issue URL}) |
| Next | [{Verified dependent title}]({Issue URL}) |

## Architecture

```text
{Components and their execution/data flow.}
```

{Brief explanation of ownership and service boundaries.}

## Implementation outline

### File tree

```diff
 src/
   service.py       # Extend existing behavior
+  handler.py       # New request handling
```

### 1. {Concrete implementation step}

```python
# src/service.py

{Focused code sketch using the repository's language and APIs.}
```

{Brief explanation of behavior and any unresolved integration point.}

### 2. {Next implementation step}

{File-specific sketch or contract, with only the explanation needed to understand it.}

## Acceptance criteria

- [ ] {An observable completion condition.}
- [ ] {Another observable completion condition.}

---

🤖 This issue description was generated with an LLM.
````

## Phased roadmaps

When the user organizes work by phases:

- Give every phase its own parent issue titled `[Parent]: Phase N - Short description of the phase`, for example `[Parent]: Phase 1 - Repository scaffolding and architecture`.
- Title implementation sub-issues `[Feature]: Short descriptive title`. Use `[Bug]: ...` for defects and `[Task]: ...` for other work when appropriate; do not create bugs or tasks just to fill categories. Do not include phase numbering in child titles: their parent establishes the phase.
- Create actual GitHub parent/sub-issue relationships, and mirror the parent in the child's Related issues table. Reuse existing phase issues and features when reorganizing a roadmap; preserve issue numbers, requirements, comments, and project membership.
- Keep deferred work and out-of-scope follow-ups on the parent rather than repeating them in feature issues. When authorized to move them, preserve their requirements and align parent wording with the agreed feature scope.
- Keep phase scope and phase acceptance criteria on the parent. A later phase can remain a parent awaiting a focused feature breakdown; preserve its full scope and exit criteria without inventing implementation details or presenting it as ready to implement.
- Use feature-level Previous/Next links for dependencies within each phase, preserving parallel work. Do not manufacture dependencies merely to create a linear list.
- Keep parent issues open until their feature sub-issues and phase acceptance criteria are complete. Reopen superseded phase references when explicitly restoring them as active parents; do not reopen completed work without a reason.
- Label feature issues `feature`. Do not introduce phase, area, technology, or `ready-for-agent` labels unless requested. Preserve unrelated labels when the request is only a description edit.
- Do not create milestones or assign a GitHub project merely because issues are phased; follow the user's explicit organizational choices.
- When also authorized to update a PR, link its `Resolves` line to the specific feature, bug, or task it completes. Do not automatically close the entire phase parent. Check that any links use the updated titles.

For standalone issues, use the appropriate `[Feature]:`, `[Bug]:`, or `[Task]:` prefix with a concise outcome-focused title; do not invent a phase parent.

## Publish and verify

- Use an available GitHub connector or the authenticated `gh` CLI. Resolve the target repository from the user's request or the current repository; do not guess a destination when it is ambiguous.
- For CLI publication, write the exact Markdown to a UTF-8 temporary file outside the repository and use `gh issue create --body-file` or `gh issue edit --body-file`. Preserve actual newlines and literal diagram text.
- After publication, read the issue back to verify the description, section order, related links, and single attribution footer were saved correctly. Verify requested labels separately. When the user authorizes removing native blocking links, confirm their removal without adding dependency rows to Related issues.
- Verify native sub-issues as well as body links: each feature has the intended parent, and the parent lists the expected features. Keep native blocking links separate from this hierarchy. Remove temporary draft files after successful verification.
- Report the issue URL and a short description of the change. If publication fails, keep the prepared draft and state the concrete blocker rather than claiming success.

