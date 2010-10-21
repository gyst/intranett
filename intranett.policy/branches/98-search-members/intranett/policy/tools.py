from OFS.Image import Image
from App.class_init import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
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
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')

    def notifyModified(self):
        super(MemberData, self).notifyModified()
        plone = getUtility(ISiteRoot)
        ct = getToolByName(plone, 'portal_catalog')
        ct.reindexObject(self)

    def getPhysicalPath(self):
        plone = getUtility(ISiteRoot)
        return plone.getPhysicalPath() + ('author', self.getId())

    security.declareProtected('Title', 'View')
    def Title(self):
        return self.getProperty('fullname')

    security.declareProtected('Description', 'View')
    def Description(self):
        position = self.getProperty('position', '')
        department = self.getProperty('department', '')
        if position and department:
            return "%s, %s" %(position, department)
        else:
            return "%s%s" %(position, department)

    def BirthDate(self):
        return self.getProperty('birth_date')

    security.declareProtected('SearchableText', 'View')
    def SearchableText(self):
        return ' '.join([self.getProperty('fullname') or '',
                         self.getProperty('email') or '',
                         self.getProperty('position') or '',
                         self.getProperty('department') or '',
                         self.getProperty('location') or '',
                         self.getProperty('description') or '',
                         self.getProperty('phone') or '',
                         self.getProperty('mobile') or ''])

InitializeClass(MemberData)

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
        memberinfo['position'] = member.getProperty('position')
        memberinfo['department'] = member.getProperty('department')
        memberinfo['birth_date'] = member.getProperty('birth_date')
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
