# -*- coding: utf-8 -*-
"""FlousFlow Documents — creation mixin.

Abstract model that other models can inherit to create documents
bound to their records through res_model/res_id.
"""

from odoo import models, _


class FlousflowDocumentMixin(models.AbstractModel):
    _name = 'flousflow.document.mixin'
    _description = 'Documents creation mixin'

    def _get_document_vals(self, **kwargs):
        """Hook: return default values used when creating a document
        from this record. Subclasses should override to fill e.g.
        folder_id, tag_ids, owner_id...
        """
        self.ensure_one()
        return {
            'res_model': self._name,
            'res_id': self.id,
        }

    def create_document(self, name, datas=None, url=False, **kwargs):
        """Create a document linked to this record."""
        self.ensure_one()
        vals = self._get_document_vals(**kwargs)
        vals.update({
            'name': name or _('Document'),
        })
        if url:
            vals.update({'type': 'url', 'url': url})
        else:
            vals.update({'type': 'binary'})
            if datas:
                vals['datas'] = datas
        return self.env['flousflow.document'].create(vals)
