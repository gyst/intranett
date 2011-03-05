import logging
import os
import sys

logger = logging.getLogger()


def create_site(app, args):
    # Display all messages on stderr
    logger.setLevel(logging.INFO)
    logger.handlers[0].setLevel(logging.INFO)

    force = '--force' in args or '-f' in args
    existing = 'Plone' in app.keys()

    root_arg = [a for a in args if a.startswith('--rootpassword')]
    if any(root_arg):
        password = root_arg[0].split('=')[1].strip()
        acl = app.acl_users
        users = getattr(acl, 'users', None)
        if not users:
            # Non-PAS folder from a fresh database
            app.acl_users._doAddUser('admin', password, ['Manager'], [])

    if existing:
        if not force:
            logger.error('Plone site already exists.')
            sys.exit(1)
        else:
            del app['Plone']
            app._p_jar.db().cacheMinimize()
            logger.info('Removed existing Plone site.')

    from Testing import makerequest
    root = makerequest.makerequest(app)
    request = root.REQUEST

    title = os.environ.get('INTRANETT_DOMAIN', 'intranett.no')
    title_arg = [a for a in args if a.startswith('--title')]
    if any(title_arg):
        targ = title_arg[0].split('=')[1].strip()
        if targ:
            title = targ

    language = 'no'
    lang_arg = [a for a in args if a.startswith('--language')]
    if any(lang_arg):
        language = lang_arg[0].split('=')[1].strip()

    request.form = {
        'extension_ids': ('intranett.policy:default', ),
        'form.submitted': True,
        'title': title,
        'language': language,
    }
    from intranett.policy.browser.admin import AddIntranettSite
    addsite = AddIntranettSite(root, request)
    addsite()
    import transaction
    transaction.get().note('Added new Plone site.')
    transaction.get().commit()
    logger.info('Added new Plone site.')


def upgrade(app, args):
    # Display all messages on stderr
    logger.setLevel(logging.DEBUG)
    logger.handlers[0].setLevel(logging.DEBUG)

    # Make app.REQUEST available
    from Testing import makerequest
    root = makerequest.makerequest(app)
    site = root.get('Plone', None)
    if site is None:
        logger.error("No site called `Plone` found in the database.")
        sys.exit(1)

    # Set up local site manager
    from zope.site.hooks import setHooks
    from zope.site.hooks import setSite
    setHooks()
    setSite(site)
    setup = site.portal_setup

    import transaction
    from intranett.policy.config import config

    logger.info("Starting the upgrade.\n\n")
    config.run_all_upgrades(setup)
    logger.info("Ran upgrade steps.")

    # Recook resources, as some CSS/JS/KSS files might have changed.
    # TODO: We could try to determine if this is needed in some way
    site.portal_javascripts.cookResources()
    site.portal_css.cookResources()
    site.portal_kss.cookResources()
    logger.info("Resources recooked.")

    transaction.get().note('Upgraded profiles and recooked resources.')
    transaction.get().commit()
    sys.exit(0)
