# -*- coding: utf-8 -*-
"""FlousFlow Documents — link documents to any record wizard."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FlousflowDocumentLinkToRecordWizard(models.TransientModel):
    _name = 'flousflow.document.link.to.record.wizard'
    _description = 'Documents Link to Record'

    document_ids = fields.Many2many(
        'flousflow.document', string='Documents', required=True,
    )
    model_id = fields.Many2one('ir.model', string='Model')
    resource_ref = fields.Reference(
        string='Record', selection='_referencable_models',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context or {}
        if context.get('active_model') == 'flousflow.document' and context.get('active_ids'):
            res['document_ids'] = [(6, 0, context['active_ids'])]
        return res

    @api.model
    def _referencable_models(self):
        models = self.env['ir.model'].sudo().search([
            ('transient', '=', False),
        ], order='name')
        return [(m.model, m.name) for m in models if m.model in self.env.registry]

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.resource_ref = False

    def action_link(self):
        self.ensure_one()
        if not self.resource_ref:
            raise UserError(_('Please select a record to link the documents to.'))
        record = self.resource_ref
        partner_id = False
        if hasattr(record, 'partner_id') and record.partner_id:
            partner_id = record.partner_id.id
        for document in self.document_ids:
            document.write({
                'res_model': record._name,
                'res_id': record.id,
                'partner_id': document.partner_id.id or partner_id,
            })
        return {'type': 'ir.actions.act_window_close'}
