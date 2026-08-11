# -*- coding: utf-8 -*-
"""FlousFlow Documents — "Request a file" wizard."""

from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class FlousflowDocumentRequestWizard(models.TransientModel):
    _name = 'flousflow.document.request.wizard'
    _description = 'Document Request'

    name = fields.Char(string='Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='set null')
    requestee_id = fields.Many2one('res.partner', string='Owner', required=True)
    folder_id = fields.Many2one(
        'flousflow.document', string='Folder', domain="[('type', '=', 'folder')]",
    )
    tag_ids = fields.Many2many('flousflow.document.tag', string='Tags')
    res_model = fields.Char(string='Resource Model')
    res_id = fields.Integer(string='Resource ID')
    activity_type_id = fields.Many2one(
        'mail.activity.type', string='Activity type', required=True,
        default=lambda self: self._default_activity_type_id(),
    )
    activity_date_deadline_range = fields.Integer(string='Due Date In')
    activity_date_deadline_range_type = fields.Selection(
        selection=[('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        string='Due type', default='days',
    )
    activity_note = fields.Html(string='Message')

    @api.model
    def _default_activity_type_id(self):
        request_type = self.env.ref(
            'mail.mail_activity_data_todo', raise_if_not_found=False,
        )
        return request_type.id if request_type else False

    def action_request(self):
        """Create a placeholder request and an activity on the requestee.

        The requestee receives an activity asking them to upload the file;
        the placeholder document (no attachment yet) keeps the context
        (folder, tags, linked record).
        """
        self.ensure_one()
        requestee = self.requestee_id
        # owner user = internal user linked to the requestee partner, if any
        owner_user = requestee.user_ids.filtered(lambda u: not u.share)[:1]

        request_doc = self.env['flousflow.document'].create({
            'name': self.name,
            'type': 'binary',
            'folder_id': self.folder_id.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'partner_id': self.partner_id.id or requestee.id,
            'res_model': self.res_model,
            'res_id': self.res_id if self.res_model and self.res_id else False,
            'owner_id': owner_user.id or self.env.uid,
            'requestee_partner_id': requestee.id,
        })

        # schedule an activity for the requestee
        vals = {
            'activity_type_id': self.activity_type_id.id,
            'summary': _('Please provide the file "%s"', self.name),
            'note': self.activity_note or False,
            'user_id': owner_user.id or self.env.uid,
        }
        if self.activity_date_deadline_range:
            date_deadline = fields.Date.context_today(self)
            if self.activity_date_deadline_range_type == 'weeks':
                date_deadline += timedelta(weeks=self.activity_date_deadline_range)
            elif self.activity_date_deadline_range_type == 'months':
                date_deadline += relativedelta(months=self.activity_date_deadline_range)
            else:
                date_deadline += timedelta(days=self.activity_date_deadline_range)
            vals['date_deadline'] = date_deadline
        activity = request_doc.activity_schedule(**vals)
        if activity:
            request_doc.write({'request_activity_id': activity[0].id})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'flousflow.document',
            'view_mode': 'form',
            'res_id': request_doc.id,
            'target': 'current',
        }
