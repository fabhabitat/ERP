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


class DeliveryUpsWiz(models.TransientModel):
    _name = 'delivery.ups.wiz'
    
    
    
    
    @api.multi
    def merge_attachment(self):
        filename = 'Print Shipping Labels.pdf'
        picking_obj = self.env['stock.picking']
        picking = picking_obj.browse(self._context.get('active_ids'))
        lst =[]
        writer = PdfWriter()
        for pick in picking:
            pick.shipping_label_print_bool = True
            ship_name = 'Shipping labels' "%s" %pick.name
            if not pick.ship_label_bool :
                attachments = self.env['ir.attachment'].search([('res_id','=',pick.id)])
            else:
                attachments = self.env['ir.attachment'].search([('res_id','=',pick.id),('name','=',ship_name)])
            for att in attachments:
                lst.append(att)
#             writer = PdfFileWriter()
#             inpfn, = sys.argv[1:]
#             outfn = '4up.' + os.path.basename(inpfn)
#             pages = PdfReader(inpfn).pages
         
        def get4(srcpages):
            if not pick.ship_label_bool:
                scale = 0.35
                srcpages = PageMerge() + srcpages
                x_increment, y_increment = (scale * i for i in srcpages.xobj_box[2:])
                for i, page in enumerate(srcpages):
                    page.scale(scale)
                    page.x = x_increment if i & 1 else 0
                    page.y = 0 if i & 2 else y_increment
                return srcpages.render()  
            if pick.ship_label_bool:
                scale = 0.88
                srcpages = PageMerge() + srcpages
                x_increment, y_increment = (scale * i for i in srcpages.xobj_box[2:])
                for i, page in enumerate(srcpages):
                    page.scale(scale)
                     
    #                 page.x = x_increment if i & 1 else 0
    #                 page.y = 0 if i & 2 else y_increment
    #                 print "parrrrrrrrrrrrrrrrrrrrrr",page.x,page.y
                return srcpages.render() 
                
        def get4_fedex(srcpages):
            scale = 0.88
            srcpages = PageMerge() + srcpages
            x_increment, y_increment = (scale * i for i in srcpages.xobj_box[2:])
            for i, page in enumerate(srcpages):
                page.scale(scale)
                 
#                 page.x = x_increment if i & 1 else 0
#                 page.y = 0 if i & 2 else y_increment
#                 print "parrrrrrrrrrrrrrrrrrrrrr",page.x,page.y
            return srcpages.render()  
        for pdf in lst:
            
            pages = PdfReader(BytesIO(base64.decodestring(pdf.datas))).pages
            pick1 = picking_obj.browse(pdf.res_id)
         
            
            for index in range(0, len(pages), 1):
                if pick1.carrier_id.delivery_type =='ups':    
                    writer.addpage(get4(pages[index:index + 1]))
                if pick1.carrier_id.delivery_type =='fedex':    
                    writer.addpage(get4_fedex(pages[index:index + 1]))
                    
            # Return merged PDF
        s = BytesIO()
        writer.write(s)
        reader = PdfFileReader(s)
        writer = PdfFileWriter()
        for page in range(0, reader.getNumPages()):
            p=reader.getPage(page)
            if pick1.carrier_id.delivery_type =='fedex' and not pick1.ship_label_bool :
                p.mediaBox.lowerRight = (900, 145)
                p.mediaBox.lowerLeft = (-600, 390)
                p.mediaBox.upperLeft = (99, 500)
                p.mediaBox.upperRight = (530, 680)
            if pick1.carrier_id.delivery_type =='ups' and not pick1.ship_label_bool:
                p.mediaBox.lowerRight = (450, 145)
                p.mediaBox.upperRight = (425, 600) 
                p.mediaBox.lowerLeft = (-150, 275)
                p.mediaBox.upperLeft = (-5, 565)
            writer.addPage(p)
        s = BytesIO()
        writer.write(s)
        out = base64.b64encode(s.getvalue())
        view_report_status_id=self.env['view.report'].create({'file_name':out,'datas_fname':filename})
        return {
        'res_id'   :view_report_status_id.id,
        'name'     :'Print Shipping Labels',
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

