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


class ValidateIncomingOrder(models.TransientModel):
    _name = 'validate.incomig.order'
    
    @api.multi
    def validate_incoming_order(self):
        picking_obj = self.env['stock.picking']
        picking = picking_obj.browse(self._context.get('active_ids'))
        for pick in picking:
#             if pick.picking_type_id.code == 'outgoing':
#                 if pick.move_line_ids:
#                     for line in pick.move_line_ids:
#                         line.qty_done = line.product_uom_qty
#                 pick.button_validate()
#             else:
                pick.button_validate()
    
    
    
    
