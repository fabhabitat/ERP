# -*- coding: utf-8 -*-

from odoo import api, fields, models
from lxml import etree
from datetime import datetime
import os
# from odoo.tools import pdf
from odoo.exceptions import UserError
import base64
# try:
#     from cStringIO import StringIO
# except:
#     from StringIO import StringIO
# from PyPDF2 import PdfFileWriter, PdfFileReader
import sys
import os
# from pdfrw import PdfReader, PdfWriter, PageMerge
import logging

params = None
log = logging.getLogger(__name__)


class CheckAvailability(models.TransientModel):
    _name = 'check.availability'
    
    @api.multi
    def check_availability(self):
        picking_obj = self.env['stock.picking']
        picking = picking_obj.browse(self._context.get('active_ids'))
        for pick in picking:
            pick.action_assign()
            if pick.picking_type_id.code == 'outgoing':
                if pick.move_line_ids:
                    shipper_package_id = False  
                    stock_quant_id = False 
                    if pick.shipper_package_code:
                        shipper_package_id = self.sudo().env['product.packaging'].search([('shipper_package_code', '=', pick.shipper_package_code)],limit=1)
                        stock_quant_id = self.sudo().env['stock.quant.package'].create({
                                           'packaging_id':shipper_package_id and shipper_package_id.id or False,
                                           'shipping_weight':pick.shipping_weight,
                                           })
                    for line in pick.move_line_ids:
                        line.qty_done = line.product_uom_qty
                        if stock_quant_id:
                            line.result_package_id = stock_quant_id.id
    
    
    
    
