# -*- coding: utf-8 -*-

from odoo import api, fields, models
from lxml import etree
from datetime import datetime
import os
from odoo.tools import pdf
from odoo.exceptions import UserError
import base64
# try:
#     from cStringIO import StringIO
# except:
#     from StringIO import StringIO

from io import StringIO
from io import BytesIO
from PyPDF2 import PdfFileWriter, PdfFileReader
import sys
import os
from pdfrw import PdfReader, PdfWriter, PageMerge
import logging

params = None
log = logging.getLogger(__name__)


class PackingListWiz(models.TransientModel):
    _name = 'packing.list.wiz'
    
    
    
    
    @api.multi
    def merge_attachment(self):
        filename = 'Print Packing List.pdf'
        picking_obj = self.env['stock.picking']
        picking = picking_obj.browse(self._context.get('active_ids'))
        lst =[]
        writer = PdfWriter()
        for pick in picking:
            if pick.packing_list_bool:
                pick.packing_list_print_bool = True
            ship_name = 'Packing List' "%s" %pick.name
            attachments = self.env['ir.attachment'].search([('res_id','=',pick.id),('name','=',ship_name)])
            for att in attachments:
                lst.append(att)
                
        def get4_fedex(srcpages):
            scale = 0.88
            srcpages = PageMerge() + srcpages
            x_increment, y_increment = (scale * i for i in srcpages.xobj_box[2:])
            for i, page in enumerate(srcpages):
                page.scale(scale)
            return srcpages.render() 
         
        for pdf in lst:
            pages = PdfReader(BytesIO(base64.decodestring(pdf.datas))).pages
            pick1 = picking_obj.browse(pdf.res_id)
            for index in range(0, len(pages), 1):
                writer.addpage(get4_fedex(pages[index:index + 1]))
                    
        s = BytesIO()
        writer.write(s)
        reader = PdfFileReader(s)
        writer = PdfFileWriter()
        for page in range(0, reader.getNumPages()):
            p=reader.getPage(page)
            writer.addPage(p)
        s = BytesIO()
        writer.write(s)
        out = base64.b64encode(s.getvalue())
        view_report_status_id=self.env['view.report'].create({'file_name':out,'datas_fname':filename})
        return {
        'res_id'   :view_report_status_id.id,
        'name'     :'Print Packing List',
        'view_type':'form',
        'view_mode':'form',
        'res_model':'view.report',
        'view_id'  : False ,
        'type'     :'ir.actions.act_window',
            }
        
        
class view_report(models.TransientModel):
        _name='view.report'
        _rec_name='datas_fname'
        
        datas_fname = fields.Char('File Name')
        file_name = fields.Binary('Report')

