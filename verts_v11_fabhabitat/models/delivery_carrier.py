import logging
import time

from odoo import api, models, fields, _, tools
from odoo.exceptions import UserError
from odoo.tools import pdf

from odoo.addons.delivery_fedex.models.fedex_request import FedexRequest
from odoo.addons.delivery_ups.models.ups_request import UPSRequest, Package


_logger = logging.getLogger(__name__)


FEDEX_CURR_MATCH = {
    u'UYU': u'UYP',
    u'XCD': u'ECD',
    u'MXN': u'NMP',
    u'KYD': u'CID',
    u'CHF': u'SFR',
    u'GBP': u'UKL',
    u'IDR': u'RPA',
    u'DOP': u'RDD',
    u'JPY': u'JYE',
    u'KRW': u'WON',
    u'SGD': u'SID',
    u'CLP': u'CHP',
    u'JMD': u'JAD',
    u'KWD': u'KUD',
    u'AED': u'DHS',
    u'TWD': u'NTD',
    u'ARS': u'ARN',
    u'LVL': u'EURO',
}

class ProviderFedex(models.Model):
    _inherit = 'delivery.carrier'
    
    carrier_code = fields.Char('Carrier Code')
    
    _sql_constraints = [
        ('carrier_code_uniq', 'unique (carrier_code)', 'The code of the carrier must be unique !')
    ]
    
    
    def fedex_send_shipping(self, pickings):
        res = []

        for picking in pickings:
            if not picking.ship_label_bool:

                srm = FedexRequest(self.log_xml, request_type="shipping", prod_environment=self.prod_environment)
                superself = self.sudo()
                srm.web_authentication_detail(superself.fedex_developer_key, superself.fedex_developer_password)
                srm.client_detail(superself.fedex_account_number, superself.fedex_meter_number)
    
                srm.transaction_detail(picking.id)
    
                # FedEx forbids the use of different packagings in the same shippign
                picking.check_packages_are_identical()
    
                package_type = picking.package_ids and picking.package_ids[0].packaging_id.shipper_package_code or self.fedex_default_packaging_id.shipper_package_code
                srm.shipment_request(self.fedex_droppoff_type, self.fedex_service_type, package_type, self.fedex_weight_unit, self.fedex_saturday_delivery)
                srm.set_currency(_convert_curr_iso_fdx(picking.company_id.currency_id.name))
                srm.set_shipper(picking.company_id.partner_id, picking.picking_type_id.warehouse_id.partner_id)
                srm.set_recipient(picking.partner_id)
    
                srm.shipping_charges_payment(superself.fedex_account_number)
    
                srm.shipment_label('COMMON2D', self.fedex_label_file_type, self.fedex_label_stock_type, 'TOP_EDGE_OF_TEXT_FIRST', 'SHIPPING_LABEL_FIRST')
    
                order_currency = picking.sale_id.currency_id or picking.company_id.currency_id
    
                net_weight = _convert_weight(picking.shipping_weight, self.fedex_weight_unit)
    
                # Commodities for customs declaration (international shipping)
                if self.fedex_service_type in ['INTERNATIONAL_ECONOMY', 'INTERNATIONAL_PRIORITY']:
    
                    commodity_currency = order_currency
                    total_commodities_amount = 0.0
                    commodity_country_of_manufacture = picking.picking_type_id.warehouse_id.partner_id.country_id.code
    
                    for operation in picking.move_line_ids:
                        commodity_amount = order_currency.compute(operation.product_id.list_price, commodity_currency)
                        total_commodities_amount += (commodity_amount * operation.qty_done)
                        commodity_description = operation.product_id.name
                        commodity_number_of_piece = '1'
                        commodity_weight_units = self.fedex_weight_unit
                        commodity_weight_value = _convert_weight(operation.product_id.weight * operation.qty_done, self.fedex_weight_unit)
                        commodity_quantity = operation.qty_done
                        commodity_quantity_units = 'EA'
                        srm.commodities(_convert_curr_iso_fdx(commodity_currency.name), commodity_amount, commodity_number_of_piece, commodity_weight_units, commodity_weight_value, commodity_description, commodity_country_of_manufacture, commodity_quantity, commodity_quantity_units)
                    srm.customs_value(_convert_curr_iso_fdx(commodity_currency.name), total_commodities_amount, "NON_DOCUMENTS")
                    srm.duties_payment(picking.picking_type_id.warehouse_id.partner_id.country_id.code, superself.fedex_account_number)
    
                package_count = len(picking.package_ids) or 1
    
                # TODO RIM master: factorize the following crap
    
                ################
                # Multipackage #
                ################
                if package_count > 1:
    
                    # Note: Fedex has a complex multi-piece shipping interface
                    # - Each package has to be sent in a separate request
                    # - First package is called "master" package and holds shipping-
                    #   related information, including addresses, customs...
                    # - Last package responses contains shipping price and code
                    # - If a problem happens with a package, every previous package
                    #   of the shipping has to be cancelled separately
                    # (Why doing it in a simple way when the complex way exists??)
    
                    master_tracking_id = False
                    package_labels = []
                    carrier_tracking_ref = ""
    
                    for sequence, package in enumerate(picking.package_ids, start=1):
    
                        package_weight = _convert_weight(package.shipping_weight, self.fedex_weight_unit)
                        srm.add_package(package_weight, sequence_number=sequence)
                        srm.set_master_package(net_weight, package_count, master_tracking_id=master_tracking_id)
                        request = srm.process_shipment()
                        package_name = package.name or sequence
    
                        warnings = request.get('warnings_message')
                        if warnings:
                            _logger.info(warnings)
    
                        # First package
                        if sequence == 1:
                            if not request.get('errors_message'):
                                master_tracking_id = request['master_tracking_id']
                                package_labels.append((package_name, srm.get_label()))
                                carrier_tracking_ref = request['tracking_number']
                            else:
                                raise UserError(request['errors_message'])
    
                        # Intermediary packages
                        elif sequence > 1 and sequence < package_count:
                            if not request.get('errors_message'):
                                package_labels.append((package_name, srm.get_label()))
                                carrier_tracking_ref = carrier_tracking_ref + "," + request['tracking_number']
                            else:
                                raise UserError(request['errors_message'])
    
                        # Last package
                        elif sequence == package_count:
                            # recuperer le label pdf
                            if not request.get('errors_message'):
                                package_labels.append((package_name, srm.get_label()))
    
                                if _convert_curr_iso_fdx(order_currency.name) in request['price']:
                                    carrier_price = request['price'][_convert_curr_iso_fdx(order_currency.name)]
                                else:
                                    _logger.info("Preferred currency has not been found in FedEx response")
                                    company_currency = picking.company_id.currency_id
                                    if _convert_curr_iso_fdx(company_currency.name) in request['price']:
                                        carrier_price = company_currency.compute(request['price'][_convert_curr_iso_fdx(company_currency.name)], order_currency)
                                    else:
                                        carrier_price = company_currency.compute(request['price']['USD'], order_currency)
    
                                carrier_tracking_ref = carrier_tracking_ref + "," + request['tracking_number']
    
                                logmessage = _("Shipment created into Fedex<br/>"
                                               "<b>Tracking Numbers:</b> %s<br/>"
                                               "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join([pl[0] for pl in package_labels]))
                                if self.fedex_label_file_type != 'PDF':
                                    attachments = [('LabelFedex-%s.%s' % (pl[0], self.fedex_label_file_type), pl[1]) for pl in package_labels]
                                if self.fedex_label_file_type == 'PDF':
                                    attachments = [('LabelFedex.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
                                picking.message_post(body=logmessage, attachments=attachments)
                                shipping_data = {'exact_price': carrier_price,
                                                 'tracking_number': carrier_tracking_ref}
                                res = res + [shipping_data]
                            else:
                                raise UserError(request['errors_message'])
    
                # TODO RIM handle if a package is not accepted (others should be deleted)
    
                ###############
                # One package #
                ###############
                elif package_count == 1:
                    srm.add_package(net_weight)
                    srm.set_master_package(net_weight, 1)
    
                    # Ask the shipping to fedex
                    request = srm.process_shipment()
    
                    warnings = request.get('warnings_message')
                    if warnings:
                        _logger.info(warnings)
    
                    if not request.get('errors_message'):
    
                        if _convert_curr_iso_fdx(order_currency.name) in request['price']:
                            carrier_price = request['price'][_convert_curr_iso_fdx(order_currency.name)]
                        else:
                            _logger.info("Preferred currency has not been found in FedEx response")
                            company_currency = picking.company_id.currency_id
                            if _convert_curr_iso_fdx(company_currency.name) in request['price']:
                                carrier_price = company_currency.compute(request['price'][_convert_curr_iso_fdx(company_currency.name)], order_currency)
                            else:
                                carrier_price = company_currency.compute(request['price']['USD'], order_currency)
    
                        carrier_tracking_ref = request['tracking_number']
                        logmessage = (_("Shipment created into Fedex <br/> <b>Tracking Number : </b>%s") % (carrier_tracking_ref))
                        picking.message_post(body=logmessage, attachments=[('LabelFedex-%s.%s' % (carrier_tracking_ref, self.fedex_label_file_type), srm.get_label())])
    
                        shipping_data = {'exact_price': carrier_price,
                                         'tracking_number': carrier_tracking_ref}
                        res = res + [shipping_data]
                    else:
                        raise UserError(request['errors_message'])
    
                ##############
                # No package #
                ##############
                else:
                    raise UserError(_('No packages for this picking'))
    
            return res
    
    def ups_send_shipping(self, pickings):
        res = []
        superself = self.sudo()
        srm = UPSRequest(self.log_xml, superself.ups_username, superself.ups_passwd, superself.ups_shipper_number, superself.ups_access_number, self.prod_environment)
        ResCurrency = self.env['res.currency']
        for picking in pickings:
            if not picking.ship_label_bool:
                packages = []
                package_names = []
                if picking.package_ids:
                    # Create all packages
                    for package in picking.package_ids:
                        packages.append(Package(self, package.shipping_weight, quant_pack=package.packaging_id, name=package.name))
                        package_names.append(package.name)
                # Create one package with the rest (the content that is not in a package)
                if picking.weight_bulk:
                    packages.append(Package(self, picking.weight_bulk))
    
                invoice_line_total = 0
                for move in picking.move_lines:
                    invoice_line_total += picking.company_id.currency_id.round(move.product_id.lst_price * move.product_qty)
    
                shipment_info = {
                    'description': picking.origin,
                    'total_qty': sum(sml.qty_done for sml in picking.move_line_ids),
                    'ilt_monetary_value': '%d' % invoice_line_total,
                    'itl_currency_code': self.env.user.company_id.currency_id.name,
                    'phone': picking.partner_id.mobile or picking.partner_id.phone or picking.sale_id.partner_id.mobile or picking.sale_id.partner_id.phone,
                }
                ups_service_type = picking.ups_service_type or self.ups_default_service_type
                ups_carrier_account = picking.ups_carrier_account
    
                if picking.carrier_id.ups_cod:
                    cod_info = {
                        'currency': picking.partner_id.country_id.currency_id.name,
                        'monetary_value': picking.sale_id.amount_total,
                        'funds_code': self.ups_cod_funds_code,
                    }
                else:
                    cod_info = None
    
                check_value = srm.check_required_value(picking.company_id.partner_id, picking.picking_type_id.warehouse_id.partner_id, picking.partner_id, picking=picking)
                if check_value:
                    raise UserError(check_value)
    
                package_type = picking.package_ids and picking.package_ids[0].packaging_id.shipper_package_code or self.ups_default_packaging_id.shipper_package_code
                result = srm.send_shipping(
                    shipment_info=shipment_info, packages=packages, shipper=picking.company_id.partner_id, ship_from=picking.picking_type_id.warehouse_id.partner_id,
                    ship_to=picking.partner_id, packaging_type=package_type, service_type=ups_service_type, label_file_type=self.ups_label_file_type, ups_carrier_account=ups_carrier_account,
                    saturday_delivery=picking.carrier_id.ups_saturday_delivery, cod_info=cod_info)
                if result.get('error_message'):
                    raise UserError(result['error_message'])
    
                currency_order = picking.sale_id.currency_id
                if not currency_order:
                    currency_order = picking.company_id.currency_id
    
                if currency_order.name == result['currency_code']:
                    price = float(result['price'])
                else:
                    quote_currency = ResCurrency.search([('name', '=', result['currency_code'])], limit=1)
                    price = quote_currency.compute(float(result['price']), currency_order)
    
                package_labels = []
                for track_number, label_binary_data in result.get('label_binary_data').items():
                    package_labels = package_labels + [(track_number, label_binary_data)]
    
                carrier_tracking_ref = "+".join([pl[0] for pl in package_labels])
                logmessage = _("Shipment created into UPS<br/>"
                               "<b>Tracking Numbers:</b> %s<br/>"
                               "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join(package_names))
                if self.ups_label_file_type != 'GIF':
                    attachments = [('LabelUPS-%s.%s' % (pl[0], self.ups_label_file_type), pl[1]) for pl in package_labels]
                if self.ups_label_file_type == 'GIF':
                    attachments = [('LabelUPS.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
                picking.message_post(body=logmessage, attachments=attachments)
                shipping_data = {
                    'exact_price': price,
                    'tracking_number': carrier_tracking_ref}
                res = res + [shipping_data]
            return res
    
def _convert_weight(weight, unit='KG'):
    ''' Convert picking weight (always expressed in KG) into the specified unit '''
    if unit == 'KG':
        return weight
    elif unit == 'LB':
        return weight / 0.45359237
    else:
        raise ValueError

def _convert_curr_fdx_iso(code):
    curr_match = {v: k for k, v in FEDEX_CURR_MATCH.items()}
    return curr_match.get(code, code)

def _convert_curr_iso_fdx(code):
    return FEDEX_CURR_MATCH.get(code, code)
