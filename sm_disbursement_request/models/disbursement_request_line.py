# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SmDisbursementRequestLine(models.Model):
    _name = 'sm.disbursement.request.line'
    _inherit = ['analytic.mixin']
    _description = 'Disbursement Request Line'
    _order = 'request_id, id'

    request_id = fields.Many2one('sm.disbursement.request', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    account_id = fields.Many2one(
        'account.account',
        required=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one('res.currency', related='request_id.currency_id', store=True)
    company_id = fields.Many2one('res.company', related='request_id.company_id', store=True)
    employee_id = fields.Many2one('hr.employee', related='request_id.employee_id', store=True)
    request_type = fields.Selection(related='request_id.request_type', store=True)
    state = fields.Selection(related='request_id.state', store=True)

    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_('Line amount must be greater than zero.'))
