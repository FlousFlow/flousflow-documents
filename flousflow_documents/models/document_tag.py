# -*- coding: utf-8 -*-
"""FlousFlow Documents — tag model."""

from odoo import fields, models


class FlousflowDocumentTag(models.Model):
    _name = 'flousflow.document.tag'
    _description = 'Tag'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')
    sequence = fields.Integer(string='Sequence', default=10)
    tooltip = fields.Char(string='Tooltip')
    document_ids = fields.Many2many(
        'flousflow.document', 'flousflow_document_tag_rel',
        'tag_id', 'document_id', string='Documents',
    )
