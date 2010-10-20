from OFS.Image import Image
from Acquisition import aq_base
from zope.component import getUtility
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import ISiteRoot
from Products.PlonePAS.tools.membership import MembershipTool as BaseMembershipTool
from Products.PlonePAS.tools.memberdata import MemberDataTool as BaseMemberDataTool
from Products.PlonePAS.tools.memberdata import MemberData as BaseMemberData
from Products.PlonePAS.tools.membership import default_portrait
from Products.PlonePAS.utils import scale_image

PORTRAIT_SIZE = (300, 300,)
PORTRAIT_THUMBNAIL_SIZE = (100, 100,)


class MemberData(BaseMemberData):
    """This is a catalog-aware MemberData. We add functions to allow the
    catalog to index member data.
    """

    def notifyModified(self):
        super(MemberData, self).notifyModified()
        plone = getUtility(ISiteRoot)
        ct = getToolByName(plone, 'portal_catalog')
        ct.reindexObject(self)

    def getPhysicalPath(self):
        plone = getUtility(ISiteRoot)
        return plone.getPhysicalPath() + ('author', self.getId())

    def Title(self):
        return self.getProperty('fullname')

    def Description(self):
        return self.getProperty('description')

    def Email(self):
        return self.getProperty('email')

    def Location(self):
        return self.getProperty('location')

    def Department(self):
        return self.getProperty('department')

    def Phone(self):
        return self.getProperty('phone')

    def Mobile(self):
        return self.getProperty('mobile')

    def SearchableText(self):
        return ' '.join([self.Title(),
                         self.Description(),
                         self.Email(),
                         self.Location(),
                         self.Department(),
                         self.Phone(),
                         self.Mobile()])


class MemberDataTool(BaseMemberDataTool):

    def __init__(self):
        super(MemberDataTool, self).__init__()
        self.thumbnails = BTreeFolder2(id='thumbnails')

    def _getPortrait(self, member_id, thumbnail=False):
        "return member_id's portrait if you can "
        if thumbnail:
            return self.thumbnails.get(member_id, None)
        return super(MemberDataTool, self)._getPortrait(member_id)

    def _setPortrait(self, portrait, member_id, thumbnail=False):
        " store portrait which must be a raw image in _portrais "
        if thumbnail:
            if member_id in self.thumbnails:
                self.thumbnails._delObject(member_id)
            self.thumbnails._setObject(id=member_id, object=portrait)
        else:
            super(MemberDataTool, self)._setPortrait(portrait, member_id)

    def _deletePortrait(self, member_id):
        " remove member_id's portrait "
        super(MemberDataTool, self)._deletePortrait(member_id)
        if member_id in self.thumbnails:
            self.thumbnails._delObject(member_id)

    def wrapUser(self, u):
        """ Override wrapUser only to use our MemberData
        """
        id = u.getId()
        members = self._members
        if not members.has_key(id):
            base = aq_base(self)
            members[id] = MemberData(base, id)
        return members[id].__of__(self).__of__(u)


class MembershipTool(BaseMembershipTool):

    def getMemberInfo(self, memberId=None):
        memberinfo = super(MembershipTool, self).getMemberInfo(memberId)
        if memberinfo is None:
            return None
        if not memberId:
            member = self.getAuthenticatedMember()
        else:
            member = self.getMemberById(memberId)
        memberinfo['email'] = member.getProperty('email')
        memberinfo['phone'] = member.getProperty('phone')
        memberinfo['mobile'] = member.getProperty('mobile')
        memberinfo['department'] = member.getProperty('department')
        return memberinfo

    def changeMemberPortrait(self, portrait, id=None):
        """update the portait of a member.

        Modified from CMFPlone version to URL-quote the member id.
        """
        safe_id = self._getSafeMemberId(id)
        if not safe_id:
            safe_id = self.getAuthenticatedMember().getId()

        membertool = getToolByName(self, 'portal_memberdata')
        if portrait and portrait.filename:
            #import pdb; pdb.set_trace( )
            scaled, mimetype = scale_image(portrait,
                                           max_size=PORTRAIT_SIZE)
            image = Image(id=safe_id, file=scaled, title='')
            membertool._setPortrait(image, safe_id)
            # Now for thumbnails
            portrait.seek(0)
            scaled, mimetype = scale_image(portrait,
                                           max_size=PORTRAIT_THUMBNAIL_SIZE)
            image = Image(id=safe_id, file=scaled, title='')
            membertool._setPortrait(image, safe_id, thumbnail=True)

    def getPersonalPortrait(self, id=None, thumbnail=True):
        """Return a members personal portait.

        Modified to make it possible to return the thumbnail portrait.
        """
        safe_id = self._getSafeMemberId(id)
        membertool   = getToolByName(self, 'portal_memberdata')

        if not safe_id:
            safe_id = self.getAuthenticatedMember().getId()

        portrait = membertool._getPortrait(safe_id, thumbnail=thumbnail)

        if portrait is None:
            portal = getToolByName(self, 'portal_url').getPortalObject()
            portrait = getattr(portal, default_portrait, None)

        return portrait
