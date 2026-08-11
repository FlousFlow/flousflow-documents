# -*- coding: utf-8 -*-
"""FlousFlow Documents — sharing (partners + link) and per-partner access."""

from odoo import api, fields, models, _


class FlousflowDocumentSharing(models.Model):
    """A saved "Share" action: applies access rights to a set of documents and
    records per-partner sharing lines (with expiration)."""

    _name = 'flousflow.document.sharing'
    _description = 'Documents Sharing'
    _order = 'id desc'

    document_ids = fields.Many2many(
        'flousflow.document', string='Documents', required=True,
    )
    owner_id = fields.Many2one(
        'res.users', string='Owner', default=lambda self: self.env.user,
    )
    access_internal = fields.Selection(
        selection=[('view', 'Viewer'), ('edit', 'Editor'), ('none', 'None')],
        string='Internal users', required=True, default='none',
    )
    access_via_link = fields.Selection(
        selection=[('view', 'Viewer'), ('edit', 'Editor'), ('none', 'None')],
        string='Access through link', required=True, default='none',
    )
    access_via_link_mode = fields.Selection(
        selection=[('discoverable', 'Discoverable'), ('hidden', 'Hidden')],
        string='Link access mode', default='discoverable',
    )
    is_access_via_link_hidden = fields.Boolean(
        string='Hide link access option', compute='_compute_is_access_via_link_hidden',
    )
    invite_partner_ids = fields.Many2many(
        'res.partner', string='Invite Partners',
    )
    invite_role = fields.Selection(
        selection=[('view', 'Viewer'), ('edit', 'Editor')],
        string='Role', required=True, default='view',
    )
    invite_notify = fields.Boolean(string='Notify')
    invite_notify_message = fields.Html(
        string='Notification Message',
        default=lambda self: _('Hello,<br/>A document has been shared with you.'),
    )
    share_access_ids = fields.One2many(
        'flousflow.document.sharing.access', 'documents_sharing_id',
        string='Share Access',
    )

    # --- Computed helpers used by the UI -------------------------------
    is_readonly = fields.Boolean(compute='_compute_is_readonly')
    is_single = fields.Boolean(compute='_compute_is_single')
    is_folder_only = fields.Boolean(compute='_compute_is_folder_only')
    has_warning_link_with_more_rights = fields.Char(
        compute='_compute_warnings', string='Has Warning Link With More Rights',
    )
    has_warning_partners_without_access = fields.Char(
        compute='_compute_warnings', string='Has Warning Partners Without Access',
    )

    @api.depends('document_ids')
    def _compute_is_single(self):
        for share in self:
            share.is_single = len(share.document_ids) == 1

    @api.depends('document_ids.type')
    def _compute_is_folder_only(self):
        for share in self:
            share.is_folder_only = bool(share.document_ids) and all(
                d.type == 'folder' for d in share.document_ids
            )

    @api.depends('access_internal', 'access_via_link', 'document_ids')
    def _compute_is_readonly(self):
        for share in self:
            share.is_readonly = bool(share.document_ids) and not any(
                d.user_permission == 'edit' for d in share.document_ids
            )

    @api.depends('access_via_link', 'access_internal')
    def _compute_is_access_via_link_hidden(self):
        for share in self:
            share.is_access_via_link_hidden = share.access_via_link != 'none'

    @api.depends('access_internal', 'access_via_link', 'document_ids')
    def _compute_warnings(self):
        for share in self:
            # link more permissive than internal access
            levels = {'none': 0, 'view': 1, 'edit': 2}
            if (levels.get(share.access_via_link, 0) >
                    levels.get(share.access_internal, 0)):
                share.has_warning_link_with_more_rights = _(
                    'The link access is more permissive than the internal '
                    'access rights. Do you really want to continue?'
                )
            else:
                share.has_warning_link_with_more_rights = False
            # partners without any access on the documents
            partners = share.invite_partner_ids - share.document_ids.mapped('partner_id')
            if partners:
                share.has_warning_partners_without_access = _(
                    'The following partners have no access to the documents: %s',
                    ', '.join(partners.mapped('name')),
                )
            else:
                share.has_warning_partners_without_access = False

    # ------------------------------------------------------------------
    @api.model
    def _prepare_sharing_access_vals(self, partner):
        return {
            'partner_id': partner.id,
            'role': self.invite_role,
        }

    def action_share(self):
        """Apply the sharing settings to the selected documents."""
        self.ensure_one()
        documents = self.document_ids
        if not self.is_readonly:
            # internal access (only meaningful when not readonly)
            if self.access_internal != 'none':
                documents.write({'access_internal': self.access_internal})
            # link access
            documents.write({
                'access_via_link': self.access_via_link,
                'is_access_via_link_hidden': self.is_access_via_link_hidden,
            })

        # per-partner access
        for partner in self.invite_partner_ids:
            for document in documents:
                existing = document.access_ids.filtered(
                    lambda a: a.partner_id.id == partner.id
                )
                vals = {
                    'document_id': document.id,
                    'partner_id': partner.id,
                    'role': self.invite_role,
                }
                if existing:
                    existing.write({'role': self.invite_role})
                else:
                    self.env['flousflow.document.access'].create(vals)
            # record the share line
            access_vals = self._prepare_sharing_access_vals(partner)
            existing_share = self.share_access_ids.filtered(
                lambda a: a.partner_id.id == partner.id
            )
            if existing_share:
                existing_share.write(access_vals)
            else:
                self.share_access_ids = [(0, 0, access_vals)]

        if self.invite_notify:
            self._notify_partners()
        return {'type': 'ir.actions.act_window_close'}

    def _notify_partners(self):
        """Send a chatter message / email to the invited partners."""
        for partner in self.invite_partner_ids:
            for document in self.document_ids:
                message = self.invite_notify_message or _('A document has been shared with you.')
                document.message_post(
                    body=message,
                    partner_ids=[partner.id],
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )

    def action_save(self):
        """Save (already applied) and close."""
        return {'type': 'ir.actions.act_window_close'}


class FlousflowDocumentSharingAccess(models.Model):
    _name = 'flousflow.document.sharing.access'
    _description = 'Documents share access'
    _order = 'id desc'

    documents_sharing_id = fields.Many2one(
        'flousflow.document.sharing', string='Documents share', ondelete='cascade',
    )
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    role = fields.Selection(
        selection=[('view', 'Viewer'), ('edit', 'Editor')],
        string='Role', default='view', required=True,
    )
    expiration_date = fields.Datetime(string='Expiration')
    original_expiration_date = fields.Datetime(string='Original Expiration')
    is_deleted = fields.Boolean(string='Is Deleted')
    has_user = fields.Boolean(string='Has User', compute='_compute_has_user')
    is_readonly = fields.Boolean(string='Readonly', compute='_compute_is_readonly')
    is_on_single_document = fields.Boolean(
        string='Is On Single Document', compute='_compute_is_on_single_document',
    )

    @api.depends('partner_id')
    def _compute_has_user(self):
        for line in self:
            line.has_user = bool(line.partner_id.user_ids.filtered(lambda u: not u.share))

    @api.depends('documents_sharing_id.document_ids')
    def _compute_is_on_single_document(self):
        for line in self:
            line.is_on_single_document = bool(
                line.documents_sharing_id and len(line.documents_sharing_id.document_ids) == 1
            )

    @api.depends('expiration_date', 'is_deleted')
    def _compute_is_readonly(self):
        for line in self:
            line.is_readonly = bool(line.is_deleted)
