# -*- coding: utf-8 -*-
"""Tests for flousflow_documents — M3 (Drive UI backend pieces) + M4
(lock/unlock, email alias, portal)."""

import base64

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestM3M4(TransactionCase):
    def setUp(self):
        super().setUp()
        self.owner = self._create_user('doc_owner', base_group='base.group_user')
        self.user = self._create_user('doc_user', base_group='base.group_user')
        self.manager = self._create_user(
            'doc_manager', base_group='flousflow_documents.group_documents_manager'
        )

    def _create_user(self, login, base_group):
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

    def _make_doc(self, name='doc.txt', folder=None, owner=None, datas=b'M3M4'):
        vals = {
            'name': name,
            'type': 'binary',
            'datas': base64.b64encode(datas),
        }
        if folder:
            vals['folder_id'] = folder.id
        if owner:
            vals['owner_id'] = owner.id
        return self.env['flousflow.document'].create(vals)

    # ------------------------------------------------------------------
    # M3 — backend pieces used by the OWL Drive UI
    # ------------------------------------------------------------------
    def test_folder_auto_color_cycles_palette(self):
        """New folders get an accent colour cycling the Odoo 0-11 palette."""
        count = self.env['flousflow.document'].search_count(
            [('type', '=', 'folder')]
        )
        f1 = self.env['flousflow.document'].create({
            'name': 'ColorA', 'type': 'folder', 'access_internal': 'edit',
        })
        f2 = self.env['flousflow.document'].create({
            'name': 'ColorB', 'type': 'folder', 'access_internal': 'edit',
        })
        # first new folder gets count % 12, next one cycles +1
        self.assertEqual(f1.color, count % 12)
        self.assertEqual(f2.color, (count + 1) % 12)
        self.assertNotEqual(f1.color, f2.color)

    def test_folder_auto_color_respects_explicit(self):
        f = self.env['flousflow.document'].create({
            'name': 'Explicit', 'type': 'folder', 'access_internal': 'edit',
            'color': 5,
        })
        self.assertEqual(f.color, 5)

    def test_folder_tree_parent_store(self):
        root = self.env['flousflow.document'].create({
            'name': 'Root', 'type': 'folder', 'access_internal': 'edit',
        })
        child = self.env['flousflow.document'].create({
            'name': 'Child', 'type': 'folder',
            'folder_id': root.id, 'access_internal': 'edit',
        })
        self.assertTrue(root.parent_path)
        self.assertTrue(child.parent_path)
        self.assertIn(root.parent_path, child.parent_path)

    def test_search_user_permission_helper(self):
        """The search helper used by record rules/filters returns edit ids."""
        folder = self.env['flousflow.document'].create({
            'name': 'Private Folder', 'type': 'folder',
            'access_internal': 'none', 'owner_id': self.owner.id,
        })
        doc = self._make_doc(folder=folder, owner=self.owner)
        # non-manager owner can see/edit
        found = self.env['flousflow.document'].with_user(self.owner).search(
            [('id', '=', doc.id), ('user_permission', '=', 'edit')]
        )
        self.assertEqual(found.id, doc.id)
        # another non-manager user without access cannot see it
        hidden = self.env['flousflow.document'].with_user(self.user).search(
            [('id', '=', doc.id)]
        )
        self.assertFalse(hidden)

    def test_document_kanban_action_exists(self):
        """The Documents app opens a native kanban view (like the original)."""
        action = self.env.ref('flousflow_documents.action_document')
        self.assertTrue(action)
        self.assertEqual(action._name, 'ir.actions.act_window')
        self.assertEqual(action.res_model, 'flousflow.document')
        # "form" is required in view_mode so clicking a kanban card opens the
        # full form view (fixed via priority on the main form view).
        self.assertEqual(action.view_mode, 'kanban,form,list,activity')

    def test_upload_with_attachment_and_name(self):
        """Upload path used by the OWL file input (name + datas)."""
        doc = self.env['flousflow.document'].with_user(self.user).create({
            'name': 'uploaded.pdf',
            'type': 'binary',
            'datas': base64.b64encode(b'%PDF-1.4 fake'),
        })
        self.assertTrue(doc.attachment_id)
        self.assertEqual(doc.mimetype, 'application/pdf')
        self.assertEqual(doc.file_extension, 'pdf')

    # ------------------------------------------------------------------
    # M4 — lock / unlock
    # ------------------------------------------------------------------
    def test_lock_sets_lock_uid(self):
        doc = self._make_doc(owner=self.owner)
        doc.with_user(self.owner).action_lock()
        self.assertEqual(doc.lock_uid.id, self.owner.id)

    def test_unlock_clears_lock_uid(self):
        doc = self._make_doc(owner=self.owner)
        doc.with_user(self.owner).action_lock()
        doc.with_user(self.owner).action_unlock()
        self.assertFalse(doc.lock_uid)

    def test_lock_twice_raises(self):
        doc = self._make_doc(owner=self.owner)
        doc.with_user(self.owner).action_lock()
        with self.assertRaises(UserError):
            doc.with_user(self.owner).action_lock()

    def test_unlock_by_other_user_blocked(self):
        doc = self._make_doc(owner=self.owner)
        doc.with_user(self.owner).action_lock()
        with self.assertRaises(UserError):
            doc.with_user(self.user).action_unlock()

    def test_unlock_by_manager_allowed(self):
        doc = self._make_doc(owner=self.owner)
        doc.with_user(self.owner).action_lock()
        doc.with_user(self.manager).action_unlock()
        self.assertFalse(doc.lock_uid)

    # ------------------------------------------------------------------
    # M4 — email alias
    # ------------------------------------------------------------------
    def test_create_alias_for_folder(self):
        folder = self.env['flousflow.document'].create({
            'name': 'Contracts', 'type': 'folder', 'access_internal': 'edit',
        })
        folder.action_create_alias()
        self.assertTrue(folder.alias_id)
        self.assertEqual(folder.alias_id.alias_name, 'contracts')
        # alias_parent_thread_id is an INTEGER field in Odoo 19 (not a M2o)
        self.assertEqual(folder.alias_id.alias_parent_thread_id, folder.id)
        self.assertEqual(folder.alias_id.alias_model_id.model, 'flousflow.document')

    def test_alias_name_unique_with_suffix(self):
        f1 = self.env['flousflow.document'].create({
            'name': 'Finance', 'type': 'folder', 'access_internal': 'edit',
        })
        f2 = self.env['flousflow.document'].create({
            'name': 'Finance', 'type': 'folder', 'access_internal': 'edit',
        })
        f1.action_create_alias()
        f2.action_create_alias()
        self.assertNotEqual(f1.alias_id.alias_name, f2.alias_id.alias_name)

    def test_message_new_creates_document(self):
        """Incoming email to a folder alias creates a binary document."""
        folder = self.env['flousflow.document'].create({
            'name': 'EmailInbox', 'type': 'folder', 'access_internal': 'edit',
        })
        folder.action_create_alias()
        msg = {
            'subject': 'New contract',
            'from': 'sender@example.com',
            'attachments': [('contract.pdf', base64.b64encode(b'%PDF-1.4 x'))],
        }
        created = self.env['flousflow.document'].with_context(
            mail_alias_id=folder.alias_id.id,
            default_folder_id=folder.id,
        ).message_new(msg)
        self.assertTrue(created)
        self.assertEqual(created.type, 'binary')
        self.assertEqual(created.name, 'contract.pdf')
        self.assertTrue(created.attachment_id)
        self.assertEqual(created.folder_id.id, folder.id)

    # ------------------------------------------------------------------
    # M4 — portal
    # ------------------------------------------------------------------
    def test_portal_documents_for_partner(self):
        """The query used by /my/documents returns shared documents only."""
        doc = self._make_doc(name='portal_doc.txt', datas=b'portal')
        self.env['flousflow.document.access'].create({
            'document_id': doc.id,
            'partner_id': self.user.partner_id.id,
            'role': 'view',
        })
        # same logic as the portal controller
        accesses = self.env['flousflow.document.access'].sudo().search(
            [('partner_id', '=', self.user.partner_id.id)]
        )
        documents = accesses.mapped('document_id').filtered(
            lambda d: d.type != 'folder' and d.attachment_id
        )
        self.assertIn(doc, documents)
        # other partner sees nothing
        other = self.env['res.partner'].create({'name': 'Other Partner'})
        other_docs = self.env['flousflow.document.access'].sudo().search(
            [('partner_id', '=', other.id)]
        ).mapped('document_id')
        self.assertNotIn(doc, other_docs)

    # ------------------------------------------------------------------
    # Trash (soft delete + auto purge)
    # ------------------------------------------------------------------
    def test_move_to_trash_sets_dates(self):
        doc = self._make_doc(owner=self.owner)
        doc.action_move_to_trash()
        self.assertTrue(doc.trashed)
        self.assertTrue(doc.trash_date)
        self.assertTrue(doc.deletion_date)
        self.assertGreater(doc.deletion_date, doc.trash_date)

    def test_trashed_hidden_from_normal_search(self):
        doc = self._make_doc(owner=self.owner)
        doc.action_move_to_trash()
        visible = self.env['flousflow.document'].with_user(self.owner).search(
            [('id', '=', doc.id), ('trashed', '=', False)]
        )
        self.assertFalse(visible)

    def test_restore_clears_trash(self):
        doc = self._make_doc(owner=self.owner)
        doc.action_move_to_trash()
        doc.action_restore()
        self.assertFalse(doc.trashed)
        self.assertFalse(doc.trash_date)
        self.assertFalse(doc.deletion_date)

    def test_cron_purges_expired_trash(self):
        from datetime import timedelta
        from odoo import fields as odoo_fields
        doc = self._make_doc(owner=self.owner)
        doc.action_move_to_trash()
        doc.deletion_date = odoo_fields.Datetime.now() - timedelta(days=1)
        self.env['flousflow.document']._cron_delete_trashed()
        self.assertFalse(self.env['flousflow.document'].browse(doc.id).exists())

    def test_delete_permanently_only_trashed(self):
        from odoo.exceptions import UserError
        doc = self._make_doc(owner=self.owner)
        with self.assertRaises(UserError):
            doc.action_delete_permanently()
        doc.action_move_to_trash()
        # Opens a confirmation wizard instead of deleting directly
        action = doc.action_delete_permanently()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'flousflow.document.delete.wizard')
        self.assertTrue(self.env['flousflow.document'].browse(doc.id).exists())
        # Confirming through the wizard actually deletes the document
        wizard = self.env['flousflow.document.delete.wizard'].create({
            'document_ids': [(6, 0, doc.ids)],
        })
        wizard.action_confirm_delete()
        self.assertFalse(self.env['flousflow.document'].browse(doc.id).exists())

    def test_new_menu_actions(self):
        """The unified New-menu actions return proper dialog actions."""
        upload = self.env['flousflow.document'].action_new_upload()
        self.assertEqual(upload['type'], 'ir.actions.act_window')
        self.assertEqual(upload['res_model'], 'flousflow.document')
        self.assertEqual(upload['target'], 'new')
        self.assertEqual(upload['context']['default_type'], 'binary')

        folder = self.env['flousflow.document'].action_new_folder()
        self.assertEqual(folder['context']['default_type'], 'folder')
        self.assertEqual(folder['target'], 'new')

        url = self.env['flousflow.document'].action_new_url()
        self.assertEqual(url['context']['default_type'], 'url')
