# Self-evolving skills

TissueAgent's knowledge optimizer analyzes saved runs for execution failures, missing input/output contracts, retries, and avoidable token use. It turns those findings into edits to existing skills and plan templates, so future runs avoid problems with past runs. This pipeline is managed through the `tissueagent optimize` CLI command.

## Usage

Run from the repository checkout with TissueAgent installed and model credentials configured. Supply one or more session directories containing `.chat.json` (normally `projects/<id>/` under the [state root](../README.md#state-and-output-locations)) and a focus for the review:

```bash
tissueagent optimize \
  --sessions /path/to/projects/run-a /path/to/projects/run-b \
  --focus "Reduce repeated preprocessing failures and clarify artifact paths" \
  --propose-only
```

The optimizer summarizes the sessions, inspects traces and available artifacts or metrics, and proposes targeted text replacements. Each round writes a report with diffs, findings, and token usage to `optimizer_reports/` in the repository.

`--propose-only` temporarily applies edits for validation, then reverts them at the end of the round. Review the report and manually apply accepted diffs if you want to preserve those exact proposals. Running again without this flag starts a new optimization round, applies its edits, and commits the edited files and report by default.

| Option | Purpose |
| --- | --- |
| `--no-commit` | Apply edits but leave them uncommitted for review |
| `--model <id>` | Override the configured model |
| `--max-iterations <n>` | Limit tool-loop iterations (default: 40) |

## Scope and validation

The optimizer can edit existing Markdown files under `knowledge/skills/` and `knowledge/plans/`, excluding Code, bundled `scripts/`, and `references/`. Each round permits up to 12 edits, with a 4,000-character limit on the combined old and new text per edit.

After each edit, the knowledge registry is checked for frontmatter errors and duplicate enabled names. Edits that break these checks are reverted. Evaluate accepted changes on relevant analysis runs before relying on them.

Implementation: [optimizer package](../src/optimizer/). The [optimizer context](OPTIMIZER_CONTEXT.md) contains the model's architecture background and editing guidance.
