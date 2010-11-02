from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.testing import z2
import transaction
from zope.configuration import xmlconfig


class IntranettLayer(PloneSandboxLayer):
    """ layer for integration tests """

    defaultBases = (PLONE_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        import intranett.policy

        xmlconfig.file("meta.zcml", intranett.policy,
                       context=configurationContext)
        xmlconfig.file("configure.zcml", intranett.policy,
                       context=configurationContext)
        xmlconfig.file("overrides.zcml", intranett.policy,
                       context=configurationContext)

        z2.installProduct(app, 'Products.PloneFormGen')
        z2.installProduct(app, 'intranett.policy')
        z2.installProduct(app, 'intranett.theme')

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'intranett.policy:default')

        setRoles(portal, TEST_USER_ID, ['Manager'])
        portal.invokeFactory('Folder', 'test-folder')
        setRoles(portal, TEST_USER_ID, ['Member'])
        transaction.commit()

    # def removeContent(self):
    #     id_ = 'front-page'
    #     if id_ in self.portal:
    #         self.loginAsPortalOwner()
    #         self.portal.setDefaultPage(None)
    #         del self.portal[id_]
    #     # We don't remove the Members/test_user_1_ folder, as it is too
    #     # convenient to use in tests
    #     for id_ in ('news', 'events'):
    #         if id_ in self.portal:
    #             del self.portal[id_]
    #     # The helpful testing machinery installs sunburst for us :(
    #     skins = self.portal.portal_skins
    #     for s in list(skins.keys()):
    #         if s.startswith('sunburst'):
    #             del skins[s]
    #     del skins.selections['Sunburst Theme']
    #    # TODO, there's also an actions.xml

INTRANETT_FIXTURE = IntranettLayer()

INTRANETT_INTEGRATION = IntegrationTesting(bases=(INTRANETT_FIXTURE,),
                                           name="intranett:integration")
INTRANETT_FUNCTIONAL = FunctionalTesting(bases=(INTRANETT_FIXTURE,),
                                         name="intranett:functional")
