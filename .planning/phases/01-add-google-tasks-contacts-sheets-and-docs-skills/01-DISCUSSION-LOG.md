# Phase 1: Add Google Tasks, Contacts, Sheets, and Docs skills - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-22
**Phase:** 01-add-google-tasks-contacts-sheets-and-docs-skills
**Areas discussed:** Scope boundaries, Subcommand design

---

## Scope Boundaries

### Sheets Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Data only (Recommended) | Read/write cell values by range (A1 notation). No formatting, charts, or formulas. | ✓ |
| Data + create | Read/write values plus create new spreadsheets. Still no formatting. | |
| Full CRUD + formatting | Full read/write/create plus bold, colors, borders. Much more complex. | |

**User's choice:** Data only
**Notes:** Covers 90% of AI agent use cases.

### Docs Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Read text + create (Recommended) | Read document as plain text. Create new docs with plain text content. | |
| Read only | Just extract text content from existing docs. | |
| Read + write + append | Read text, create docs, and append text to existing docs. Still no formatting. | ✓ |

**User's choice:** Read + write + append
**Notes:** None

### Contacts Depth

| Option | Description | Selected |
|--------|-------------|----------|
| List + search + get (Recommended) | Read-only — agents typically look up contacts, not create them. | |
| Full CRUD | List, search, get, create, update, delete contacts. | ✓ |
| Read + create | List, search, get, plus create new contacts. No update/delete. | |

**User's choice:** Full CRUD
**Notes:** None

### Tasks Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Full CRUD (Recommended) | List task lists, list tasks, create, complete, update, delete. | ✓ |
| Read + create + complete | List, create, and mark complete. No update or delete. | |

**User's choice:** Full CRUD
**Notes:** Tasks API is simple enough to go all-in.

---

## Subcommand Design

### Tasks CLI — Task List Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Flat with --list flag | All subcommands at top level with --list flag to target specific list. | |
| Nested subcommands | Separate 'lists' subcommand group: 'tasks lists' and 'tasks list/create/complete/delete'. | ✓ |
| Default list only | Only operate on the default task list. Ignore multi-list support. | |

**User's choice:** Nested subcommands
**Notes:** None

### Sheets CLI

| Option | Description | Selected |
|--------|-------------|----------|
| read + write + list (Recommended) | list, read SPREADSHEET_ID RANGE, write SPREADSHEET_ID RANGE --values. | |
| read + write + list + create | Same as above plus 'create --title NAME'. | ✓ |
| get + set + list | Renamed: 'get' instead of 'read', 'set' instead of 'write'. | |

**User's choice:** read + write + list + create
**Notes:** None

### Docs CLI

| Option | Description | Selected |
|--------|-------------|----------|
| read + create + append + list (Recommended) | list, read DOC_ID, create --title --body, append DOC_ID --body. | ✓ |
| Same but 'get' instead of 'read' | claws docs get DOC_ID. | |

**User's choice:** read + create + append + list
**Notes:** None

### Contacts CLI

| Option | Description | Selected |
|--------|-------------|----------|
| list + search + get + create + update + delete (Recommended) | Full suite with --name/--email/--phone flags. | ✓ |
| Combine list and search | Single 'list' command with optional --query flag. | |

**User's choice:** Full suite
**Notes:** None

---

## Claude's Discretion

- Error handling patterns (follow existing handle_*_error convention)
- API base URLs and endpoint paths
- Internal helper function structure
- Test structure and coverage

## Deferred Ideas

None — discussion stayed within phase scope
