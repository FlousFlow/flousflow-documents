# -*- coding: utf-8 -*-
"""FlousFlow Documents — per-partner access and access tracking."""

from odoo import fields, models


class FlousflowDocumentAccess(models.Model):
    _name = 'flousflow.document.access'
    _description = 'Document / Partner'
    _order = 'id'

    document_id = fields.Many2one(
        'flousflow.document', string='Document', required=True,
        ondelete='cascade', index=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Partner', required=True,
        ondelete='cascade', index=True,
    )
    role = fields.Selection(
        selection=[('view', 'Viewer'), ('edit', 'Editor')],
        string='Role', required=True, default='view',
    )
    expiration_date = fields.Datetime(string='Expiration')
    last_access_date = fields.Datetime(string='Last Accessed On')

    _partner_document_unique = models.Constraint(
        'unique(document_id, partner_id)',
        'This partner already has access to this document.',
    )


class FlousflowDocumentAccessTracking(models.Model):
    """Audit trail of permission changes (who changed what on which docs)."""

    _name = 'flousflow.document.access.tracking'
    _description = 'Document Access Tracking'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', string='User', required=True, index=True)
    changes = fields.Json(string='Changes', required=True)
    documents = fields.Json(string='Impacted Document Ids', required=True)
