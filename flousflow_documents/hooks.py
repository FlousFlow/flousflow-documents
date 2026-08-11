# -*- coding: utf-8 -*-
"""Post-install hook: install Arabic translations directly via JSONB.

Odoo 19 stores translations in JSONB columns (there is no ir.translation
table): field labels live in ir_model_fields.field_description, view strings
in ir_ui_view.arch_db, menu names in ir_ui_menu.name and selection values in
ir_model_fields_selection.name. This hook merges ar_001 into those columns so
the Documents app appears fully in Arabic while the source stays English.
"""

import json
import logging
import re

_logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# FIELD LABEL TRANSLATION MAP
# key: (model_name, field_name) → Arabic label
# ──────────────────────────────────────────────────────────
FIELD_TRANSLATIONS = {
    # ============ flousflow.document ============
    ('flousflow.document', 'type'): 'النوع',
    ('flousflow.document', 'name'): 'الاسم',
    ('flousflow.document', 'sequence'): 'التسلسل',
    ('flousflow.document', 'color'): 'اللون',
    ('flousflow.document', 'folder_id'): 'المجلد',
    ('flousflow.document', 'parent_path'): 'مسار الأب',
    ('flousflow.document', 'children_ids'): 'المجلدات الفرعية',
    ('flousflow.document', 'attachment_id'): 'المرفق',
    ('flousflow.document', 'datas'): 'محتوى الملف',
    ('flousflow.document', 'mimetype'): 'نوع الملف',
    ('flousflow.document', 'file_size'): 'حجم الملف',
    ('flousflow.document', 'checksum'): 'المجموع الاختباري (SHA1)',
    ('flousflow.document', 'index_content'): 'المحتوى المفهرس',
    ('flousflow.document', 'file_extension'): 'امتداد الملف',
    ('flousflow.document', 'previous_attachment_ids'): 'السجل السابق',
    ('flousflow.document', 'current_revision_uuid'): 'معرف المراجعة الحالية',
    ('flousflow.document', 'url'): 'رابط',
    ('flousflow.document', 'url_preview_image'): 'صورة معاينة الرابط',
    ('flousflow.document', 'owner_id'): 'المالك',
    ('flousflow.document', 'access_internal'): 'صلاحيات المستخدمين الداخليين',
    ('flousflow.document', 'access_via_link'): 'صلاحيات الوصول عبر الرابط',
    ('flousflow.document', 'is_access_via_link_hidden'): 'إخفاء خيار الوصول عبر الرابط',
    ('flousflow.document', 'access_ids'): 'الوصول المسموح',
    ('flousflow.document', 'access_token'): 'رمز المستند',
    ('flousflow.document', 'access_url'): 'رابط الوصول',
    ('flousflow.document', 'lock_uid'): 'مقفل بواسطة',
    ('flousflow.document', 'request_activity_id'): 'نشاط الطلب',
    ('flousflow.document', 'requestee_partner_id'): 'شريك الطلب',
    ('flousflow.document', 'trashed'): 'في السلة',
    ('flousflow.document', 'trash_date'): 'تاريخ السلة',
    ('flousflow.document', 'deletion_date'): 'الحذف المجدول',
    ('flousflow.document', 'is_recent'): 'حديث',
    ('flousflow.document', 'alias_id'): 'الاسم المستعار للبريد',
    ('flousflow.document', 'alias_name'): 'اسم الاسم المستعار',
    ('flousflow.document', 'alias_domain_id'): 'نطاق الاسم المستعار',
    ('flousflow.document', 'alias_domain'): 'اسم نطاق الاسم المستعار',
    ('flousflow.document', 'alias_email'): 'البريد المستعار',
    ('flousflow.document', 'alias_tag_ids'): 'الوسوم المطبقة على مستندات البريد',
    ('flousflow.document', 'user_permission'): 'صلاحية المستخدم',
    ('flousflow.document', 'user_folder_id'): 'الأب',
    ('flousflow.document', 'user_can_move'): 'يمكن نقله',
    ('flousflow.document', 'tag_ids'): 'الوسوم',
    ('flousflow.document', 'partner_id'): 'جهة الاتصال',
    ('flousflow.document', 'res_model'): 'نموذج المورد',
    ('flousflow.document', 'res_id'): 'المورد',
    ('flousflow.document', 'res_name'): 'اسم المورد',
    ('flousflow.document', 'company_id'): 'الشركة',
    ('flousflow.document', 'favorited_ids'): 'مفضل لدى',
    ('flousflow.document', 'is_favorited'): 'مفضل',
    ('flousflow.document', 'preview_src'): 'مصدر المعاينة',
    ('flousflow.document', 'create_activity_option'): 'إنشاء نشاط جديد',
    ('flousflow.document', 'create_activity_type_id'): 'نوع النشاط',
    ('flousflow.document', 'create_activity_summary'): 'الملخص',
    ('flousflow.document', 'create_activity_note'): 'ملاحظة',
    ('flousflow.document', 'create_activity_user_id'): 'المسؤول',
    ('flousflow.document', 'create_activity_date_deadline_range'): 'الاستحقاق في',
    ('flousflow.document', 'create_activity_date_deadline_range_type'): 'نوع الاستحقاق',

    # ============ flousflow.document.tag ============
    ('flousflow.document.tag', 'name'): 'الاسم',
    ('flousflow.document.tag', 'color'): 'اللون',
    ('flousflow.document.tag', 'sequence'): 'التسلسل',
    ('flousflow.document.tag', 'tooltip'): 'تلميح',
    ('flousflow.document.tag', 'document_ids'): 'المستندات',

    # ============ flousflow.document.access ============
    ('flousflow.document.access', 'document_id'): 'المستند',
    ('flousflow.document.access', 'partner_id'): 'الشريك',
    ('flousflow.document.access', 'role'): 'الدور',
    ('flousflow.document.access', 'expiration_date'): 'تاريخ الانتهاء',
    ('flousflow.document.access', 'last_access_date'): 'آخر وصول',

    # ============ flousflow.document.access.tracking ============
    ('flousflow.document.access.tracking', 'user_id'): 'المستخدم',
    ('flousflow.document.access.tracking', 'changes'): 'التغييرات',
    ('flousflow.document.access.tracking', 'documents'): 'معرفات المستندات المتأثرة',

    # ============ flousflow.document.sharing ============
    ('flousflow.document.sharing', 'document_ids'): 'المستندات',
    ('flousflow.document.sharing', 'owner_id'): 'المالك',
    ('flousflow.document.sharing', 'access_internal'): 'المستخدمون الداخليون',
    ('flousflow.document.sharing', 'access_via_link'): 'الوصول عبر الرابط',
    ('flousflow.document.sharing', 'access_via_link_mode'): 'وضع الوصول عبر الرابط',
    ('flousflow.document.sharing', 'is_access_via_link_hidden'): 'إخفاء خيار الوصول عبر الرابط',
    ('flousflow.document.sharing', 'invite_partner_ids'): 'دعوة الشركاء',
    ('flousflow.document.sharing', 'invite_role'): 'الدور',
    ('flousflow.document.sharing', 'invite_notify'): 'إشعار',
    ('flousflow.document.sharing', 'invite_notify_message'): 'رسالة الإشعار',
    ('flousflow.document.sharing', 'share_access_ids'): 'مشاركة الوصول',
    ('flousflow.document.sharing', 'is_readonly'): 'للقراءة فقط',
    ('flousflow.document.sharing', 'is_single'): 'مفرد',
    ('flousflow.document.sharing', 'is_folder_only'): 'مجلدات فقط',
    ('flousflow.document.sharing', 'has_warning_link_with_more_rights'): 'تحذير الرابط بصلاحيات أكبر',
    ('flousflow.document.sharing', 'has_warning_partners_without_access'): 'تحذير الشركاء بدون وصول',

    # ============ flousflow.document.sharing.access ============
    ('flousflow.document.sharing.access', 'documents_sharing_id'): 'مشاركة المستندات',
    ('flousflow.document.sharing.access', 'partner_id'): 'الشريك',
    ('flousflow.document.sharing.access', 'role'): 'الدور',
    ('flousflow.document.sharing.access', 'expiration_date'): 'تاريخ الانتهاء',
    ('flousflow.document.sharing.access', 'original_expiration_date'): 'تاريخ الانتهاء الأصلي',
    ('flousflow.document.sharing.access', 'is_deleted'): 'محذوف',
    ('flousflow.document.sharing.access', 'has_user'): 'لديه مستخدم',
    ('flousflow.document.sharing.access', 'is_readonly'): 'للقراءة فقط',
    ('flousflow.document.sharing.access', 'is_on_single_document'): 'على مستند واحد',

    # ============ flousflow.document.operation ============
    ('flousflow.document.operation', 'document_ids'): 'المستندات',
    ('flousflow.document.operation', 'operation'): 'العملية',
    ('flousflow.document.operation', 'destination_folder_id'): 'المجلد الوجهة',
    ('flousflow.document.operation', 'access_internal'): 'صلاحيات الوجهة الداخلية',
    ('flousflow.document.operation', 'access_via_link'): 'صلاحيات الوجهة عبر الرابط',
    ('flousflow.document.operation', 'user_permission'): 'صلاحية مستخدم الوجهة',
    ('flousflow.document.operation', 'is_access_via_link_hidden'): 'إخفاء خيار الوصول عبر الرابط',

    # ============ flousflow.document.request.wizard ============
    ('flousflow.document.request.wizard', 'name'): 'الاسم',
    ('flousflow.document.request.wizard', 'partner_id'): 'جهة الاتصال',
    ('flousflow.document.request.wizard', 'requestee_id'): 'المطلوب منه',
    ('flousflow.document.request.wizard', 'folder_id'): 'المجلد',
    ('flousflow.document.request.wizard', 'tag_ids'): 'الوسوم',
    ('flousflow.document.request.wizard', 'res_model'): 'نموذج المورد',
    ('flousflow.document.request.wizard', 'res_id'): 'معرف المورد',
    ('flousflow.document.request.wizard', 'activity_type_id'): 'نوع النشاط',
    ('flousflow.document.request.wizard', 'activity_date_deadline_range'): 'الاستحقاق في',
    ('flousflow.document.request.wizard', 'activity_date_deadline_range_type'): 'نوع الاستحقاق',
    ('flousflow.document.request.wizard', 'activity_note'): 'الرسالة',

    # ============ flousflow.document.link.to.record.wizard ============
    ('flousflow.document.link.to.record.wizard', 'document_ids'): 'المستندات',
    ('flousflow.document.link.to.record.wizard', 'model_id'): 'النموذج',
    ('flousflow.document.link.to.record.wizard', 'resource_ref'): 'السجل',

    # ============ flousflow.document.delete.wizard ============
    ('flousflow.document.delete.wizard', 'document_ids'): 'المستندات',
    ('flousflow.document.delete.wizard', 'document_count'): 'عدد المستندات',

    # ============ res.config.settings ============
    ('res.config.settings', 'flousflow_documents_deletion_delay'): 'مدة الحذف (أيام)',
}


# ──────────────────────────────────────────────────────────
# VIEW STRING TRANSLATION MAP
# key: English view string → Arabic
# Applied to ir.ui.view arch_db (string="..." attributes)
# ──────────────────────────────────────────────────────────
VIEW_STRING_TRANSLATIONS = {
    # Form view
    'Document': 'مستند',
    'Share': 'مشاركة',
    'Move / Copy': 'نقل / نسخ',
    'Link to Record': 'ربط بسجل',
    'Request a file': 'طلب ملف',
    'Move to Trash': 'نقل إلى السلة',
    'Restore': 'استعادة',
    'Delete Forever': 'حذف نهائي',
    'Favorite': 'مفضلة',
    'Lock': 'قفل',
    'Unlock': 'فتح القفل',
    'Resource Model': 'نموذج المورد',
    'Resource': 'المورد',
    'File': 'ملف',
    'Access': 'الوصول',
    'Owner': 'المالك',
    'Email Alias': 'الاسم المستعار للبريد',
    'Create Alias': 'إنشاء اسم مستعار',
    'Partner Access': 'وصول الشركاء',
    'Details': 'التفاصيل',
    'Folder Color': 'لون المجلد',
    'Activities': 'الأنشطة',

    # New Folder / Rename / Add URL dialogs
    'New Folder': 'مجلد جديد',
    'Folder Name': 'اسم المجلد',
    'Parent Folder': 'المجلد الأب',
    'Internal Users Rights': 'صلاحيات المستخدمين الداخليين',
    'Create': 'إنشاء',
    'Cancel': 'إلغاء',
    'Rename': 'إعادة تسمية',
    'Save': 'حفظ',
    'Add URL': 'إضافة رابط',

    # Control panel New menu
    'Upload': 'رفع',
    'Link': 'رابط',
    'Request': 'طلب',
    'Folder': 'مجلد',

    # List / search
    'Documents': 'المستندات',
    'Linked Model': 'النموذج المرتبط',
    'Search': 'بحث',
    'My Documents': 'مستنداتي',
    'Shared with me': 'المشاركة معي',
    'Favorites': 'المفضلة',
    'Recent': 'الأخيرة',
    'Folders': 'المجلدات',
    'Files': 'الملفات',
    'URLs': 'الروابط',
    'Tag': 'وسم',
    'Type': 'النوع',
    'Company': 'الشركة',

    # Tags views
    'Tags': 'الوسوم',
    'Search Tags': 'بحث الوسوم',

    # Settings
    'Deletion delay': 'مدة الحذف',
    'Days': 'أيام',

    # Share wizard
    'Internal users': 'المستخدمون الداخليون',
    'Access through link': 'الوصول عبر الرابط',
    'Invited partners': 'الشركاء المدعوون',

    # Move / Copy wizard
    'Access Rights (optional)': 'صلاحيات الوصول (اختياري)',
    'Destination Folder': 'المجلد الوجهة',
    'Confirm': 'تأكيد',

    # Request-a-file wizard
    'Requested from': 'المطلوب منه',
    'Related contact': 'جهة الاتصال',
    'Activity': 'النشاط',

    # Link to record wizard
    'Target Record': 'السجل المستهدف',
    'Model': 'النموذج',
    'Record': 'السجل',

    # Placeholders
    'Document name...': 'اسم المستند...',
    'Folder name...': 'اسم المجلد...',
    'e.g. invoices': 'مثال: فواتير',
    'e.g. Signed contract scan': 'مثال: مسح عقد موقع',
    'https://...': 'https://...',
}


# ──────────────────────────────────────────────────────────
# MENU NAME TRANSLATION MAP
# key: English menu name → Arabic
# ──────────────────────────────────────────────────────────
MENU_TRANSLATIONS = {
    'Documents': 'المستندات',
    'Trash': 'السلة',
    'Configuration': 'التكوين',
    'Structure': 'الهيكل',
    'Tags': 'الوسوم',
    'Settings': 'الإعدادات',
}


# ──────────────────────────────────────────────────────────
# SELECTION VALUE TRANSLATION MAP
# key: (model_name, field_name, selection_value) → Arabic
# ──────────────────────────────────────────────────────────
SELECTION_TRANSLATIONS = {
    # flousflow.document.type
    ('flousflow.document', 'type', 'url'): 'رابط',
    ('flousflow.document', 'type', 'binary'): 'ملف',
    ('flousflow.document', 'type', 'folder'): 'مجلد',

    # access levels
    ('flousflow.document', 'access_internal', 'view'): 'مشاهد',
    ('flousflow.document', 'access_internal', 'edit'): 'محرر',
    ('flousflow.document', 'access_internal', 'none'): 'لا أحد',
    ('flousflow.document', 'access_via_link', 'view'): 'مشاهد',
    ('flousflow.document', 'access_via_link', 'edit'): 'محرر',
    ('flousflow.document', 'access_via_link', 'none'): 'لا أحد',
    ('flousflow.document', 'user_permission', 'edit'): 'محرر',
    ('flousflow.document', 'user_permission', 'view'): 'مشاهد',
    ('flousflow.document', 'user_permission', 'none'): 'لا أحد',

    # due type
    ('flousflow.document', 'create_activity_date_deadline_range_type', 'days'): 'أيام',
    ('flousflow.document', 'create_activity_date_deadline_range_type', 'weeks'): 'أسابيع',
    ('flousflow.document', 'create_activity_date_deadline_range_type', 'months'): 'شهور',

    # roles
    ('flousflow.document.access', 'role', 'view'): 'مشاهد',
    ('flousflow.document.access', 'role', 'edit'): 'محرر',

    # sharing
    ('flousflow.document.sharing', 'access_internal', 'view'): 'مشاهد',
    ('flousflow.document.sharing', 'access_internal', 'edit'): 'محرر',
    ('flousflow.document.sharing', 'access_internal', 'none'): 'لا أحد',
    ('flousflow.document.sharing', 'access_via_link', 'view'): 'مشاهد',
    ('flousflow.document.sharing', 'access_via_link', 'edit'): 'محرر',
    ('flousflow.document.sharing', 'access_via_link', 'none'): 'لا أحد',
    ('flousflow.document.sharing', 'access_via_link_mode', 'discoverable'): 'قابل للاكتشاف',
    ('flousflow.document.sharing', 'access_via_link_mode', 'hidden'): 'مخفي',
    ('flousflow.document.sharing', 'invite_role', 'view'): 'مشاهد',
    ('flousflow.document.sharing', 'invite_role', 'edit'): 'محرر',
    ('flousflow.document.sharing.access', 'role', 'view'): 'مشاهد',
    ('flousflow.document.sharing.access', 'role', 'edit'): 'محرر',

    # operation wizard
    ('flousflow.document.operation', 'operation', 'move'): 'نقل إلى',
    ('flousflow.document.operation', 'operation', 'copy'): 'نسخ في',
    ('flousflow.document.operation', 'access_internal', 'view'): 'مشاهد',
    ('flousflow.document.operation', 'access_internal', 'edit'): 'محرر',
    ('flousflow.document.operation', 'access_internal', 'none'): 'لا أحد',
    ('flousflow.document.operation', 'access_via_link', 'view'): 'مشاهد',
    ('flousflow.document.operation', 'access_via_link', 'edit'): 'محرر',
    ('flousflow.document.operation', 'access_via_link', 'none'): 'لا أحد',
    ('flousflow.document.operation', 'user_permission', 'edit'): 'محرر',
    ('flousflow.document.operation', 'user_permission', 'view'): 'مشاهد',
    ('flousflow.document.operation', 'user_permission', 'none'): 'لا أحد',

    # request wizard due type
    ('flousflow.document.request.wizard', 'activity_date_deadline_range_type', 'days'): 'أيام',
    ('flousflow.document.request.wizard', 'activity_date_deadline_range_type', 'weeks'): 'أسابيع',
    ('flousflow.document.request.wizard', 'activity_date_deadline_range_type', 'months'): 'شهور',
}


# ──────────────────────────────────────────────────────────
# ACTION NAME TRANSLATION MAP
# key: English action name → Arabic
# Applied to ir.actions.act_window.name (JSONB), shown in breadcrumbs
# ──────────────────────────────────────────────────────────
ACTIONS_TRANSLATIONS = {
    'Documents': 'المستندات',
    'Trash': 'السلة',
    'Add Folder': 'مجلد جديد',
    'Add URL': 'إضافة رابط',
    'Tags': 'الوسوم',
}


def _install_action_arabic_translations(env):
    """Inject Arabic translations for act_window names via JSONB."""
    _logger.info('Installing Arabic action name translations...')
    cr = env.cr
    updated = 0
    for en_name, ar_name in ACTIONS_TRANSLATIONS.items():
        cr.execute("""
            UPDATE ir_act_window
            SET name = COALESCE(name, jsonb_build_object('en_US', %s))
                       || jsonb_build_object('ar_001', %s)
            WHERE name->>'en_US' = %s
              AND (name->>'ar_001' IS NULL OR name->>'ar_001' != %s)
        """, (en_name, ar_name, en_name, ar_name))
        if cr.rowcount:
            updated += 1
    _logger.info('Arabic action translations installed: %d actions updated.', updated)


# ──────────────────────────────────────────────────────────
# Application functions
# ──────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────
# KANBAN CARD TEXT-NODE TRANSLATION MAP
# Odoo 19 kanban card templates render text nodes (not string="..." attributes)
# that the string="" regex above cannot catch. We replace these exact text
# snippets inside the ar_001 arch so cards show Arabic type labels.
# key: English snippet → Arabic snippet
# ──────────────────────────────────────────────────────────
VIEW_TEXT_TRANSLATIONS = {
    '>Folder</t>': '>مجلد</t>',
    '>File</t>': '>ملف</t>',
    '>Link</t>': '>رابط</t>',
    ' bytes': ' بايت',
    # portal page text nodes
    '>My Documents</h2>': '>مستنداتي</h2>',
    '>Document</th>': '>المستند</th>',
    '>Size</th>': '>الحجم</th>',
    '>Date</th>': '>التاريخ</th>',
    '>Download</th>': '>التحميل</th>',
    '>Download</a>': '>تحميل</a>',
    'No documents have been shared with you yet.':
        'لا توجد مستندات تمت مشاركتها معك بعد.',
}


def _install_view_arabic_translations(env):
    """Inject Arabic translations into ir.ui.view arch_db for view strings."""
    _logger.info('Installing Arabic view string translations...')
    cr = env.cr

    def _translate_string(match):
        en = match.group(1)
        ar = VIEW_STRING_TRANSLATIONS.get(en)
        if ar:
            ar_escaped = (ar.replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('"', '&quot;'))
            return 'string="' + ar_escaped + '"'
        return match.group(0)

    def _translate_text(arch):
        """Replace known kanban card text nodes with Arabic."""
        for en, ar in VIEW_TEXT_TRANSLATIONS.items():
            arch = arch.replace(en, ar)
        return arch

    cr.execute("""
        SELECT v.id, v.arch_db->>'en_US' AS en_arch, v.name
        FROM ir_ui_view v
        JOIN ir_model_data md ON md.res_id = v.id
            AND md.model = 'ir.ui.view'
        WHERE md.module = 'flousflow_documents'
          AND v.arch_db->>'en_US' IS NOT NULL
        ORDER BY v.name
    """)
    rows = cr.fetchall()
    _logger.info('Found %d Documents views', len(rows))

    updated = 0
    for view_id, en_arch, vname in rows:
        has_str = any(en_str in en_arch
                      for en_str in VIEW_STRING_TRANSLATIONS)
        has_text = any(en_txt in en_arch
                       for en_txt in VIEW_TEXT_TRANSLATIONS)
        if not has_str and not has_text:
            continue

        ar_arch = re.sub(r'(?:string|placeholder)="([^"]*)"',
                         _translate_string, en_arch)
        ar_arch = _translate_text(ar_arch)
        if ar_arch == en_arch:
            continue

        ar_json = json.dumps({"ar_001": ar_arch})
        cr.execute("""
            UPDATE ir_ui_view
            SET arch_db = COALESCE(arch_db, '{}'::jsonb) || %s::jsonb
            WHERE id = %s
        """, (ar_json, view_id))
        if cr.rowcount:
            updated += 1

    _logger.info('Arabic view translations installed: %d views updated.', updated)


def _install_menu_arabic_translations(env):
    """Inject Arabic translations for menu names via JSONB on ir.ui.menu.name."""
    _logger.info('Installing Arabic menu name translations...')
    cr = env.cr
    updated = 0
    for en_name, ar_name in MENU_TRANSLATIONS.items():
        cr.execute("""
            UPDATE ir_ui_menu
            SET name = COALESCE(name, jsonb_build_object('en_US', %s))
                       || jsonb_build_object('ar_001', %s)
            WHERE name->>'en_US' = %s
              AND (name->>'ar_001' IS NULL OR name->>'ar_001' != %s)
        """, (en_name, ar_name, en_name, ar_name))
        if cr.rowcount:
            updated += 1
    _logger.info('Arabic menu translations installed: %d menus updated.', updated)


def _install_selection_arabic_translations(env):
    """Inject Arabic translations for selection/statusbar values."""
    _logger.info('Installing Arabic selection translations...')
    cr = env.cr

    updated = 0
    for (model_name, field_name, sel_value), arb_label in \
            SELECTION_TRANSLATIONS.items():
        cr.execute("""
            UPDATE ir_model_fields_selection s
            SET name = s.name || jsonb_build_object('ar_001', %s)
            FROM ir_model_fields f
            WHERE f.id = s.field_id
              AND f.name = %s
              AND f.model = %s
              AND s.value = %s
              AND (s.name->>'ar_001' IS NULL
                   OR s.name->>'ar_001' != %s)
        """, (arb_label, field_name, model_name, sel_value, arb_label))
        if cr.rowcount:
            updated += 1

    _logger.info(
        'Arabic selection translations installed: %d values updated.', updated
    )


def _install_arabic_translations(env):
    """Install Arabic (ar_001) translations for all Documents fields
    and view strings."""
    _logger.info('Installing Arabic translations for Documents fields...')

    # ── Phase 1: Field Labels ──
    updated = 0
    for (model_name, field_name), arb_label in FIELD_TRANSLATIONS.items():
        field = env['ir.model.fields'].search([
            ('model', '=', model_name),
            ('name', '=', field_name),
        ], limit=1)
        if field:
            env.cr.execute("""
                UPDATE ir_model_fields
                SET field_description = field_description || %s::jsonb
                WHERE id = %s
                  AND (field_description->>'ar_001' IS NULL
                       OR field_description->>'ar_001' != %s)
            """, (
                '{"ar_001": "' + arb_label.replace('"', '\\"') + '"}',
                field.id,
                arb_label,
            ))
            if env.cr.rowcount:
                updated += 1

    _logger.info('Arabic translations installed: %d fields updated.', updated)

    # ── Phase 2: View Strings ──
    _install_view_arabic_translations(env)

    # ── Phase 3: Selection/Statusbar Values ──
    _install_selection_arabic_translations(env)

    # ── Phase 4: Menu Names ──
    _install_menu_arabic_translations(env)

    # ── Phase 5: Action (act_window) Names ──
    _install_action_arabic_translations(env)
