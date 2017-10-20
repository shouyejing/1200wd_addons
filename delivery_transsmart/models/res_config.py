# -*- coding: utf-8 -*-
##############################################################################
#
#    Delivery Transsmart Ingegration
#    © 2016 - 1200 Web Development <http://1200wd.com/>
#    © 2015 - ONESTEiN BV (<http://www.onestein.nl>)
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
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)

class DeliveryTranssmartConfiguration(models.TransientModel):
    _name = 'delivery.transsmart.config.settings'
    _inherit = 'res.config.settings'

    service_level_time_id = fields.Many2one(
        'delivery.service.level.time',
        string='Default Prebooking Service Level Time',
        help='Default service level time',
    )
    carrier_id = fields.Many2one(
        'res.partner',
        string='Default Prebooking Carrier',
        help='Default carrier',
    )
    disable = fields.Boolean('Disable')
    web_service_transsmart = fields.Many2one(
        'delivery.web.service',
        string='Connection',
        help='Transsmart connection for this Odoo instance'
    )

    @api.multi
    def get_default_transsmart(self):
        ir_values_obj = self.env['ir.values']
        carrier_id = ir_values_obj.get_default('delivery.transsmart', 'transsmart_default_carrier')
        service_level_time_id = ir_values_obj.get_default('delivery.transsmart', 'transsmart_default_service_level')
        web_service_transsmart = ir_values_obj.get_default('delivery.transsmart', 'web_service_transsmart')
        return {
            'carrier_id': carrier_id,
            'service_level_time_id': service_level_time_id,
            'web_service_transsmart': web_service_transsmart,
        }
   
    @api.multi
    def transsmart_default_carrier_id(self):
        ir_values_obj = self.env['ir.values']
        carrier_id = ir_values_obj.get_default('delivery.transsmart', 'transsmart_default_carrier')
        carrier = self.env['res.partner'].browse([carrier_id])
        if carrier:
            return carrier[0].transsmart_id
        else:
            raise Warning(_('No default Default Prebooking Carrier found. Please change Transsmart settings'))

    @api.multi
    def transsmart_default_service_level_time_id(self):
        ir_values_obj = self.env['ir.values']
        service_level_time_id = ir_values_obj.get_default('delivery.transsmart', 'transsmart_default_service_level')
        service = self.env['delivery.service.level.time'].browse([service_level_time_id])
        if service:
            return service[0].transsmart_id
        else:
            raise Warning(_('No default Prebooking Service Level Time found. Please change Transsmart settings'))

    @api.multi
    def set_transsmart_defaults(self):
        ir_values_obj = self.env['ir.values']
        ir_values_obj.set_default('delivery.transsmart', 'transsmart_default_carrier',
                                  self.carrier_id and self.carrier_id.id or None)
        ir_values_obj.set_default('delivery.transsmart', 'transsmart_default_service_level',
                                  self.service_level_time_id and self.service_level_time_id.id or None)
        ir_values_obj.set_default('delivery.transsmart', 'web_service_transsmart',
                                  self.web_service_transsmart and self.web_service_transsmart.id or None)

    def get_transsmart_service(self):
        """
        If no default connection is set and there is only one connection return that connection.
        :return: Transsmart delivery webservice object.
        """
        if self.web_service_transsmart:
            return self.web_service_transsmart
        else:
            wst = self.env['ir.values'].get_default('delivery.transsmart', 'web_service_transsmart')
        if not wst:
            if len(self.env['delivery.web.service'].search([])) == 1:
                return self.env['delivery.web.service'].search([])
            else:
                raise Warning(_('No Transsmart connection information found or no default connection selected'))
        return self.env['delivery.web.service'].browse([wst])

    def get_transsmart_carrier_tag(self):
        return self.env.ref(
                'delivery_transsmart.res_partner_category_transsmart_carrier'
        ).id

    @api.multi
    def sync_transsmart_models(self):
        delivery_service_level_model = self.env['delivery.service.level']
        delivery_service_level_time_model = self.env[
                'delivery.service.level.time']
        res_partner_model = self.env['res.partner']
        transsmart_cost_center_model = self.env['transsmart.cost.center']
        transsmart_package_type_model = self.env['transsmart.package.type']
        local_data = delivery_service_level_model.search([])
        local_transsmart_ids = [local.transsmart_id for local in local_data]
        remote_data = self.get_transsmart_service().receive(
                '/ServiceLevelOther')
        for data in remote_data:
            vals = {'code': data['Code'],
                    'name': data['Name'],
                    'transsmart_id': data['Id'],}
            if not data['Id'] in local_transsmart_ids:
                delivery_service_level_model.create(vals)
                _logger.info("Created transsmart delivery.service.level %s" % (data['Id'],))
            else:
                rec_to_be_updated = local_data.filtered(
                        lambda rec: rec.transsmart_id == data['Id'])
                rec_to_be_updated.write(vals)
                _logger.info("Updated Service Level {}".format(
                    rec_to_be_updated.transsmart_id))

        local_data = delivery_service_level_time_model.search([])
        local_transsmart_ids = [local.transsmart_id for local in local_data]
        remote_data = self.get_transsmart_service().receive(
                '/ServiceLevelTime')
        for data in remote_data:
            vals = {'code': data['Code'],
                    'name': data['Name'],
                    'transsmart_id': data['Id']}
            if not data['Id'] in local_transsmart_ids:
                delivery_service_level_time_model.create(vals)
                _logger.info("Created transsmart delivery.service.level.time %s" % (data['Id'],))
            else:
                rec_to_be_updated = local_data.filtered(
                        lambda rec: rec.transsmart_id == data['Id'])
                rec_to_be_updated.write(vals)
                _logger.info("Updated Service Level Time {}".format(
                    rec_to_be_updated.transsmart_id))

        # this is how you indentify res.partners that are carriers 
        # some carriers have a transsmart_id of 0, we cannot be sure to which
        # carrier in transsmart our local res.partner maps to so we ignore it
        local_data = res_partner_model.search(
                [('transsmart_id', 'not in', [None, 0])])
        local_transsmart_ids = [local.transsmart_id for local in local_data]
        remote_data = self.get_transsmart_service().receive('/Carrier')
        for data in remote_data:
            vals = {'transsmart_code': data['Code'],
                    'name': data['Name'],
                    'supplier': True,
                    'customer': False,
                    'is_company': True,
                    'transsmart_id': data['Id'],
                    'category_id': [(4, self.get_transsmart_carrier_tag())]}
            if not data['Id'] in local_transsmart_ids:
                res_partner_model.create(vals)
                _logger.info("Created transsmart res.partner %s" % (data['Id'],))
            else:
                rec_to_be_updated = local_data.filtered(
                        lambda rec: rec.transsmart_id == data['Id'])
                rec_to_be_updated.write(vals)
                _logger.info("Updated res.partner {}".format(
                    rec_to_be_updated.transsmart_id))

        local_data = transsmart_cost_center_model.search([])
        local_transsmart_ids = [local.transsmart_id for local in local_data]
        remote_data = self.get_transsmart_service().receive('/Costcenter')
        for data in remote_data:
            vals = {'code': data['Code'],
                    'name': data['Name'],
                    'transsmart_id': data['Id']}
            if not data['Id'] in local_transsmart_ids:
                transsmart_cost_center_model.create(vals)
                _logger.info("Created transsmart.cost.center %s" % (data['Code'],))
            else:
                rec_to_be_updated = local_data.filtered(
                    lambda rec: rec.transsmart_id == data['Id'])
                rec_to_be_updated.write(vals)
                _logger.info("Updated transsmart.cost.center {}".format(
                    rec_to_be_updated.transsmart_id))
        # get the packages (box, pallet etc...)
        local_data = transsmart_package_type_model.search([])
        local_transsmart_ids = [local.transsmart_id for local in local_data]
        remote_data = self.get_transsmart_service().receive('/Package')
        for data in remote_data:
            vals = {'name': data['Name'],
                    'package_type': data['Type'],
                    'length': data['Length'],
                    'width': data['Width'],
                    'height': data['Height'],
                    'weight': data['Weight'],
                    'is_default': data['IsDefault'],
                    'transsmart_id': data['Id']}
            if not data['Id'] in local_transsmart_ids:
                transsmart_package_type_model.create(vals)
                _logger.info("Created transsmart.package.type {}".format(
                    data['Id']))
            else:
                rec_to_be_updated = local_data.filtered(
                        lambda rec: rec.transsmart_id == data['Id'])
                rec_to_be_updated.write(vals)
                _logger.info("Updated transsmart.package.type {}".format(
                    data['Id']))
        return True

    @api.multi
    def lookup_transsmart_delivery_carrier(self, transsmart_document):
        if 'ServiceLevelOtherId' not in transsmart_document:
            raise Warning(_('No Service Level Other Id found in Transsmart Document'))
        service_level_other = self.env['delivery.service.level'].\
            search([('transsmart_id','=',transsmart_document['ServiceLevelOtherId'])])
        if len(service_level_other) != 1:
            raise Warning(_('No unique Service Level Other found with transsmart Id %s. Found %d. '
                            'You have to refresh or review the transsmart data!') %
                          (transsmart_document['ServiceLevelOtherId'], len(service_level_other)))

        if 'ServiceLevelTimeId' not in transsmart_document:
            raise Warning(_('No Service Level Time Id found in Transsmart Document'))
        service_level_time = self.env['delivery.service.level.time'].\
            search([('transsmart_id','=',transsmart_document['ServiceLevelTimeId'])])
        if len(service_level_time) != 1:
            raise Warning(_('No unique Service Level Time found with transsmart Id %s. Found %d. '
                            'You have to refresh or review the transsmart data!') %
                          (transsmart_document['ServiceLevelTimeId'], len(service_level_time)))

        if 'CarrierId' not in transsmart_document:
            raise Warning(_('No Carrier Id found in Transsmart Document'))
        carrier = self.env['res.partner'].search([('transsmart_id','=',transsmart_document['CarrierId'])])
        if len(carrier) != 1:
            raise Warning(_('No unique Carrier found with transsmart Id %s. Found %d. '
                            'You have to refresh or review the transsmart data!') %
                          (transsmart_document['CarrierId'],len(carrier)))

        products = self.env['product.product'].search([
            ('service_level_id', '=', service_level_other[0].id), 
            ('service_level_time_id', '=', service_level_time[0].id)
        ])
        if len(products) > 1:
            raise Warning(_('More then one delivery product with Service Level ID %d and Service Level Time ID %d'),
                          (service_level_other[0].id, service_level_time[0].id))
        if len(products) < 1:
            # autocreate product
            products = [self.env['product.product'].create({
                'name': "({} {})".format(service_level_time[0].name, service_level_other[0].name),
                'type': 'service',
                'service_level_id': service_level_other[0].id, 
                'service_level_time_id': service_level_time[0].id
            })]

        delivery_carrier = self.env['delivery.carrier'].search(
            [('partner_id','=', carrier[0].id), ('product_id','=',products[0].id)])
        if len(delivery_carrier) > 1:
            raise Warning(_('More then one delivery carrier found for partner %d and product %d'),
                          (carrier[0].id, products[0].id))
        if len(delivery_carrier) < 1:
            # autcreate delivery.carrier
            delivery_carrier = self.env['delivery.carrier'].create({
                'name': carrier[0].name + ' ' + products[0].name,
                'partner_id': carrier[0].id,
                'product_id': products[0].id
            })

        return delivery_carrier[0]


class ResCompany(models.Model):
    _inherit = 'res.company'

    transsmart_enabled = fields.Boolean(
        'Use Transsmart',
        default=True)
