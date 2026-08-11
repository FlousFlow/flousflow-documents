# -*- coding: utf-8 -*-
"""FlousFlow Documents — configuration settings (trash deletion delay)."""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    flousflow_documents_deletion_delay = fields.Integer(
        string='Deletion delay (days)',
        help='Number of days items stay in the trash before being permanently '
             'deleted. Set to 0 to disable automatic deletion.',
        config_parameter='flousflow_documents_deletion_delay',
        default=30,
    )
