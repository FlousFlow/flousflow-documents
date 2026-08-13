# -*- coding: utf-8 -*-

from lxml import etree

from odoo.tests.common import TransactionCase

from ..hooks import _translate_view_arch


class TestDocumentViewTranslations(TransactionCase):
    def test_placeholder_attribute_name_is_preserved(self):
        translated = _translate_view_arch(
            '<form string="New Folder">'
            '<field name="name" string="Folder Name" '
            'placeholder="Folder name..." autofocus="1"/>'
            '</form>'
        )

        root = etree.fromstring(translated.encode())
        field = root.find("field")
        self.assertEqual(field.get("string"), "اسم المجلد")
        self.assertEqual(field.get("placeholder"), "اسم المجلد...")

    def test_all_document_view_translations_are_valid_xml(self):
        views = self.env["ir.ui.view"].search([
            ("model", "=", "flousflow.document"),
        ])
        self.assertTrue(views)

        for view in views:
            english_arch = view.with_context(lang="en_US").arch
            translated_arch = _translate_view_arch(english_arch)
            with self.subTest(view=view.key or view.name):
                etree.fromstring(translated_arch.encode())

    def test_settings_are_nested_in_a_settings_block(self):
        settings_view = self.env.ref(
            "flousflow_documents.view_flousflow_documents_settings"
        )
        arch = etree.fromstring(settings_view.arch.encode())
        settings = arch.xpath("//setting")

        self.assertTrue(settings)
        for setting in settings:
            with self.subTest(setting=setting.get("string")):
                self.assertTrue(
                    setting.xpath("ancestor::block"),
                    "Settings must be nested in a block so SearchableSetting "
                    "receives the showAllContainer environment.",
                )
