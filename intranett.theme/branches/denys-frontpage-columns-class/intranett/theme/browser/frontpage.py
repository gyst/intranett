from zope.component import getMultiAdapter

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName

class FrontpageView(BrowserView):
    """
    Frontpage view
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    # def columns_class(self):
    #     """ CSS class that is assigned to columns on the frontpage. """
    #     ploneview = getMultiAdapter((self.context, self.request), name=u'plone')
    #     
    #     fp_left = ploneview.have_portlets('frontpage.portlets.left', view)
    #     fp_central = ploneview.have_portlets('frontpage.portlets.central', view)
    #     fp_right = ploneview.have_portlets('frontpage.portlets.right', view)
    #     
    #     if fp_left and fp_central and fp_right:
    #         return 'width-1:3'
    #     elif (fp_left and fp_central) 
    #          or (fp_left and fp_right) 
    #          or (fp_central and fp_right):
    #          return 'width-1:2'
    #     elif (fp_left)
