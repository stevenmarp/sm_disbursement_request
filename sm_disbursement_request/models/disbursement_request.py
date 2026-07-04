# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SmDisbursementRequest(models.Model):
    _name = 'sm.disbursement.request'
    _description = 'Disbursement Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='New', copy=False, readonly=True, tracking=True)
    request_type = fields.Selection(
        [
            ('advance', 'Employee Advance'),
            ('reimbursement', 'Reimbursement'),
            ('settlement', 'Advance Settlement'),
        ],
        required=True,
        default='advance',
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('accounted', 'Accounted'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        tracking=True,
    )
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    due_date = fields.Date(tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', compute='_compute_employee_data', store=True, readonly=False)
    department_id = fields.Many2one('hr.department', compute='_compute_employee_data', store=True, readonly=False)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)
    journal_id = fields.Many2one(
        'account.journal',
        required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        tracking=True,
    )
    clearing_account_id = fields.Many2one(
        'account.account',
        string='Advance / Payable Account',
        required=True,
        domain="[('company_ids', 'in', company_id)]",
        tracking=True,
    )
    advance_id = fields.Many2one(
        'sm.disbursement.request',
        string='Advance Request',
        domain="[('request_type', '=', 'advance'), ('state', 'in', ['accounted', 'paid']), ('employee_id', '=', employee_id)]",
        tracking=True,
    )
    settlement_ids = fields.One2many('sm.disbursement.request', 'advance_id', string='Settlements')
    line_ids = fields.One2many('sm.disbursement.request.line', 'request_id', string='Lines', copy=True)
    move_id = fields.Many2one('account.move', readonly=True, copy=False)
    move_count = fields.Integer(compute='_compute_counts')
    settlement_count = fields.Integer(compute='_compute_counts')
    amount_total = fields.Monetary(compute='_compute_amounts', store=True, recursive=True, tracking=True)
    amount_settled = fields.Monetary(compute='_compute_amounts', store=True, recursive=True)
    amount_residual = fields.Monetary(compute='_compute_amounts', store=True, recursive=True)
    notes = fields.Text()
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.depends('employee_id')
    def _compute_employee_data(self):
        for request in self:
            request.partner_id = request.employee_id.work_contact_id or request.employee_id.user_id.partner_id
            request.department_id = request.employee_id.department_id

    @api.depends('line_ids.amount', 'settlement_ids.amount_total', 'settlement_ids.state')
    def _compute_amounts(self):
        for request in self:
            request.amount_total = sum(request.line_ids.mapped('amount'))
            settled = sum(request.settlement_ids.filtered(lambda item: item.state != 'cancelled').mapped('amount_total'))
            request.amount_settled = settled
            request.amount_residual = request.amount_total - settled if request.request_type == 'advance' else 0.0

    def _compute_counts(self):
        for request in self:
            request.move_count = 1 if request.move_id else 0
            request.settlement_count = len(request.settlement_ids)

    @api.constrains('request_type', 'advance_id')
    def _check_advance_link(self):
        for request in self:
            if request.request_type == 'settlement' and not request.advance_id:
                raise ValidationError(_('Settlement request must be linked to an advance request.'))
            if request.request_type != 'settlement' and request.advance_id:
                raise ValidationError(_('Only settlement requests can be linked to an advance request.'))

    @api.constrains('line_ids')
    def _check_lines(self):
        for request in self:
            if request.state != 'draft' and not request.line_ids:
                raise ValidationError(_('Add at least one disbursement line before processing.'))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = sequence.next_by_code('sm.disbursement.request') or 'New'
        return super().create(vals_list)

    def unlink(self):
        locked = self.filtered(lambda request: request.state != 'draft')
        if locked:
            raise UserError(_('Only draft disbursement requests can be deleted.'))
        return super().unlink()

    def action_submit(self):
        for request in self:
            request._ensure_can_submit()
            request.state = 'submitted'

    def action_approve(self):
        self._check_manager()
        for request in self:
            if request.state != 'submitted':
                raise UserError(_('Only submitted requests can be approved.'))
            request.state = 'approved'

    def action_reset_to_draft(self):
        self._check_manager()
        for request in self:
            if request.move_id:
                raise UserError(_('Request already has a journal entry. Cancel the entry first if you need to revise it.'))
            request.state = 'draft'

    def action_cancel(self):
        self._check_manager()
        for request in self:
            if request.move_id and request.move_id.state == 'posted':
                raise UserError(_('Posted journal entry exists. Cancel it before cancelling this request.'))
            request.state = 'cancelled'

    def action_create_journal_entry(self):
        self._check_manager()
        for request in self:
            request._create_journal_entry()

    def action_mark_paid(self):
        self._check_manager()
        for request in self:
            if request.state != 'accounted':
                raise UserError(_('Only accounted requests can be marked as paid.'))
            request.state = 'paid'

    def action_view_move(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_journal_line')
        action['domain'] = [('id', '=', self.move_id.id)]
        action['views'] = [(False, 'form')]
        action['res_id'] = self.move_id.id
        return action

    def action_view_settlements(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('sm_disbursement_request.action_sm_disbursement_request')
        action['domain'] = [('advance_id', '=', self.id)]
        action['context'] = {
            'default_request_type': 'settlement',
            'default_employee_id': self.employee_id.id,
            'default_advance_id': self.id,
            'default_journal_id': self.journal_id.id,
            'default_clearing_account_id': self.clearing_account_id.id,
        }
        return action

    def _ensure_can_submit(self):
        for request in self:
            if request.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            if not request.line_ids:
                raise UserError(_('Add at least one line before submitting.'))
            if request.amount_total <= 0:
                raise UserError(_('Total amount must be greater than zero.'))
            if request.request_type == 'settlement' and request.amount_total > request.advance_id.amount_residual:
                raise UserError(_('Settlement amount cannot exceed advance residual amount.'))

    def _create_journal_entry(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved requests can create journal entries.'))
        if self.move_id:
            raise UserError(_('Journal entry already exists.'))
        if not self.partner_id:
            raise UserError(_('Employee must have a related contact.'))
        lines = []
        for line in self.line_ids:
            line_vals = {
                'name': line.name or self.name,
                'account_id': line.account_id.id,
                'debit': line.amount,
                'credit': 0.0,
                'partner_id': self.partner_id.id,
            }
            if line.analytic_distribution:
                line_vals['analytic_distribution'] = line.analytic_distribution
            lines.append((0, 0, line_vals))
        lines.append((0, 0, {
            'name': self.name,
            'account_id': self.clearing_account_id.id,
            'debit': 0.0,
            'credit': self.amount_total,
            'partner_id': self.partner_id.id,
        }))
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': self.date,
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'line_ids': lines,
        })
        move.action_post()
        self.write({'move_id': move.id, 'state': 'accounted'})

    def _check_manager(self):
        if not self.env.user.has_group('sm_disbursement_request.group_sm_disbursement_manager'):
            raise UserError(_('Only Disbursement Managers can perform this action.'))
