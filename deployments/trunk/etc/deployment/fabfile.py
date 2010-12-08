import os
import os.path

from fabric.api import cd
from fabric.api import env
from fabric.api import get
from fabric.api import hide
from fabric.api import local
from fabric.api import run
from fabric.api import settings
from fabric.api import show
import pkg_resources

env.shell = "/bin/bash -c"
BUILDOUT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

# XXX hosting@jarn.com
CRON_MAILTO = 'hanno@jarn.com'
DISTRIBUTE_VERSION = '0.6.14'
HOME = '/srv/jarn'
VENV = '/srv/jarn'
PIL_VERSION = '1.1.7-jarn1'
PIL_LOCATION = 'http://dist.jarn.com/public/PIL-%s.zip' % PIL_VERSION
SVN_AUTH = '--username=intranett --password=BJrKt6JahD5mkl'
SVN_FLAGS = '--trust-server-cert --non-interactive --no-auth-cache'
SVN_EXE = 'svn %s' % SVN_FLAGS
SVN_CONFIG = os.path.join(HOME, '.subversion', 'config')
SVN_PREFIX = 'https://svn.jarn.com/jarn/intranett.no/deployments/tags'


def svn_info():
    with cd(VENV):
        run('pwd && svn info')


def dump_db():
    with cd(VENV):
        with settings(hide('warnings'), warn_only=True):
            run('rm var/snapshotbackups/*')
        run('bin/snapshotbackup')


def download_last_dump():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'),
                  warn_only=True):
        existing = run('ls -rt1 %s/var/snapshotbackups/*' % VENV)
    for e in existing.split('\n'):
        get(e, os.path.join(BUILDOUT_ROOT, 'var', 'snapshotbackups'))


def update():
    _prepare_update(newest=False)
    with cd(VENV):
        run('bin/supervisorctl stop varnish')
        run('bin/supervisorctl stop zope:*')
        run('bin/instance-debug upgrade')
        run('bin/supervisorctl start zope:instance1')
        run('bin/supervisorctl start zope:instance2')
        run('bin/supervisorctl start varnish')


def full_update():
    _prepare_update()
    with cd(VENV):
        run('bin/supervisorctl shutdown')
        run('bin/supervisord')
        run('bin/supervisorctl stop varnish')
        run('bin/instance-debug upgrade')
        run('bin/supervisorctl start varnish')


def init_server():
    envvars = _set_environment_vars()
    _set_cron_mailto()
    _disable_svn_store_passwords()
    _virtualenv()

    # switch / checkout svn
    command = 'switch' if _is_svn_checkout() else 'co'
    _svn_get(command=command)
    _buildout(envvars=envvars)
    _create_plone_site()


def _buildout(envvars, newest=True):
    domain = envvars['domain']
    front = envvars['front']
    arg = '' if newest else '-N'
    with cd(VENV):
        run('bin/python2.6 bootstrap.py -d')
        with settings(hide('stdout', 'stderr', 'warnings'), warn_only=True):
            run('mkdir downloads')
        run('{x1}; {x2}; bin/buildout {arg}'.format(
            x1=front, x2=domain, arg=arg))
        run('chmod 700 var/blobstorage')


def _create_plone_site():
    # TODO
    pass


def _disable_svn_store_passwords():
    with settings(hide('stdout', 'stderr', 'warnings'), warn_only=True):
        # run svn info once, so we create ~/.subversion/config
        run('svn info')
        output = run('cat %s' % SVN_CONFIG)
    lines = output.split('\n')
    new_lines = []
    changed = False
    for line in lines:
        if 'store-passwords = no' in line:
            changed = True
            new_lines.append('store-passwords = no')
        else:
            new_lines.append(line)
    if changed:
        with settings(hide('running', 'stdout', 'stderr')):
            run('echo -e "{content}" > {config}'.format(
                content='\n'.join(new_lines), config=SVN_CONFIG))


def _is_svn_checkout():
    with settings(hide('stdout', 'stderr', 'warnings'), warn_only=True):
        out = run('svn info %s' % VENV)
    return 'Revision' in out


def _latest_svn_tag():
    with settings(hide('running')):
        tags = local('{exe} ls {auth} {svn}'.format(
            exe=SVN_EXE, auth=SVN_AUTH, svn=SVN_PREFIX))
    tags = [t.rstrip('/') for t in tags.split('\n')]
    tags = [(pkg_resources.parse_version(t), t) for t in tags]
    tags.sort()
    return tags[-1][1]


def _prepare_update(newest=True):
    envvars = _set_environment_vars()
    dump_db()
    _svn_get()
    _buildout(envvars=envvars, newest=newest)


def _set_cron_mailto():
    with settings(hide('stdout', 'warnings'), warn_only=True):
        # if no crontab exists, this crontab -l has an exit code of 1
        run('crontab -l > %s/crontab.tmp' % HOME)
        crontab = run('cat %s/crontab.tmp' % HOME)
    cron_lines = crontab.split('\n')
    mailto = [l for l in cron_lines if l.startswith('MAILTO')]
    wrong_address = not CRON_MAILTO in mailto
    if not mailto or wrong_address:
        # add mailto right after the comments
        boilerplate = ('DO NOT EDIT THIS FILE', 'installed on',
            'Cron version V5.0')
        new_cron_lines = []
        added = False
        for line in cron_lines:
            if line.startswith('#'):
                # Remove some excessive boilerplate
                skip = False
                for b in boilerplate:
                    if b in line:
                        skip = True
                if not skip:
                    new_cron_lines.append(line)
            elif line.startswith('MAILTO') and wrong_address:
                continue
            else:
                if not added:
                    new_cron_lines.append('MAILTO=%s' % CRON_MAILTO)
                    added = True
                new_cron_lines.append(line)
        if not added:
            new_cron_lines.append('MAILTO=%s' % CRON_MAILTO)
        with settings(hide('running', 'stdout', 'stderr')):
            run('echo -e "{content}" > {home}/crontab.tmp'.format(
                home=HOME, content='\n'.join(new_cron_lines)))
            run('crontab %s/crontab.tmp' % HOME)
    with settings(hide('stdout', 'stderr')):
        run('rm %s/crontab.tmp' % HOME)


def _set_environment_vars():
    with settings(hide('stdout', 'stderr')):
        profile = run('cat %s/.bash_profile' % HOME)
    profile_lines = profile.split('\n')
    subdomain = env.host_string
    domain_line = 'export INTRANETT_DOMAIN=%s.intranett.no' % subdomain
    with settings(hide('stdout', 'stderr')):
        front_ip = run('/sbin/ifconfig ethfe | head -n 2 | tail -n 1')
    front_ip = front_ip.lstrip('inet addr:').split()[0]
    front_line = 'export INTRANETT_ZOPE_IP=%s' % front_ip

    exports = [l for l in profile_lines if l.startswith('export INTRANETT_')]
    if len(exports) < 2:
        start, end = profile_lines[:2], profile_lines[2:]
        new_file = start + [front_line] + [domain_line + '\n'] + end
        with settings(hide('running', 'stdout', 'stderr')):
            # run(domain_line)
            # run(front_line)
            run('echo -e "{content}" > {home}/.bash_profile'.format(
                home=HOME, content='\n'.join(new_file)))
    return dict(domain=domain_line, front=front_line)


def _svn_get(command='switch'):
    latest_tag = _latest_svn_tag()
    print('Switching to version: %s' % latest_tag)
    with settings(hide('stdout', 'stderr', 'running')):
        run('{exe} revert -R .'.format(exe=SVN_EXE))
        run('{exe} cleanup'.format(exe=SVN_EXE))
        run('{exe} {command} {auth} {svn}/{tag} {loc}'.format(
            exe=SVN_EXE, command=command, auth=SVN_AUTH, svn=SVN_PREFIX,
            tag=latest_tag, loc=VENV))
        if command == 'switch':
            run('{exe} up {auth}'.format(exe=SVN_EXE, auth=SVN_AUTH))


def _virtualenv():
    with settings(hide('stdout', 'stderr')):
        with cd(HOME):
            run('virtualenv-2.6 --no-site-packages --distribute %s' % VENV)
        run('rm -rf /tmp/distribute*')
        with cd(VENV):
            run('bin/easy_install-2.6 distribute==%s' % DISTRIBUTE_VERSION)
            run('rm bin/activate')
            run('rm bin/activate_this.py')
            run('rm bin/pip')
            # Only install PIL if it isn't there
            with settings(hide('warnings'), show('stdout'), warn_only=True):
                out = run('bin/python -c "from PIL import Image; print(Image.__version__)"')
            if PIL_VERSION not in out:
                run('bin/easy_install-2.6 %s' % PIL_LOCATION)
                run('rm bin/pil*.py')
