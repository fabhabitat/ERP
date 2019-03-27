from odoo import api,fields,models,_
from datetime import datetime
import os
from odoo.tools import pdf
from odoo.exceptions import UserError
import base64
import xlrd
# try:
#     from cStringIO import StringIO
# except:
#     from StringIO import StringIO
# from pyPdf import PdfFileWriter, PdfFileReader
import logging
import io

params = None
log = logging.getLogger(__name__)


class DoUpdate(models.TransientModel):
    _name = 'do.update'
    
    barcode_sheet =fields.Binary('Barcode Sheet')

    @api.multi
    def load_barcode_sheet(self):
        message = ""
        for self_obj in self:
            data_decode = self_obj.barcode_sheet
#             product_pool = self.env['product.product']
            if not data_decode:
                raise UserError(_('Please Choose The File!'))
            val=base64.decodestring(data_decode)
            fp = io.BytesIO()
            fp.write(val)
            wb = xlrd.open_workbook(file_contents=fp.getvalue())
            wb.sheet_names()
            sheet_name=wb.sheet_names()
            sh = wb.sheet_by_name(sheet_name[0])
            n_rows=sh.nrows
            product_sku_dic ={}
            defalut_code  = ''
            for row in range(1,n_rows):
                product_id=False
                dict={}
                if sh.row_values(row)[0] and sh.row_values(row)[1] and sh.row_values(row)[2]and sh.row_values(row)[3]and sh.row_values(row)[4]and sh.row_values(row)[5]and sh.row_values(row)[6]and sh.row_values(row)[7]and sh.row_values(row)[8]and sh.row_values(row)[9]and sh.row_values(row)[10]and sh.row_values(row)[11]and sh.row_values(row)[12]and sh.row_values(row)[13]and sh.row_values(row)[14]:
                    client = str(sh.row_values(row)[0])
#                     product_ids=product_pool.search([('default_code','=',default_code)])
                    sku_no = str(sh.row_values(row)[1])
                    qty = str(sh.row_values(row)[2])
                    po_no = str(sh.row_values(row)[3])
                    ship_to_name = str(sh.row_values(row)[4])
                    ship_to_email = str(sh.row_values(row)[5])
                    ship_address = str(sh.row_values(row)[6])
                    ship_city = str(sh.row_values(row)[7])
                    ship_state = str(sh.row_values(row)[8])
                    ship_zip = str(sh.row_values(row)[9])
                    ship_country = str(sh.row_values(row)[10])
                    ship_phone = str(sh.row_values(row)[11])
                    date_ship = str(sh.row_values(row)[12])
                    method_of_shipment = str(sh.row_values(row)[13])
                    comments = str(sh.row_values(row)[14])
                    picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
                    if picking_type_id.default_location_src_id:
                        location_id = picking_type_id.default_location_src_id.id
#                     elif self.customer_name_id:
#                         location_id = self.customer_name_id.property_stock_supplier.id
                    else:
                        customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()
                    
                    if ship_to_name:
                        ship_zip1 = ship_zip.split('.')
                        po_no1 = po_no.split('.')
                        ship_phone1 = ship_phone.split('.')
                        res_country_id = self.env['res.country'].search([('code', '=', ship_country)])
                        res_state_id = self.env['res.country.state'].search([('name', '=', ship_state)])
                        res_partner_id = self.env['res.partner'].create({'name':ship_to_name,
                                                                           'email':ship_to_email,
                                                                           'street':ship_address,
                                                                           'city':ship_city,
                                                                           'state_id':res_state_id.id,
                                                                           'zip':str(ship_zip1[0]),
                                                                           'country_id':res_country_id.id,
                                                                           'phone':str(ship_phone1[0]),
                                                                        })
                        if  res_partner_id:
                            if picking_type_id.default_location_dest_id:
                                location_dest_id = picking_type_id.default_location_dest_id.id
                            elif res_partner_id:
                                location_dest_id = res_partner_id.property_stock_customer.id
                            else:
                                location_dest_id, supplierloc = self.env['stock.warehouse']._get_partner_locations()                                                 
                            do_id = self.env['stock.picking'].create({
                                                   'partner_id':res_partner_id.id,
                                                   'street':res_partner_id.street,
                                                   'city':res_partner_id.city,
                                                   'zip':res_partner_id.zip,
                                                   'country_id': res_partner_id.country_id.id,
                                                   'state_id': res_partner_id.state_id.id,
                                                   'po_order_number' : str(po_no1[0]),
                                                   'location_id':location_id,
                                                   'picking_type_id':picking_type_id.id,
                                                   'location_dest_id':location_dest_id,
                                                   })
                            if do_id:
                                if sku_no:
                                    product_ids = self.env['product.product'].search([('default_code','=',sku_no)])
                                self.env['stock.move'].create({'picking_id':do_id.id,
                                                           'product_id':product_ids.id,
                                                           'product_uom_qty':qty,
                                                           'name':product_ids.partner_ref,
                                                           'product_uom':product_ids.uom_id.id,
                                                           'location_id':location_id,
                                                           'location_dest_id':location_dest_id,
                                                        })

                            return True            
    
    
    
    
