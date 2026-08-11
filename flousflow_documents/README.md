# Flous Flow Documents

Standalone **document management** module for **Odoo 19 Community**, functionally
equivalent to the Enterprise *Documents* app (built as an original
implementation — no proprietary code copied).

## Features

### M1 — Core
- **Folders are documents** — a folder is a record of `flousflow.document` with
  `type='folder'`, arranged in a tree via `parent_path`.
- **Files & URLs** — upload binary attachments (auto-creates `ir.attachment`,
  keeps version history) or save external links.
- **Permission model** — computed `user_permission` (Editor / Viewer / None)
  driven by:
  - folder hierarchy inheritance (`access_internal`, `none` = inherit),
  - document owner override,
  - per-partner sharing with roles and expiration (`flousflow.document.access`),
  - manager group override.
- **Record rules** — global read/create/write rules plus a base write+unlink
  rule and a manager rule, mirroring the Enterprise behaviour (least privilege).
- **Tags** — colored, ordered, with tooltip.
- **Favorites** — per-user starred documents.
- **Link to any record** — `res_model` / `res_id` (Many2oneReference).
- **Multi-company** safe (`_check_company_auto`).
- **Chatter & activities** — `mail.thread` + `mail.activity.mixin`, optional
  auto-created activity on upload.
- **Default folder structure** — Inbox, Admin, Finance (+Bank/Cash/Purchase/
  Sales/Taxes/Annual Closing/Social/Miscellaneous), Legal (+Insurances/Loans/
  Registrations/Contracts), Projects, Marketing, Products.

### M2 — Sharing & operations
- **Share wizard** (`flousflow.document.sharing`) — share documents with
  partners (role view/edit), internal + link access, sharing audit rows.
- **Public link** — controller `/flousflow/documents/<id>` downloads a file with
  a valid token (200), 404 otherwise.
- **Move / Copy** wizard (`flousflow.document.operation`) — move to another
  folder, or copy (duplicates the attachment).
- **Request a file** wizard — creates a placeholder document + activity.
- **Link to record** wizard — binds a document to any model/record.

### M3 — Native kanban view (matching the original Documents app)
- The Documents app opens a **native kanban view** (`o_documents_view`), exactly
  like the original: preview thumbnail, favourite star, document name, activity
  / lock indicators, owner avatar, a muted description line and coloured tag
  badges.
- **Folders** are filtered through the **search panel** (a "Folders" facet,
  `icon="fa-folder"`) instead of a custom sidebar.
- Image files show a real preview thumbnail (`preview_src` data-URI field);
  other types show a file-type icon.
- List view available via the view switcher (kanban / list / activities).
- No custom OWL client action is used anymore — everything is native Odoo
  (removed in 19.0.1.1.0).

### M4 — Lock, email alias, portal
- **Lock / Unlock** (checkout) — `action_lock` / `action_unlock` on documents,
  lock icon on cards, Lock/Unlock button in the detail panel; only the locker
  or a manager may unlock.
- **Email alias** on folders — `mail.alias` created per folder
  (`_create_alias`), email address `alias_name@domain`, documents created from
  incoming emails via `message_new` (first attachment becomes the file).
- **Portal** — `/my/documents` page listing the documents shared with the
  current partner, with download links (token-protected).

### M5 — Trash, sections & unified New menu
- **Trash** — soft delete (`action_move_to_trash` / `action_restore` /
  `action_delete_permanently`) with a configurable deletion delay
  (Settings → Documents → Deletion delay) and a daily cron that purges
  expired items. A dedicated **Trash** menu action shows trashed documents
  with Restore / Delete buttons (matching the original Trash section).
  **Delete Forever asks for an explicit confirmation** (a transient wizard)
  before permanently deleting, matching the original app and protecting
  against accidental data loss.
- **Sections** — My Documents / Shared with me / Favorites / Recent search
  filters in the search view.
- **Unified New menu** — Upload / Link / Request / Folder control-panel
  buttons (native Odoo view buttons, `display="always"`), matching the
  original "New" menu.
- **Edit-gated header actions** — Share / Move-Copy / Link-to-Record /
  Request-a-file / Move-to-Trash / Lock are hidden for users whose
  `user_permission != 'edit'` (mirrors the original Documents app, where
  read-only documents don't expose editing actions).

### UI verification (from the web client)
All major flows verified end-to-end in the browser against a native kanban
view: card click → full form; New menu dialogs (Upload / Link / Request /
Folder); Trash cycle (move → Trash menu → restore → confirmed permanent
delete); Share wizard (internal rights + partner invites); favorites toggle
and the Favorites / Recent / My Documents filters; Lock / Unlock; Move-Copy,
Request-a-file and Link-to-record wizards; portal `/my/documents` page with
token-protected downloads. Full test suite: **38/38 passing**.

### Arabic translation (i18n)
The module ships with a full **Arabic (ar_001)** translation applied on
install via a post-init hook (`hooks.py` → `_install_arabic_translations`),
following the Odoo 19 JSONB translation pattern (source stays English, Arabic
is merged into the JSONB columns — there is no `ir.translation` table in 19):
- **Fields** — `ir_model_fields.field_description` (119 labels).
- **Views** — `ir_ui_view.arch_db` (17 views: `string=`, `placeholder=` and
  kanban/portal text nodes).
- **Selections** — `ir_model_fields_selection.name` (43 values).
- **Menus** — `ir_ui_menu.name` (7 menus).
- **Python `_()` terms** — `i18n/ar_001.po` (action titles, error messages,
  wizard labels) marked with the `#. odoo-python` comment so `_()` resolves
  them at runtime.

The `post_init_hook` runs on install; for an already-installed database the
same function can be invoked through the Odoo shell (see hooks docstring).

## Models

| Model | Purpose |
|-------|---------|
| `flousflow.document` | Documents, folders and URLs (single model) |
| `flousflow.document.tag` | Colored tags |
| `flousflow.document.access` | Per-partner sharing (role + expiration) |
| `flousflow.document.access.tracking` | Audit of permission changes |
| `flousflow.document.sharing` | Share wizard (documents + partners) |
| `flousflow.document.operation` | Move / Copy transient |
| `flousflow.document.request.wizard` | Request-a-file transient |
| `flousflow.document.link.to.record.wizard` | Link-to-record transient |
| `flousflow.document.delete.wizard` | Delete-forever confirmation transient |
| `flousflow.document.mixin` | Abstract mixin to create docs from other records |

## Security

- Groups: **Documents / User** → **Administrator** → **System Administrator**
  (`res.groups.privilege` based, Odoo 19 style).
- Record rules all rely on the computed `user_permission` field (non-stored,
  with a `search` helper) — the same architecture as Enterprise.

## Install / Upgrade

```bash
# Install
docker exec odoo_clean_web odoo --db_host=db --db_user=odoo --db_password=odoo -i flousflow_documents -d aaa --stop-after-init

# Upgrade after changes
docker exec odoo_clean_web odoo --db_host=db --db_user=odoo --db_password=odoo -u flousflow_documents -d aaa --stop-after-init

# Tests (use a non-conflicting HTTP port if the web server is running)
docker exec odoo_clean_web odoo --db_host=db --db_user=odoo --db_password=odoo --http-port=8187 --test-enable -u flousflow_documents -d test --stop-after-init
```

## Notes

- **Portal page**: `/my/documents` (auth='user') — lists documents shared with
  the current partner. The QWeb template lives in `views/portal_templates.xml`.
- **Email alias**: a folder gets a `mail.alias` via the *Create email alias*
  button on the folder form; incoming emails create documents in that folder.
- **Lock**: a locked document shows a lock icon; only the locking user or a
  documents manager can unlock it.

## Roadmap

- M2 — sharing wizard, bulk operations, request-a-file, link-to-record wizard
- M3 — custom OWL Drive-like UI
- M4 — email alias upload, portal, lock/unlock, HR redirect
- M5 — pluggable AI sorting

## License

LGPL-3 — Flous Flow.
