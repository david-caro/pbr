# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os.path
import shlex
import sys

import fixtures
import testtools
import textwrap

from pbr.tests import base
from pbr.tests.test_packaging import CreatePackages
from pbr.tests.test_packaging import Venv

PIPFLAGS = shlex.split(os.environ.get('PIPFLAGS', ''))
PIPVERSION = os.environ.get('PIPVERSION', 'pip')
PBRVERSION = os.environ.get('PBRVERSION', 'pbr')
REPODIR = os.environ.get('REPODIR', '')
WHEELHOUSE = os.environ.get('WHEELHOUSE', '')
PIP_CMD = ['-m', 'pip'] + PIPFLAGS + ['install', '-f', WHEELHOUSE]
PROJECTS = shlex.split(os.environ.get('PROJECTS', ''))
PBR_ROOT = os.path.abspath(os.path.join(__file__, '..', '..', '..'))


def all_projects():
    if not REPODIR:
        return
    # Future: make this path parameterisable.
    excludes = set(['tempest', 'requirements'])
    for name in PROJECTS:
        name = name.strip()
        short_name = name.split('/')[-1]
        try:
            with open(os.path.join(
                    REPODIR, short_name, 'setup.py'), 'rt') as f:
                if 'pbr' not in f.read():
                    continue
        except IOError:
            continue
        if short_name in excludes:
            continue
        yield (short_name, dict(name=name, short_name=short_name))


class TestIntegration(base.BaseTestCase):

    scenarios = list(all_projects())

    def setUp(self):
        # Integration tests need a higher default - big repos can be slow to
        # clone, particularly under guest load.
        env = fixtures.EnvironmentVariable(
            'OS_TEST_TIMEOUT', os.environ.get('OS_TEST_TIMEOUT', '600'))
        with env:
            super(TestIntegration, self).setUp()
        base._config_git()

    @testtools.skipUnless(
        os.environ.get('PBR_INTEGRATION', None) == '1',
        'integration tests not enabled')
    def test_integration(self):
        # Test that we can:
        # - run sdist from the repo in a venv
        # - install the resulting tarball in a new venv
        # - pip install the repo
        # - pip install -e the repo
        # We don't break these into separate tests because we'd need separate
        # source dirs to isolate from side effects of running pip, and the
        # overheads of setup would start to beat the benefits of parallelism.
        self.useFixture(base.CapturedSubprocess(
            'sync-req',
            ['python', 'update.py', os.path.join(REPODIR, self.short_name)],
            cwd=os.path.join(REPODIR, 'requirements')))
        self.useFixture(base.CapturedSubprocess(
            'commit-requirements',
            'git diff --quiet || git commit -amrequirements',
            cwd=os.path.join(REPODIR, self.short_name), shell=True))
        path = os.path.join(
            self.useFixture(fixtures.TempDir()).path, 'project')
        self.useFixture(base.CapturedSubprocess(
            'clone',
            ['git', 'clone', os.path.join(REPODIR, self.short_name), path]))
        venv = self.useFixture(Venv('sdist',
                                    modules=['pip', 'wheel', PBRVERSION],
                                    pip_cmd=PIP_CMD))
        python = venv.python
        self.useFixture(base.CapturedSubprocess(
            'sdist', [python, 'setup.py', 'sdist'], cwd=path))
        venv = self.useFixture(Venv('tarball',
                                    modules=['pip', 'wheel', PBRVERSION],
                                    pip_cmd=PIP_CMD))
        python = venv.python
        filename = os.path.join(
            path, 'dist', os.listdir(os.path.join(path, 'dist'))[0])
        self.useFixture(base.CapturedSubprocess(
            'tarball', [python] + PIP_CMD + [filename]))
        venv = self.useFixture(Venv('install-git',
                                    modules=['pip', 'wheel', PBRVERSION],
                                    pip_cmd=PIP_CMD))
        root = venv.path
        python = venv.python
        self.useFixture(base.CapturedSubprocess(
            'install-git', [python] + PIP_CMD + ['git+file://' + path]))
        if self.short_name == 'nova':
            found = False
            for _, _, filenames in os.walk(root):
                if 'migrate.cfg' in filenames:
                    found = True
            self.assertTrue(found)
        venv = self.useFixture(Venv('install-e',
                                    modules=['pip', 'wheel', PBRVERSION],
                                    pip_cmd=PIP_CMD))
        root = venv.path
        python = venv.python
        self.useFixture(base.CapturedSubprocess(
            'install-e', [python] + PIP_CMD + ['-e', path]))


class TestInstallWithoutPbr(base.BaseTestCase):

    @testtools.skipUnless(
        os.environ.get('PBR_INTEGRATION', None) == '1',
        'integration tests not enabled')
    def test_install_without_pbr(self):
        # Test easy-install of a thing that depends on a thing using pbr
        tempdir = self.useFixture(fixtures.TempDir()).path
        # A directory containing sdists of the things we're going to depend on
        # in using-package.
        dist_dir = os.path.join(tempdir, 'distdir')
        os.mkdir(dist_dir)
        self._run_cmd(sys.executable, ('setup.py', 'sdist', '-d', dist_dir),
                      allow_fail=False, cwd=PBR_ROOT)
        # testpkg - this requires a pbr-using package
        test_pkg_dir = os.path.join(tempdir, 'testpkg')
        os.mkdir(test_pkg_dir)
        pkgs = {
            'pkgTest': {
                'setup.py': textwrap.dedent("""\
                    #!/usr/bin/env python
                    import setuptools
                    setuptools.setup(
                        name = 'pkgTest',
                        tests_require = ['pkgReq'],
                        test_suite='pkgReq'
                    )
                """),
                'setup.cfg': textwrap.dedent("""\
                    [easy_install]
                    find_links = %s
                """ % dist_dir)},
            'pkgReq': {
                'requirements.txt': textwrap.dedent("""\
                    pbr
                """),
                'pkgReq/__init__.py': textwrap.dedent("""\
                    print("FakeTest loaded and ran")
                """)},
        }
        pkg_dirs = self.useFixture(CreatePackages(pkgs)).package_dirs
        test_pkg_dir = pkg_dirs['pkgTest']
        req_pkg_dir = pkg_dirs['pkgReq']

        self._run_cmd(sys.executable, ('setup.py', 'sdist', '-d', dist_dir),
                      allow_fail=False, cwd=req_pkg_dir)
        # A venv to test within
        venv = self.useFixture(Venv('nopbr', ['pip', 'wheel']))
        python = venv.python
        # Run the depending script
        self.useFixture(base.CapturedSubprocess(
            'nopbr', [python] + ['setup.py', 'test'], cwd=test_pkg_dir))


class TestMarkersPip(base.BaseTestCase):

    scenarios = [
        ('pip-1.5', {'version': 'pip>=1.5,<1.6'}),
        ('pip-6.0', {'version': 'pip>=6.0,<6.1'}),
        ('pip-latest', {'version': 'pip'}),
    ]

    @testtools.skipUnless(
        os.environ.get('PBR_INTEGRATION', None) == '1',
        'integration tests not enabled')
    def test_pip_versions(self):
        pkgs = {
            'test_markers':
                {'requirements.txt': textwrap.dedent("""\
                    pkg_a; python_version=='1.2'
                    pkg_b; python_version!='1.2'
                """)},
            'pkg_a': {},
            'pkg_b': {},
        }
        pkg_dirs = self.useFixture(CreatePackages(pkgs)).package_dirs
        temp_dir = self.useFixture(fixtures.TempDir()).path
        repo_dir = os.path.join(temp_dir, 'repo')
        venv = self.useFixture(Venv('markers'))
        bin_python = venv.python
        os.mkdir(repo_dir)
        for pkg in pkg_dirs:
            self._run_cmd(
                bin_python, ['setup.py', 'sdist', '-d', repo_dir],
                cwd=pkg_dirs[pkg], allow_fail=False)
        self._run_cmd(
            bin_python,
            ['-m', 'pip', 'install', '--upgrade', self.version],
            cwd=venv.path, allow_fail=False)
        self._run_cmd(
            bin_python,
            ['-m', 'pip', 'install', '--no-index', '-f', repo_dir,
             'test_markers'],
            cwd=venv.path, allow_fail=False)
        self.assertIn('pkg-b', self._run_cmd(
            bin_python, ['-m', 'pip', 'freeze'], cwd=venv.path,
            allow_fail=False)[0])
