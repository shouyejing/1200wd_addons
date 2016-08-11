# -*- coding: utf-8 -*-
#
#    Sales - Actual Costs and Margins
#    Copyright (C) 2015 November
#    1200 Web Development
#    http://1200wd.com/
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class product_template(models.Model):
    _inherit = "product.template"

    @api.one
    def calculate_costs(self):
        # Calculate extra costs from product_extra_costs table
        pc = self.env['product.cost'].search([('product_tmpl_id', '=', self.id)])
        self.extra_costs = 0
        for r in pc:
            self.extra_costs += r.costs
        _logger.debug("1200wd - Updating extra costs of product_tmpl_id {} to {}".format(self.id, self.extra_costs))
        return True

    @api.one
    @api.depends('standard_price', 'extra_costs')
    def calculate_actual_costs(self):
        self.actual_cost = self.standard_price + self.extra_costs
        _logger.debug("1200wd - Updating actual cost of product_tmpl_id {} to {}".format(self.id, self.actual_cost))
        return True

    extra_costs = fields.Float(string="Extra costs", readonly=True,
                               digits_compute=dp.get_precision('Product Price'),
                               compute="calculate_costs", store=True,
                               help="Total extra costs per product. (i.e. for shipping, import tax, currency risks)")
    actual_cost = fields.Float(string="Actual Cost Price", readonly=True,
                               digits_compute=dp.get_precision('Product Price'),
                               compute="calculate_actual_costs", store=True,
                               help="Actual Cost Price for this product, including extra costs for shipping, import, "
                                    "labour, currency risks, etc.")


class product_cost_type(models.Model):
    _name = "product.cost.type"

    name = fields.Char(string="Extra Cost Type", size=64, required=True)
    active = fields.Boolean(string='Active', default=True)
    default_costs = fields.Float(string="Default Extra costs", digits=dp.get_precision('Product Price'))


class product_cost(models.Model):
    _name = "product.cost"

    product_tmpl_id = fields.Many2one('product.template', 'Product')
    type = fields.Many2one('product.cost.type', 'Type', ondelete='restrict')
    costs = fields.Float(string="Extra costs", digits=dp.get_precision('Product Price'))
    name = fields.Text(string="Description")

    _sql_constraints = [
        ('product_type_unique', 'unique(product_tmpl_id, type)', 'Product and Cost Type must be an unique combination')
    ]

    def _update_product_costs(self, ptids):
        """
        Calculate extra costs and update product template. Input is a list of product template IDs.
        """
        for ptid in ptids:
            pc = self.env['product.cost'].search([('product_tmpl_id', '=', ptid)])
            extra_costs = 0
            for r in pc:
                extra_costs += r.costs
            data = {
                'extra_costs': extra_costs,
            }
            self.env['product.template'].browse(ptid).write(data)
            _logger.debug("1200wd - Updating extra costs of product_tmpl_id {} to {}".format(ptid, extra_costs))
        return True

    @api.multi
    def write(self, vals):
        ps = set([t.product_tmpl_id.id for t in self])
        res = super(product_cost, self).write(vals)
        self._update_product_costs(ps)
        return res

    @api.model
    def create(self, vals):
        res = super(product_cost, self).create(vals)
        self._update_product_costs([vals['product_tmpl_id']])
        return res

    @api.multi
    def unlink(self):
        ps = set([t.product_tmpl_id.id for t in self])
        res = super(product_cost, self).unlink()
        self._update_product_costs(ps)
        return res

    @api.one
    @api.onchange('type')
    def update_default_costs(self):
        if self.type.default_costs:
            self.costs = self.type.default_costs