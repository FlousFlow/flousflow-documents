# -*- coding: utf-8 -*-
"""Tests for flousflow_documents — permission model + core behaviour."""

import base64

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestDocumentCore(TransactionCase):
    def setUp(self):
        super().setUp()
        self.owner = self._create_user('doc_owner', base_group='base.group_user')
        self.user = self._create_user('doc_user', base_group='base.group_user')
        self.manager = self._create_user(
            'doc_manager', base_group='flousflow_documents.group_documents_manager'
        )

    def _create_user(self, login, base_group):
        # Internal users always get the Documents / User group (like Odoo —
        # without it they cannot access the Documents app at all).
        group_ids = [self.env.ref('flousflow_documents.group_documents_user').id]
        if base_group != 'flousflow_documents.group_documents_manager':
            group_ids.append(self.env.ref(base_group).id)
        else:
            group_ids = [self.env.ref(base_group).id]
        return self.env['res.users'].create({
            'name': login.replace('_', ' ').title(),
            'login': login,
            'group_ids': [(6, 0, group_ids)],
        })

    def _make_private_folder(self, name='Private Folder'):
        return self.env['flousflow.document'].create({
            'name': name,
            'type': 'folder',
            'access_internal': 'none',
            'owner_id': self.owner.id,
        })

    # ------------------------------------------------------------------
    def test_default_folders_loaded(self):
        inbox = self.env.ref('flousflow_documents.folder_inbox')
        self.assertEqual(inbox.type, 'folder')
        self.assertEqual(inbox.access_internal, 'edit')

    def test_create_file_with_datas(self):
        doc = self.env['flousflow.document'].create({
            'name': 'test.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'hello world'),
        })
        self.assertTrue(doc.attachment_id)
        self.assertEqual(doc.file_size, 11)
        self.assertEqual(doc.file_extension, 'txt')

    def test_create_url(self):
        doc = self.env['flousflow.document'].create({
            'name': 'Odoo',
            'type': 'url',
            'url': 'https://www.odoo.com',
        })
        self.assertEqual(doc.type, 'url')
        self.assertEqual(doc.url, 'https://www.odoo.com')

    def test_version_history_on_reupload(self):
        doc = self.env['flousflow.document'].create({
            'name': 'v1.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'version one'),
        })
        first_attachment = doc.attachment_id
        doc.write({'datas': base64.b64encode(b'version two')})
        self.assertNotEqual(doc.attachment_id, first_attachment)
        self.assertIn(first_attachment, doc.previous_attachment_ids)

    # ------------------------------------------------------------------
    def test_owner_reads_private_document(self):
        folder = self._make_private_folder()
        doc = self.env['flousflow.document'].create({
            'name': 'secret.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'secret'),
            'folder_id': folder.id,
            'owner_id': self.owner.id,
        })
        visible = self.env['flousflow.document'].with_user(self.owner).search(
            [('id', '=', doc.id)]
        )
        self.assertEqual(visible.id, doc.id)

    def test_other_user_cannot_read_private_document(self):
        folder = self._make_private_folder()
        doc = self.env['flousflow.document'].create({
            'name': 'secret.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'secret'),
            'folder_id': folder.id,
            'owner_id': self.owner.id,
        })
        visible = self.env['flousflow.document'].with_user(self.user).search(
            [('id', '=', doc.id)]
        )
        self.assertFalse(visible)

    def test_partner_access_grants_view(self):
        folder = self._make_private_folder()
        doc = self.env['flousflow.document'].create({
            'name': 'shared.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'shared'),
            'folder_id': folder.id,
        })
        self.env['flousflow.document.access'].create({
            'document_id': doc.id,
            'partner_id': self.user.partner_id.id,
            'role': 'view',
        })
        visible = self.env['flousflow.document'].with_user(self.user).search(
            [('id', '=', doc.id)]
        )
        self.assertEqual(visible.id, doc.id)
        # view permission → cannot write
        with self.assertRaises(AccessError):
            doc.with_user(self.user).write({'name': 'hacked.txt'})

    def test_expired_access_revoked(self):
        from datetime import datetime, timedelta
        folder = self._make_private_folder()
        doc = self.env['flousflow.document'].create({
            'name': 'temp.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'temp'),
            'folder_id': folder.id,
        })
        self.env['flousflow.document.access'].create({
            'document_id': doc.id,
            'partner_id': self.user.partner_id.id,
            'role': 'view',
            'expiration_date': datetime.now() - timedelta(days=1),
        })
        visible = self.env['flousflow.document'].with_user(self.user).search(
            [('id', '=', doc.id)]
        )
        self.assertFalse(visible)

    def test_manager_sees_everything(self):
        folder = self._make_private_folder()
        doc = self.env['flousflow.document'].create({
            'name': 'secret.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'secret'),
            'folder_id': folder.id,
            'owner_id': self.owner.id,
        })
        visible = self.env['flousflow.document'].with_user(self.manager).search(
            [('id', '=', doc.id)]
        )
        self.assertEqual(visible.id, doc.id)

    def test_create_in_private_folder_blocked(self):
        folder = self._make_private_folder()
        with self.assertRaises(AccessError):
            self.env['flousflow.document'].with_user(self.user).create({
                'name': 'x.txt',
                'type': 'binary',
                'datas': base64.b64encode(b'x'),
                'folder_id': folder.id,
            })

    def test_create_in_editable_folder_allowed(self):
        folder = self.env['flousflow.document'].create({
            'name': 'Open Folder',
            'type': 'folder',
            'access_internal': 'edit',
        })
        doc = self.env['flousflow.document'].with_user(self.user).create({
            'name': 'ok.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'ok'),
            'folder_id': folder.id,
        })
        self.assertTrue(doc)

    # ------------------------------------------------------------------
    # M2 — sharing, operations, linking
    # ------------------------------------------------------------------
    def test_share_wizard_applies_access(self):
        doc = self.env['flousflow.document'].create({
            'name': 'share_me.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'share'),
        })
        partner = self.env['res.partner'].create({'name': 'Share Partner'})
        share = self.env['flousflow.document.sharing'].create({
            'document_ids': [(6, 0, [doc.id])],
            'owner_id': self.env.uid,
            'access_internal': 'view',
            'access_via_link': 'view',
            'invite_partner_ids': [(6, 0, [partner.id])],
            'invite_role': 'edit',
        })
        share.action_share()
        doc.invalidate_recordset()
        self.assertEqual(doc.access_internal, 'view')
        self.assertEqual(doc.access_via_link, 'view')
        acc = doc.access_ids.filtered(lambda a: a.partner_id.id == partner.id)
        self.assertTrue(acc)
        self.assertEqual(acc.role, 'edit')
        self.assertEqual(len(share.share_access_ids), 1)

    def test_share_link_url_generated(self):
        doc = self.env['flousflow.document'].create({
            'name': 'link_me.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'link'),
            'access_via_link': 'view',
        })
        if not doc.access_token:
            doc.access_token = doc._generate_access_token()
        url = doc._get_access_url()
        self.assertTrue(url)
        self.assertIn(str(doc.id), url)
        self.assertIn(doc.access_token, url)

    def test_move_operation(self):
        folder_a = self.env['flousflow.document'].create({
            'name': 'Folder A', 'type': 'folder', 'access_internal': 'edit',
        })
        folder_b = self.env['flousflow.document'].create({
            'name': 'Folder B', 'type': 'folder', 'access_internal': 'edit',
        })
        doc = self.env['flousflow.document'].create({
            'name': 'movable.txt', 'type': 'binary',
            'datas': base64.b64encode(b'move'),
            'folder_id': folder_a.id,
        })
        op = self.env['flousflow.document.operation'].create({
            'document_ids': [(6, 0, [doc.id])],
            'operation': 'move',
            'destination_folder_id': folder_b.id,
        })
        op.action_move()
        self.assertEqual(doc.folder_id.id, folder_b.id)

    def test_copy_operation(self):
        folder = self.env['flousflow.document'].create({
            'name': 'Copy Folder', 'type': 'folder', 'access_internal': 'edit',
        })
        doc = self.env['flousflow.document'].create({
            'name': 'copied.txt', 'type': 'binary',
            'datas': base64.b64encode(b'copy content'),
        })
        op = self.env['flousflow.document.operation'].create({
            'document_ids': [(6, 0, [doc.id])],
            'operation': 'copy',
            'destination_folder_id': folder.id,
        })
        op.action_copy()
        copies = self.env['flousflow.document'].search([
            ('name', '=', 'copied.txt'), ('id', '!=', doc.id),
        ])
        self.assertEqual(len(copies), 1)
        self.assertTrue(copies.attachment_id)
        self.assertEqual(copies.file_size, 12)

    def test_link_to_record_wizard(self):
        doc = self.env['flousflow.document'].create({
            'name': 'linked.txt', 'type': 'binary',
            'datas': base64.b64encode(b'link'),
        })
        # use res.partner (contacts is a dependency of this module)
        partner = self.env['res.partner'].create({'name': 'Link Target'})
        model = self.env['ir.model'].search(
            [('model', '=', 'res.partner')], limit=1,
        )
        link = self.env['flousflow.document.link.to.record.wizard'].create({
            'document_ids': [(6, 0, [doc.id])],
            'model_id': model.id,
        })
        link.resource_ref = '%s,%d' % (partner._name, partner.id)
        link.action_link()
        self.assertEqual(doc.res_model, 'res.partner')
        self.assertEqual(int(doc.res_id), partner.id)

    def test_request_file_wizard(self):
        partner = self.env['res.partner'].create({'name': 'Requestee'})
        req = self.env['flousflow.document.request.wizard'].create({
            'name': 'Signed Contract',
            'requestee_id': partner.id,
        })
        req.action_request()
        created = self.env['flousflow.document'].search(
            [('name', '=', 'Signed Contract')], limit=1,
        )
        self.assertTrue(created)
        self.assertTrue(created.requestee_partner_id)
        self.assertTrue(created.request_activity_id)
