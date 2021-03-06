from plone.app.portlets.portlets import base
from plone.memoize.instance import memoize
from plone.portlets.interfaces import IPortletDataProvider
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope import schema
from zope.formlib import form
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from intranett.policy import IntranettMessageFactory as _

news_vocab = [SimpleTerm(token, token, title)
              for token, title in
              [(u'last', _(u'The most recently published news item')),
               (u'before_last',
                _(u'The second-most recently published news item'))]]


class INewsHighlight(IPortletDataProvider):
    """A portlet for displaying recent news items on the front page.
    """

    portletTitle = schema.TextLine(title=_(u"Portlet title"), description=u"")

    source = schema.Choice(title=_(u"Which item to display"),
        vocabulary=SimpleVocabulary(news_vocab), required=True, default=None)


class Assignment(base.Assignment):

    implements(INewsHighlight)

    def __init__(self, portletTitle="", source=None):
        self.portletTitle = portletTitle
        self.source = source

    title = _("News Highlight")


class Renderer(base.Renderer):

    render = ViewPageTemplateFile('newshighlight.pt')

    @property
    def available(self):
        return self.item() is not None

    @property
    def portletTitle(self):
        return self.data.portletTitle

    @memoize
    def item(self):
        context = self.context
        catalog = getToolByName(context, 'portal_catalog')
        items = catalog(portal_type='News Item',
                        review_state='published',
                        sort_on='effective',
                        sort_order='reverse',
                        sort_limit=2)[:2]
        if not items:
            return None

        source = self.data.source
        if source == 'last':
            return items[0]
        elif source == 'before-last' and len(items) > 1:
            return items[1]
        return None


class AddForm(base.AddForm):

    form_fields = form.Fields(INewsHighlight)

    def create(self, data):
        return Assignment(**data)


class EditForm(base.EditForm):

    form_fields = form.Fields(INewsHighlight)
