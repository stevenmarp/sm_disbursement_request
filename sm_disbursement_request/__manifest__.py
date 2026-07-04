# -*- coding: utf-8 -*-
{
    'name': 'Disbursement Request',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Employee advances, reimbursements, settlements, approvals, and accounting entries',
    'description': """
Disbursement Request
=======================

Manage employee cash advances and reimbursements with approval workflow and accounting entries.

Main Features
-------------
* Employee advance request with line details, expense accounts, analytic distribution, and attachments.
* Reimbursement request for employee expense claims.
* Settlement request linked to an advance with automatic residual tracking.
* Approval flow from draft, submitted, approved, accounted, paid, and cancelled.
* Journal entry creation from approved request.
* Smart buttons for journal entries and settlements.
* Manager controls with access groups.
    """,
    'author': 'Steven Marp',
    'website': 'https://apps.odoo.com/apps/modules/browse?author=Steven Marp',
    'license': 'OPL-1',
    'depends': ['account', 'analytic', 'hr', 'mail'],
    'data': [
        'security/disbursement_security.xml',
        'security/ir.model.access.csv',
        'data/disbursement_sequence.xml',
        'views/disbursement_request_views.xml',
        'views/disbursement_menus.xml',
    ],
    'images': [
        'static/description/banner.gif',
        'static/description/icon.png',
        'static/description/image.png',
        'static/description/screenshot_01.png',
        'static/description/screenshot_02.png',
        'static/description/screenshot_03.png',
        'static/description/screenshot_04.png',
        'static/description/screenshot_05.png',
        'static/description/screenshot_06.png',
        'static/description/screenshot_07.png',
        'static/description/screenshot_08.png',
        'static/description/screenshot_09.png',
        'static/description/screenshot_10.png',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'price': 19.00,
    'currency': 'USD',
}
