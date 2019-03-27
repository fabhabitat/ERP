# -*- coding: utf-8 -*-

from odoo import api, fields, models
from lxml import etree
from datetime import datetime, date,timedelta
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


class PickList(models.TransientModel):
    _name = 'pick.list'
    
    wiz_pick_ids = fields.One2many('pick.list.line','wiz_pick_id','Pick List Line')
    current_date = fields.Datetime("Current Date")
    current_user_id = fields.Many2one('res.users', 'Responsible',default=lambda self:self.env.uid)
    company_id = fields.Many2one('res.company', 'Company Id',default=lambda self:self.env.user.company_id)

    @api.model
    def default_get(self, fields):
        res = super(PickList, self).default_get(fields)
        picking_obj = self.env['stock.picking']
        picking = picking_obj.browse(self._context.get('active_ids'))
        if not picking:
            return res
        id_lines = []
        if 'wiz_pick_ids' in fields or 'wiz_pick_ids' in fields:
            for pick in picking:
                for line in pick.move_lines:
                    for move_line in line.move_line_ids:
                        id_lines.append((0, 0, {
                                'sku':line.product_id.default_code,
                                'sku_name':line.product_id.name,
                                'location':move_line.location_id.name,
                                'quantity':move_line.qty_done,
                                'barcode':line.product_id.barcode,
                            }))
            res.update({'wiz_pick_ids':id_lines})
        return res
    
    @api.multi
    def calculate_date_time(self):
        pick_list_date  = " "
        self.current_date = datetime.now()
        po_date = datetime.strptime(self.current_date, '%Y-%m-%d %H:%M:%S')
        po_date_new = po_date+timedelta(hours=5,minutes=30)
        new_po_date = po_date_new.strftime('%Y-%m-%d %H:%M:%S')
        pick_list_date = new_po_date
        return pick_list_date
    
    @api.multi
    def pick_list_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        self.sent = True
        picking_obj = self.env['stock.picking']
        picking = picking_obj.browse(self._context.get('active_ids'))
        for pick in picking:
            pick.pick_list_print_bool = True
        return self.env.ref('verts_v11_fabhabitat.multiple_pick_up_list_report_id').report_action(self)
    
    
class WizPickLine(models.TransientModel):
    _name = "pick.list.line"
     
    wiz_pick_id = fields.Many2one('pick.list','Wiz Pick Id')
    sku = fields.Char("SKU")
    sku_name = fields.Char("SKU Name")
    location = fields.Char("Pick Location")
    quantity=fields.Float("Quantity")
    barcode = fields.Char("Barcode")
    
