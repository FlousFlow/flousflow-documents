# -*- coding: utf-8 -*-
"""FlousFlow Documents — public share link controller.

Allows external (non-logged) users to download a document shared via link.
The link is only valid when `access_via_link != 'none'` and the access token
matches (when the token is set).
"""

import werkzeug

from odoo import http
from odoo.http import request


class FlousflowDocumentController(http.Controller):

    @http.route('/flousflow/documents/<int:document_id>', type='http', auth='public', website=False)
    def document_download(self, document_id, access_token=None, **kwargs):
        document = request.env['flousflow.document'].sudo().browse(document_id)
        if not document.exists() or document.type != 'binary':
            return werkzeug.exceptions.NotFound()
        if document.access_via_link == 'none':
            return werkzeug.exceptions.NotFound()
        if document.access_token and access_token != document.access_token:
            return werkzeug.exceptions.NotFound()
        attachment = document.attachment_id.sudo()
        if not attachment:
            return werkzeug.exceptions.NotFound()
        content_disposition = 'attachment; filename=%s' % werkzeug.utils.quote(
            attachment.name or 'document'
        )
        return request.make_response(
            attachment.raw,
            headers=[
                ('Content-Type', attachment.mimetype or 'application/octet-stream'),
                ('Content-Disposition', content_disposition),
                ('Content-Length', str(attachment.file_size or len(attachment.raw or b''))),
            ],
        )
