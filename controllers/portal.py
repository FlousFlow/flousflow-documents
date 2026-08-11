# -*- coding: utf-8 -*-
"""FlousFlow Documents — portal pages for shared documents."""

from odoo import http
from odoo.http import request


class FlousflowDocumentPortal(http.Controller):

    @http.route('/my/documents', type='http', auth='user', website=True)
    def portal_my_documents(self, **kwargs):
        partner = request.env.user.partner_id
        accesses = request.env['flousflow.document.access'].sudo().search(
            [('partner_id', '=', partner.id)]
        )
        documents = accesses.mapped('document_id').filtered(
            lambda d: d.type != 'folder' and d.attachment_id
        )
        return request.render('flousflow_documents.portal_my_documents', {
            'documents': documents,
            'page_name': 'documents',
        })
