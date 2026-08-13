{
    "name": "Flous Flow Documents",
    "version": "19.0.1.1.1",
    "category": "Productivity/Documents",
    "summary": "Folders, files and URLs with granular permissions, sharing, favorites, trash and portal — for Odoo 19 Community",
    "description": """
Flous Flow Documents
====================

A standalone document management module for Odoo 19 Community, functionally
equivalent to the Enterprise Documents app (built as an original
implementation, not a copy of proprietary code).

Features:
- Folders are documents (type='folder') with a parent_path tree
- Upload files (binary) or save URLs
- Hierarchical permission inheritance (view/edit/none) with owner override
- Per-partner sharing with roles and expiration (documents.access)
- Colored tags, favorites, multi-company
- Link any document to any Odoo record (res_model/res_id)
- Computed user_permission field + record rules for least-privilege access
- Activity mixin + chatter for audit
- Default folder structure (Inbox, Finance, Legal, Projects, ...)
- Sharing wizard, bulk move/copy, request-a-file wizard, link-to-record wizard
- Native kanban view (preview thumbnails + tags + owner) + Folders search panel
- Email alias on folders, portal page, lock/unlock (M4)
""",
    "author": "Flous Flow",
    "website": "https://flousflow.com",
    "support": "support@flousflow.com",
    "license": "LGPL-3",
    "icon": "flousflow_documents/static/description/icon.png",
    "depends": [
        "base",
        "mail",
        "web",
        "contacts",
        "portal",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/folders.xml",
        "data/cron.xml",
        "views/document_views.xml",
        "views/tag_views.xml",
        "views/wizard_views.xml",
        "views/portal_templates.xml",
        "views/settings_views.xml",
        "views/menus.xml",
    ],
    "demo": [],
    "assets": {
        "web.assets_backend": [
            "flousflow_documents/static/src/documents/documents_kanban.scss",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "post_init_hook": "_install_arabic_translations",
    "images": [
        "static/description/cover.png",
        "static/description/screenshot_kanban.png",
        "static/description/screenshot_form.png",
        "static/description/screenshot_share.png",
        "static/description/screenshot_trash.png",
        "static/description/screenshot_portal.png",
    ],
}
