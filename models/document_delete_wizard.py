# -*- coding: utf-8 -*-
"""FlousFlow Documents — permanent deletion confirmation wizard."""

from odoo import api, fields, models, _


class FlousflowDocumentDeleteWizard(models.TransientModel):
    """Confirmation dialog shown before permanently deleting trashed documents.
    Permanent deletion is destructive and cannot be undone, so it always goes
    through this explicit confirmation (mirrors the original Documents app)."""

    _name = 'flousflow.document.delete.wizard'
    _description = 'Delete Documents Confirmation'

    document_ids = fields.Many2many(
        'flousflow.document', string='Documents', readonly=True,
    )
    document_count = fields.Integer(
        string='Document Count', compute='_compute_document_count', readonly=True,
    )

    @api.depends('document_ids')
    def _compute_document_count(self):
        for wizard in self:
            wizard.document_count = len(wizard.document_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # The wizard is opened from the action context (selected documents)
        context = self.env.context or {}
        if context.get('active_model') == 'flousflow.document' and context.get('active_ids'):
            res['document_ids'] = [(6, 0, context['active_ids'])]
        return res

    def action_confirm_delete(self):
        """Permanently delete the selected trashed documents."""
        self.ensure_one()
        if not self.document_ids:
            return {'type': 'ir.actions.act_window_close'}
        self.document_ids.unlink()
        return {'type': 'ir.actions.act_window_close'}
