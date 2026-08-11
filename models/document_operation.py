# -*- coding: utf-8 -*-
"""FlousFlow Documents — bulk operations (move / copy) wizard."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FlousflowDocumentOperation(models.TransientModel):
    _name = 'flousflow.document.operation'
    _description = 'Documents Operation'

    document_ids = fields.Many2many(
        'flousflow.document', string='Documents', required=True,
    )
    operation = fields.Selection(
        selection=[('move', 'Move to'), ('copy', 'Duplicate in')],
        string='Operation', required=True, default='move',
    )
    destination_folder_id = fields.Many2one(
        'flousflow.document', string='Destination Folder',
        domain="[('type', '=', 'folder')]", ondelete='set null',
    )
    # When moving into a folder, optionally redefine the access rights
    access_internal = fields.Selection(
        selection=[('view', 'Viewer'), ('edit', 'Editor'), ('none', 'None')],
        string='Destination Access Internal', default='none',
    )
    access_via_link = fields.Selection(
        selection=[('view', 'Viewer'), ('edit', 'Editor'), ('none', 'None')],
        string='Destination Access Via Link', default='none',
    )
    user_permission = fields.Selection(
        selection=[('edit', 'Editor'), ('view', 'Viewer'), ('none', 'None')],
        string='Destination User Permission', default='none',
    )
    is_access_via_link_hidden = fields.Boolean(string='Link Access Hidden')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # The wizard is opened from the action context (selected documents)
        context = self.env.context or {}
        if context.get('active_model') == 'flousflow.document' and context.get('active_ids'):
            res['document_ids'] = [(6, 0, context['active_ids'])]
        return res

    def action_move(self):
        """Move the selected documents into the destination folder."""
        self.ensure_one()
        if not self.destination_folder_id:
            raise UserError(_('Please select a destination folder.'))
        if self.destination_folder_id in self.document_ids:
            raise UserError(_('A folder cannot be moved into itself.'))
        self.document_ids.write({'folder_id': self.destination_folder_id.id})
        if self.access_internal != 'none':
            self.document_ids.write({'access_internal': self.access_internal})
        if self.access_via_link != 'none':
            self.document_ids.write({'access_via_link': self.access_via_link})
        if self.user_permission != 'none':
            for doc in self.document_ids:
                if doc.type != 'folder':
                    doc.write({'access_internal': self.user_permission})
        return {'type': 'ir.actions.act_window_close'}

    def action_copy(self):
        """Duplicate the selected documents into the destination folder."""
        self.ensure_one()
        if not self.destination_folder_id:
            raise UserError(_('Please select a destination folder.'))
        for document in self.document_ids:
            if document.type == 'folder':
                # deep-copy folders (children too)
                self._copy_folder(document, self.destination_folder_id)
            elif document.type == 'binary':
                # copy needs a fresh attachment (attachment_id is copy=False)
                attachment = document.attachment_id
                new_attachment = self.env['ir.attachment'].create({
                    'name': attachment.name,
                    'datas': attachment.datas,
                    'mimetype': attachment.mimetype,
                    'type': 'binary',
                    'res_model': 'flousflow.document',
                })
                document.copy({
                    'folder_id': self.destination_folder_id.id,
                    'owner_id': self.env.uid,
                    'attachment_id': new_attachment.id,
                })
            else:  # url
                document.copy({
                    'folder_id': self.destination_folder_id.id,
                    'owner_id': self.env.uid,
                })
        return {'type': 'ir.actions.act_window_close'}

    def _copy_folder(self, folder, parent_folder):
        new_folder = folder.copy({
            'folder_id': parent_folder.id,
            'owner_id': self.env.uid,
        })
        for child in folder.children_ids:
            self._copy_folder(child, new_folder)
        return new_folder
