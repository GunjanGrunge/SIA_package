# Optional SIA Attribution

SIA attribution is an explicit, project-level choice. It credits the workflow
without taking authorship away from the human maintainer. Ask this question in
the first Intake batch, record the answer in the project `AGENT.md`, and do
nothing until the user has chosen one of these modes:

```text
SIA attribution: none | README badge | commit trailers | both
```

`none` is the default when the user does not answer. A user may change the
selection later; record the new choice and its date rather than rewriting
history.

## Modes

### None

Do not add an attribution section, badge, asset, commit trailer, Git config,
or GitHub integration. SIA's project artifacts may still exist because they
are the project's own operational history, not marketing.

### README badge

With explicit approval to edit or create the project's README, add this
compact, clickable badge near the top. Preserve the repository's existing
style and place it with other badges if they already exist.

```markdown
[![Powered by SIA — Self-Improving Agents](https://img.shields.io/badge/Powered%20by-SIA%20%E2%80%94%20Self--Improving%20Agents-007BFF?style=flat-square)](https://github.com/GunjanGrunge/SIA_package)
```

If the project has no README, ask whether the user wants SIA to create one;
do not create a README only to place a badge. If the repository uses local
brand assets, the user may also approve a small SIA mark linked to the public
package. Never overwrite the project's branding, ownership statement, or
existing badges.

### Commit trailers

For every **SIA-mediated commit** after the user chooses this mode, preserve
the configured human Git author and committer exactly as the human/host
supplied them. Add these trailers to the commit message body instead:

```text
Assisted-by: SIA — Self-Improving Agents
SIA-Run: <relative path to the relevant sdd/ report or session log>
```

Use a real, committed project-relative evidence path in `SIA-Run`; omit that
line only if no such evidence exists and report the missing evidence as a
DEVIATION. Do not use `Co-authored-by` for SIA, fabricate a GitHub identity,
change `user.name`/`user.email`, amend prior commits, or add trailers to a
commit the user made outside an SIA-mediated task. GitHub will show these
trailers in the commit body after the user pushes the commit; SIA does not
need a GitHub App or token to do this.

### Both

Apply the README badge once, with the same approval and preservation rules,
then use commit trailers for later SIA-mediated commits.

## Required Project Record

The generated project `AGENT.md` must contain this section when attribution
has been discussed:

```markdown
## SIA Attribution

Mode: <none | README badge | commit trailers | both>
Chosen: <ISO-8601 date>
README status: <not requested | pending approval | added at path | not applicable>
Commit-trailer rule: <not enabled | exact trailer format above>
```

The project's generated operating skill and `sdd/skill-manifest.md` must name
the selected mode. This lets a later host follow the choice without guessing.

## Execution and Review

Treat a README change as an ordinary, owned documentation task: name the exact
README and any asset in the plan/brief, review the rendered Markdown, and
commit it only after the user-approved attribution choice. Before an
SIA-mediated commit, verify that the chosen mode and `SIA-Run` evidence path
match the project record. Attribution is never a substitute for verification,
human approval, or the execution evidence gate.
