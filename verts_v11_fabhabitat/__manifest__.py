{
    'name': 'VERTS module for the Fab Habitat',
    'category': '',
    'description': """
    """,
    'author': 'VERTS Services India Private Limited',
    'depends': ['stock','account','delivery','delivery_ups','delivery_fedex'],
    'external_dependencies': {"python": ['pdfrw']},
    'data': [
        'wizard/delivery_ups_views.xml',
        'wizard/check_availability.xml',
        'wizard/do_update_wiz_view.xml',
        'wizard/validate_incoming_order_view.xml',
        'wizard/pick_list_view.xml',
        'wizard/packing_merge_view.xml',
        'wizard/invoice_merge_view.xml',
        'view/delivery_order_view.xml',
        'view/delivery_carrier_view.xml',
        'report/shipping_label_report_view.xml',
        'report/packing_list_report_view.xml',
        'report/invoices_report_view.xml',
        'report/pickup_list.xml',
        'report/stock_picking_report.xml',
        'report/multiple_pick_list_template.xml',
             ],

 'installation' : True

}
