# -*- coding: utf-8 -*-
"""FlousFlow Documents — main document model.

Folders, files and URLs are all records of this model (type='folder').
The permission system mirrors the Odoo Enterprise Documents behaviour:
a computed `user_permission` field (edit/view/none) drives global record
rules, with owner override and per-partner sharing.
"""

import mimetypes
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_PERM_LEVEL = {'none': 0, 'view': 1, 'edit': 2}


class FlousflowDocument(models.Model):
    _name = 'flousflow.document'
    _description = 'Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'
    _check_company_auto = True
    _parent_name = 'folder_id'
    _parent_store = True

    # ------------------------------------------------------------------
    # Type & identity
    # ------------------------------------------------------------------
    type = fields.Selection(
        selection=[('url', 'URL'), ('binary', 'File'), ('folder', 'Folder')],
        string='Type', required=True, default='binary', tracking=True,
    )
    name = fields.Char(string='Name', required=True, tracking=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    # Folder accent color (0-11, Odoo standard palette) — used by the Drive UI
    # exactly like the original Documents app colours folders in the tree.
    color = fields.Integer(string='Color', default=0)

    # ------------------------------------------------------------------
    # Tree (folders are documents)
    # ------------------------------------------------------------------
    folder_id = fields.Many2one(
        'flousflow.document', string='Folder',
        domain="[('type', '=', 'folder')]",
        index=True, ondelete='cascade', check_company=True, tracking=True,
    )
    parent_path = fields.Char(index=True, copy=False)
    children_ids = fields.One2many(
        'flousflow.document', 'folder_id', string='Children', copy=False,
    )

    # ------------------------------------------------------------------
    # File content
    # ------------------------------------------------------------------
    attachment_id = fields.Many2one(
        'ir.attachment', string='Attachment', ondelete='restrict', copy=False,
    )
    datas = fields.Binary(
        related='attachment_id.datas', string='File Content', readonly=False,
    )
    mimetype = fields.Char(related='attachment_id.mimetype', string='Mime Type', readonly=True)
    file_size = fields.Integer(related='attachment_id.file_size', string='File Size', readonly=True)
    checksum = fields.Char(related='attachment_id.checksum', string='Checksum/SHA1', readonly=True)
    index_content = fields.Text(related='attachment_id.index_content', string='Indexed Content', readonly=True)
    file_extension = fields.Char(string='File Extension', compute='_compute_file_extension')
    previous_attachment_ids = fields.Many2many(
        'ir.attachment', 'flousflow_document_previous_attachment_rel',
        'document_id', 'attachment_id', string='History', readonly=True, copy=False,
    )
    current_revision_uuid = fields.Char(string='Current Revision UUID', copy=False, readonly=True)

    # URL type
    url = fields.Char(string='Link URL')
    url_preview_image = fields.Char(string='URL Preview Image')

    # ------------------------------------------------------------------
    # Access & permissions
    # ------------------------------------------------------------------
    owner_id = fields.Many2one('res.users', string='Owner', index=True, tracking=True)
    access_internal = fields.Selection(
        selection=[('view', 'Viewer'), ('edit', 'Editor'), ('none', 'None')],
        string='Internal Users Rights', default='none', required=True,
    )
    access_via_link = fields.Selection(
        selection=[('view', 'Viewer'), ('edit', 'Editor'), ('none', 'None')],
        string='Link Access Rights', default='none', required=True,
    )
    is_access_via_link_hidden = fields.Boolean(string='Link Access Hidden')
    access_ids = fields.One2many(
        'flousflow.document.access', 'document_id', string='Allowed Access',
    )
    access_token = fields.Char(string='Document Token', copy=False, default=lambda self: self._generate_access_token())
    access_url = fields.Char(string='Access URL', compute='_compute_access_url', readonly=True)
    lock_uid = fields.Many2one('res.users', string='Locked by', copy=False, readonly=True)
    # Request-a-file tracking (a request document has no attachment yet)
    request_activity_id = fields.Many2one('mail.activity', string='Request Activity', copy=False)
    requestee_partner_id = fields.Many2one('res.partner', string='Requestee Partner', copy=False, index=True)

    # ------------------------------------------------------------------
    # Trash (soft delete, auto-purge after configurable delay)
    # ------------------------------------------------------------------
    trashed = fields.Boolean(string='In Trash', default=False, index=True)
    trash_date = fields.Datetime(string='Trash Date', copy=False)
    deletion_date = fields.Datetime(string='Scheduled Deletion', copy=False)
    # "Recent" helper for the search panel section (last 30 days)
    is_recent = fields.Boolean(string='Recent', compute='_compute_is_recent',
                               search='_search_is_recent')

    # ------------------------------------------------------------------
    # Email alias (upload documents to a folder by email) — M4
    # ------------------------------------------------------------------
    alias_id = fields.Many2one(
        'mail.alias', string='Email Alias', ondelete='restrict', copy=False,
    )
    alias_name = fields.Char(
        string='Alias Name', help='Local part of the folder email address, '
        'e.g. "invoices" for invoices@yourdomain.com',
    )
    alias_domain_id = fields.Many2one(
        'mail.alias.domain', string='Alias Domain', copy=False,
    )
    alias_domain = fields.Char(
        string='Alias Domain Name', related='alias_id.alias_domain',
        readonly=True,
    )
    alias_email = fields.Char(
        string='Alias Email', compute='_compute_alias_email',
    )
    alias_tag_ids = fields.Many2many(
        'flousflow.document.tag', 'flousflow_document_alias_tag_rel',
        'document_id', 'tag_id', string='Tags applied to emailed documents',
    )

    # Computed permission fields (used by record rules + views)
    user_permission = fields.Selection(
        selection=[('edit', 'Editor'), ('view', 'Viewer'), ('none', 'None')],
        string='User permission', compute='_compute_user_permission',
        search='_search_user_permission', recursive=True,
    )
    user_folder_id = fields.Char(string='Parent', compute='_compute_user_folder_id')
    user_can_move = fields.Boolean(string='Can move it', compute='_compute_user_can_move')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    tag_ids = fields.Many2many(
        'flousflow.document.tag', 'flousflow_document_tag_rel',
        'document_id', 'tag_id', string='Tags',
    )
    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='set null', index=True)
    res_model = fields.Char(string='Resource Model', index=True, copy=False)
    res_id = fields.Many2oneReference(string='Resource', model_field='res_model', index=True, copy=False)
    res_name = fields.Char(string='Resource Name', compute='_compute_res_name')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company, index=True, ondelete='cascade',
    )

    # Favorites
    favorited_ids = fields.Many2many('res.users', string='Favorite of', copy=False)
    is_favorited = fields.Boolean(string='Is Favorited', compute='_compute_is_favorited', search='_search_is_favorited')

    # Kanban preview — a ready-to-use data URI for image files so the card can
    # show a real thumbnail (like the original Documents app preview). Other
    # types fall back to a file-type icon in the kanban template.
    preview_src = fields.Char(string='Preview Source', compute='_compute_preview_src')

    # ------------------------------------------------------------------
    # Activity auto-creation on upload
    # ------------------------------------------------------------------
    create_activity_option = fields.Boolean(string='Create a new activity')
    create_activity_type_id = fields.Many2one('mail.activity.type', string='Activity type')
    create_activity_summary = fields.Char(string='Summary')
    create_activity_note = fields.Html(string='Note')
    create_activity_user_id = fields.Many2one('res.users', string='Responsible')
    create_activity_date_deadline_range = fields.Integer(string='Due Date In')
    create_activity_date_deadline_range_type = fields.Selection(
        selection=[('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        string='Due type', default='days',
    )

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    @api.depends('name')
    def _compute_file_extension(self):
        for doc in self:
            doc.file_extension = False
            if doc.name and '.' in doc.name:
                doc.file_extension = doc.name.rsplit('.', 1)[-1].lower()

    @api.depends('access_token')
    def _compute_access_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for doc in self:
            doc.access_url = False
            if doc.access_token and doc.type != 'folder':
                doc.access_url = f'{base_url}/flousflow/documents/{doc.id}'

    @api.depends('type', 'attachment_id', 'mimetype')
    def _compute_preview_src(self):
        for doc in self:
            doc.preview_src = False
            if doc.type == 'binary' and doc.attachment_id and doc.mimetype \
                    and doc.mimetype.startswith('image/'):
                try:
                    datas = doc.attachment_id.with_context(bin_size=False).datas
                    if datas:
                        doc.preview_src = 'data:%s;base64,%s' % (
                            doc.mimetype, datas.decode('ascii'))
                except Exception:
                    doc.preview_src = False

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for doc in self:
            doc.res_name = False
            if doc.res_model and doc.res_id:
                try:
                    record = self.env[doc.res_model].browse(int(doc.res_id))
                    doc.res_name = record.exists().display_name or False
                except Exception:
                    doc.res_name = False

    @api.depends('alias_name', 'alias_domain')
    def _compute_alias_email(self):
        for doc in self:
            doc.alias_email = False
            if doc.alias_name and doc.alias_domain:
                doc.alias_email = f'{doc.alias_name}@{doc.alias_domain}'

    @api.depends('favorited_ids')
    def _compute_is_favorited(self):
        for doc in self:
            doc.is_favorited = self.env.uid in doc.favorited_ids.ids

    # ------------------------------------------------------------------
    # Email alias — M4
    # ------------------------------------------------------------------
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Create a document from an incoming email sent to a folder alias."""
        custom_values = dict(custom_values or {})
        attachments = msg_dict.get('attachments') or []
        if attachments:
            # first attachment becomes the document file
            first = attachments[0]
            if isinstance(first, (list, tuple)):
                filename, datas = first[0], first[1]
            else:
                filename = first.get('name', msg_dict.get('subject') or _('Email'))
                datas = first.get('datas')
            custom_values.setdefault('name', filename or _('Email'))
            custom_values.setdefault('datas', datas)
        else:
            custom_values.setdefault('name', msg_dict.get('subject') or _('Email'))
        custom_values.setdefault('type', 'binary')
        return super().message_new(msg_dict, custom_values)

    def _get_alias_name(self):
        """Default alias local part from the folder name."""
        self.ensure_one()
        import re
        base = re.sub(r'[^a-z0-9]+', '_', (self.name or '').lower()).strip('_')
        base = base or 'documents'
        # ensure uniqueness
        domain = self.alias_domain_id
        existing = self.env['mail.alias'].search([
            ('alias_name', '=', base),
            ('alias_domain_id', '=', domain.id if domain else False),
        ], limit=1)
        if existing and existing.alias_parent_thread_id != self.id:
            base = f'{base}_{self.id}'
        return base

    def _create_alias(self):
        """Create (or update) the mail.alias of a folder so documents can be
        uploaded by sending an email to the folder address."""
        for folder in self:
            if folder.type != 'folder':
                continue
            if not folder.alias_name:
                folder.alias_name = folder._get_alias_name()
            domain_id = folder.alias_domain_id.id or False
            model_id = self.env['ir.model']._get('flousflow.document').id
            vals = {
                'alias_name': folder.alias_name,
                'alias_parent_model_id': model_id,
                'alias_parent_thread_id': folder.id,
                'alias_model_id': model_id,
                'alias_force_thread_id': False,
                'alias_domain_id': domain_id,
                'alias_defaults': {
                    'folder_id': folder.id,
                    'type': 'binary',
                    'tag_ids': [(6, 0, folder.alias_tag_ids.ids)],
                },
            }
            if folder.alias_id:
                folder.alias_id.write(vals)
            else:
                folder.alias_id = self.env['mail.alias'].create(vals)
        return True

    def action_create_alias(self):
        """Button: create / refresh the folder email alias."""
        self.ensure_one()
        self._create_alias()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'flousflow.document',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    @api.model
    def _search_is_favorited(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            return [('id', 'in', [])]
        # A boolean condition is normalised by the ORM into an 'in' leaf
        # (e.g. `('is_favorited', '=', True)` becomes
        # `('is_favorited', 'in', [True])`) before the FULL optimization level,
        # so we must accept both scalar and collection values.
        if isinstance(value, bool):
            values = {value}
        else:
            try:
                values = {bool(v) for v in value}
            except TypeError:
                values = set()
        if not values:
            return [('id', 'in', [])]
        favorited = set(
            self.sudo().search(
                [('favorited_ids', 'in', [self.env.uid])]
            ).ids
        )
        # tautology: `in [True, False]` matches everything
        if values == {True, False}:
            return [('id', 'not in', [])] if operator in ('=', 'in') \
                else [('id', 'in', [])]
        want_favorited = True in values
        if operator in ('=', 'in'):
            if want_favorited:
                return [('id', 'in', list(favorited))]
            return [('id', 'not in', list(favorited))]
        # operator in ('!=', 'not in')
        if want_favorited:
            return [('id', 'not in', list(favorited))]
        return [('id', 'in', list(favorited))]

    # ------------------------------------------------------------------
    # Permission computation (the core of the module)
    # ------------------------------------------------------------------
    @api.depends(
        'type', 'owner_id', 'access_internal', 'access_via_link',
        'access_ids.partner_id', 'access_ids.role', 'access_ids.expiration_date',
        'folder_id.user_permission', 'folder_id.owner_id', 'folder_id.access_internal',
    )
    def _get_user_permission_for_record(self, doc, uid, partner, now, is_manager):
        """Compute the permission for ONE record from raw stored fields only.

        Used by BOTH `_compute_user_permission` and `_search_user_permission`.
        It never reads the computed `user_permission` field — that avoids a
        re-entrancy bug where the rule search (invoked while the field is
        being computed) would read the half-computed value and wrongly exclude
        records.
        """
        if is_manager:
            return 'edit'
        if doc.type == 'folder':
            return self._get_folder_user_permission(doc, uid, partner, now)
        if doc.owner_id and doc.owner_id.id == uid:
            return 'edit'
        folder_perm = self._get_folder_user_permission(doc.folder_id, uid, partner, now)
        own_perm = doc.access_internal
        if own_perm == 'none':
            # 'none' means "inherit from folder" — the folder permission applies
            permission = folder_perm
        else:
            # Explicit access on the document: the folder still constrains
            permission = self._min_permission(folder_perm, own_perm)
        # Per-partner sharing on the document itself overrides (grants access)
        for acc in doc.access_ids:
            if acc.partner_id.id == partner.id and (
                not acc.expiration_date or acc.expiration_date > now
            ):
                if acc.role == 'edit':
                    return 'edit'
                elif acc.role == 'view' and permission != 'edit':
                    permission = 'view'
        return permission

    @api.depends(
        'type', 'owner_id', 'access_internal', 'access_via_link',
        'access_ids.partner_id', 'access_ids.role', 'access_ids.expiration_date',
        'folder_id.user_permission', 'folder_id.owner_id', 'folder_id.access_internal',
    )
    def _compute_user_permission(self):
        user = self.env.user
        uid = user.id
        partner = user.partner_id
        # Real superuser (uid 1), settings admins and documents managers can
        # edit everything. NOTE: `with_user(user)` sets `env.su` to False, so
        # the superuser check must require uid == 1.
        is_manager = (
            (self.env.su and self.env.uid == 1)
            or user.has_group('flousflow_documents.group_documents_manager')
            or user.has_group('base.group_system')
        )
        now = fields.Datetime.now()
        for doc in self:
            doc.user_permission = self._get_user_permission_for_record(
                doc, uid, partner, now, is_manager
            )

    def _get_folder_user_permission(self, folder, uid, partner, now=None):
        """Effective permission granted by a folder chain.

        - Owner of any folder in the chain (or the folder itself) → edit.
        - A partner sharing row (role edit) on any folder → edit.
        - Otherwise the NEAREST folder (closest to the document) whose
          access_internal != 'none' wins; 'none' means inherit from parent.
        """
        if not folder:
            return 'none'
        now = now or fields.Datetime.now()
        current = folder
        while current:
            if current.owner_id and current.owner_id.id == uid:
                return 'edit'
            for acc in current.access_ids:
                if acc.partner_id.id == partner.id and (
                    not acc.expiration_date or acc.expiration_date > now
                ):
                    if acc.role == 'edit':
                        return 'edit'
            current = current.folder_id
        current = folder
        while current:
            if current.access_internal != 'none':
                return current.access_internal
            current = current.folder_id
        return 'none'

    def _min_permission(self, perm_a, perm_b):
        """Most restrictive of two permissions (none < view < edit)."""
        return perm_a if _PERM_LEVEL.get(perm_a, 0) <= _PERM_LEVEL.get(perm_b, 0) else perm_b

    @api.model
    def _search_user_permission(self, operator, value):
        """Search helper for `user_permission`, used by record rules and filters.

        Computes the ids the current user can edit/view and translates the
        operator into an `id in (...)`. Uses sudo to avoid record-rule
        recursion while computing.

        NOTE: Odoo 19 calls this during domain validation (ir.rule
        `_check_domain`) and may pass the value as an `OrderedSet`, so the
        value is normalised defensively (never wrapped into a set literal).
        """
        # Odoo 19 may pass the value as an OrderedSet (its own collection type,
        # NOT a subclass of `set`), so never wrap it into a set literal.
        if isinstance(value, str):
            values = {value}
        else:
            try:
                values = {v for v in value if isinstance(v, str)}
            except TypeError:
                values = set()
        # Only the operators used by our rules/filters are supported.
        if operator not in ('=', '!=', 'in', 'not in'):
            return [('id', 'in', [])]

        user = self.env.user
        uid = user.id
        partner = user.partner_id
        is_manager = (
            (self.env.su and self.env.uid == 1)
            or user.has_group('flousflow_documents.group_documents_manager')
            or user.has_group('base.group_system')
        )
        if is_manager:
            # Manager: edit on everything
            all_ids = set(self.sudo().search([], order='id').ids)
            if operator in ('=', 'in'):
                if values & {'edit'}:
                    return [('id', 'in', list(all_ids))]
                return [('id', 'in', [])]
            # operator != / not in
            if values & {'edit'} and len(values) == 1:
                return [('id', 'in', [])]
            return [('id', 'in', list(all_ids))]

        docs = self.sudo().search([], order='id')
        # Prefetch the raw fields so the whole permission computation reads
        # from cache and NEVER touches the computed `user_permission` field
        # (that access would re-enter this method recursively).
        docs.read(['type', 'owner_id', 'access_internal', 'folder_id', 'access_ids'])
        now = fields.Datetime.now()
        edit_ids = set()
        view_ids = set()
        for doc in docs:
            perm = self._get_user_permission_for_record(doc, uid, partner, now, is_manager)
            if perm == 'edit':
                edit_ids.add(doc.id)
            elif perm == 'view':
                view_ids.add(doc.id)
        all_ids = set(docs.ids)
        none_ids = all_ids - edit_ids - view_ids

        if operator in ('=', 'in'):
            if values == {'edit'}:
                allowed = edit_ids
            elif values == {'view'}:
                allowed = view_ids
            elif values == {'none'}:
                allowed = none_ids
            else:
                allowed = set()
                if 'edit' in values:
                    allowed |= edit_ids
                if 'view' in values:
                    allowed |= view_ids
                if 'none' in values:
                    allowed |= none_ids
        else:  # operator in ('!=', 'not in')
            allowed = all_ids
            if 'edit' in values:
                allowed -= edit_ids
            if 'view' in values:
                allowed -= view_ids
            if 'none' in values:
                allowed -= none_ids
        return [('id', 'in', list(allowed))]

    @api.depends('folder_id', 'folder_id.name')
    def _compute_user_folder_id(self):
        for doc in self:
            doc.user_folder_id = doc.folder_id.name or ''

    @api.depends('user_permission', 'folder_id.user_permission', 'type')
    def _compute_user_can_move(self):
        for doc in self:
            doc.user_can_move = (
                doc.user_permission == 'edit'
                and (not doc.folder_id or doc.folder_id.user_permission == 'edit')
            )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model
    def _generate_access_token(self):
        return self.env['ir.attachment']._generate_access_token()

    @api.model_create_multi
    def create(self, vals_list):
        # Auto-assign a folder colour (cycles the standard 0-11 palette).
        folder_count = self.search_count([('type', '=', 'folder')])
        for vals in vals_list:
            if vals.get('type') == 'folder' and 'color' not in vals:
                vals['color'] = folder_count % 12
                folder_count += 1
        for vals in vals_list:
            datas = vals.pop('datas', None)
            if vals.get('type') == 'binary':
                if not vals.get('name') and datas:
                    vals['name'] = _('Document')
                if datas and vals.get('name'):
                    filename = vals['name']
                    mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                    attach_vals = {
                        'name': filename,
                        'datas': datas,
                        'mimetype': mimetype,
                        'type': 'binary',
                        'res_model': self._name,
                    }
                    if vals.get('company_id'):
                        attach_vals['company_id'] = vals['company_id']
                    attachment = self.env['ir.attachment'].create(attach_vals)
                    vals['attachment_id'] = attachment.id
                    vals['current_revision_uuid'] = attachment.checksum
            if vals.get('type') == 'url' and not vals.get('url'):
                vals['url'] = vals.get('name', '')
        records = super().create(vals_list)
        records._maybe_create_activity()
        return records

    def write(self, vals):
        """Handle versioning on file replacement without recursion.

        Builds the complete vals (including version-history commands) and
        calls super().write once.
        """
        datas = vals.pop('datas', None)
        new_attach_id = vals.get('attachment_id')

        if datas:
            # New upload on existing document(s) → create a fresh attachment
            for doc in self:
                if doc.type != 'binary':
                    continue
                filename = doc.name or _('Document')
                mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'datas': datas,
                    'mimetype': mimetype,
                    'type': 'binary',
                    'res_model': self._name,
                    'company_id': doc.company_id.id,
                })
                if doc.attachment_id:
                    vals.setdefault('previous_attachment_ids', [])
                    vals['previous_attachment_ids'] += [(4, doc.attachment_id.id)]
                vals['attachment_id'] = attachment.id
                vals['current_revision_uuid'] = attachment.checksum
        elif new_attach_id:
            # Attachment replaced explicitly → keep old one in history
            for doc in self:
                if doc.attachment_id and doc.attachment_id.id != new_attach_id:
                    vals.setdefault('previous_attachment_ids', [])
                    vals['previous_attachment_ids'] += [(4, doc.attachment_id.id)]

        return super().write(vals)

    def unlink(self):
        attachments = self.mapped('attachment_id')
        res = super().unlink()
        if attachments:
            remaining = self.env['flousflow.document'].sudo().search([
                ('attachment_id', 'in', attachments.ids),
            ])
            removable = attachments - remaining.mapped('attachment_id')
            for att in removable.sudo():
                try:
                    att.unlink()
                except Exception:
                    # attachment may be locked by another module — keep it
                    pass
        return res

    # ------------------------------------------------------------------
    # Activities
    # ------------------------------------------------------------------
    def _maybe_create_activity(self):
        """Create an activity on upload when create_activity_option is set."""
        for doc in self:
            if not doc.create_activity_option or not doc.create_activity_type_id:
                continue
            vals = {
                'activity_type_id': doc.create_activity_type_id.id,
                'summary': doc.create_activity_summary or False,
                'note': doc.create_activity_note or False,
                'user_id': doc.create_activity_user_id.id or self.env.uid,
            }
            if doc.create_activity_date_deadline_range:
                date_deadline = fields.Date.context_today(self)
                if doc.create_activity_date_deadline_range_type == 'weeks':
                    date_deadline = date_deadline + timedelta(weeks=doc.create_activity_date_deadline_range)
                elif doc.create_activity_date_deadline_range_type == 'months':
                    date_deadline = date_deadline + relativedelta(months=doc.create_activity_date_deadline_range)
                else:
                    date_deadline = date_deadline + timedelta(days=doc.create_activity_date_deadline_range)
                vals['date_deadline'] = date_deadline
            doc.activity_schedule(**vals)

    # ------------------------------------------------------------------
    # Actions (UI helpers)
    # ------------------------------------------------------------------
    def action_toggle_favorite(self):
        self.ensure_one()
        if self.env.uid in self.favorited_ids.ids:
            self.favorited_ids = [(3, self.env.uid)]
        else:
            self.favorited_ids = [(4, self.env.uid)]
        return True

    # ------------------------------------------------------------------
    # M2 actions — sharing, operations, request, link
    # ------------------------------------------------------------------
    def _get_access_url(self):
        """Full share URL for a document (public route + token)."""
        self.ensure_one()
        if not self.access_token or self.access_via_link == 'none':
            return False
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return f'{base_url}/flousflow/documents/{self.id}?access_token={self.access_token}'

    def action_share(self):
        """Open the sharing wizard for the selected documents."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Share'),
            'res_model': 'flousflow.document.sharing',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_ids': [(6, 0, self.ids)],
                'default_owner_id': self.env.uid,
            },
        }

    def action_share_link(self):
        """Copy the share link to the clipboard (returns it for display)."""
        self.ensure_one()
        if not self.access_token:
            self.access_token = self._generate_access_token()
        return self._get_access_url()

    def action_move(self):
        """Open the move/copy operation wizard."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Move / Copy'),
            'res_model': 'flousflow.document.operation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'flousflow.document',
                'active_ids': self.ids,
                'default_document_ids': [(6, 0, self.ids)],
            },
        }

    def action_request_file(self):
        """Open the 'Request a file' wizard."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request a file'),
            'res_model': 'flousflow.document.request.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_link_to_record(self):
        """Open the 'Link to record' wizard."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Link to Record'),
            'res_model': 'flousflow.document.link.to.record.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'flousflow.document',
                'active_ids': self.ids,
                'default_document_ids': [(6, 0, self.ids)],
            },
        }

    def action_folder_create(self):
        """Close the 'New Folder' dialog (record is saved by the form)."""
        return {'type': 'ir.actions.act_window_close'}

    def action_rename(self):
        """Close the 'Rename' dialog (record is saved by the form)."""
        return {'type': 'ir.actions.act_window_close'}

    def action_url_save(self):
        """Close the 'Add URL' dialog (record is saved by the form)."""
        return {'type': 'ir.actions.act_window_close'}

    def action_lock(self):
        for doc in self:
            if doc.lock_uid:
                raise UserError(_('This document is already locked.'))
            doc.lock_uid = self.env.uid
        return True

    def action_unlock(self):
        for doc in self:
            if doc.lock_uid and doc.lock_uid.id != self.env.uid and not self.env.user.has_group('flousflow_documents.group_documents_manager'):
                raise UserError(_('Only the user who locked the document or a manager can unlock it.'))
            doc.lock_uid = False
        return True

    # ------------------------------------------------------------------
    # Trash
    # ------------------------------------------------------------------
    def action_move_to_trash(self):
        """Move the document (and its sub-folders content) to the trash."""
        delay = int(self.env['ir.config_parameter'].sudo().get_param(
            'flousflow_documents_deletion_delay', '30'))
        now = fields.Datetime.now()
        for doc in self:
            if doc.trashed:
                continue
            doc.trashed = True
            doc.trash_date = now
            doc.deletion_date = now + timedelta(days=delay)
        return True

    def action_restore(self):
        for doc in self:
            if not doc.trashed:
                continue
            doc.trashed = False
            doc.trash_date = False
            doc.deletion_date = False
        return True

    def action_delete_permanently(self):
        """Ask for an explicit confirmation before permanently deleting the
        trashed documents (permanent deletion cannot be undone)."""
        for doc in self:
            if not doc.trashed:
                raise UserError(
                    _('Only trashed documents can be permanently deleted.'))
        return {
            'name': _('Delete Forever'),
            'type': 'ir.actions.act_window',
            'res_model': 'flousflow.document.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_ids': self.ids},
        }

    @api.model
    def _cron_delete_trashed(self):
        """Auto-purge trashed documents past their scheduled deletion date."""
        to_delete = self.search([
            ('trashed', '=', True),
            ('deletion_date', '<=', fields.Datetime.now()),
        ])
        if to_delete:
            to_delete.unlink()
        return True

    @api.depends('write_date')
    def _compute_is_recent(self):
        cutoff = fields.Datetime.now() - timedelta(days=30)
        for doc in self:
            doc.is_recent = doc.write_date >= cutoff

    @api.model
    def _search_is_recent(self, operator, value):
        cutoff = fields.Datetime.now() - timedelta(days=30)
        recent = (operator == '=' and value) or (operator == '!=' and not value)
        if recent:
            return [('write_date', '>=', cutoff)]
        return [('write_date', '<', cutoff)]

    # ------------------------------------------------------------------
    # "New" menu actions (control-panel view buttons). Returning a dict at
    # runtime avoids load-time xmlid ordering issues with view buttons.
    # ------------------------------------------------------------------
    def _open_new_dialog(self, doc_type, title, view_xmlid):
        return {
            'type': 'ir.actions.act_window',
            'name': _(title),
            'res_model': 'flousflow.document',
            'view_mode': 'form',
            'view_id': self.env.ref('flousflow_documents.%s' % view_xmlid).id,
            'target': 'new',
            'context': {'default_type': doc_type},
        }

    def action_new_upload(self, *args, **kwargs):
        return self._open_new_dialog('binary', 'Upload', 'view_document_form')

    def action_new_url(self, *args, **kwargs):
        return self._open_new_dialog('url', 'New Link', 'view_document_form_upload_url')

    def action_new_folder(self, *args, **kwargs):
        return self._open_new_dialog('folder', 'New Folder', 'view_document_form_new_folder')

    @api.model
    def _referencable_models(self):
        """Models usable in the 'link to record' reference field."""
        models = self.env['ir.model'].sudo().search([
            ('transient', '=', False),
        ], order='name')
        return [(m.model, m.name) for m in models if m.model in self.env.registry]

    @api.constrains('type', 'attachment_id', 'request_activity_id', 'requestee_partner_id')
    def _check_type_attachment(self):
        for doc in self:
            if (doc.type == 'binary' and not doc.attachment_id
                    and not doc.request_activity_id and not doc.requestee_partner_id):
                raise UserError(_('A file document must have an attachment. Upload a file first.'))
            if doc.type == 'folder' and doc.attachment_id:
                raise UserError(_('A folder cannot have an attachment.'))
            if doc.type == 'url' and doc.attachment_id:
                raise UserError(_('A URL document cannot have an attachment.'))
