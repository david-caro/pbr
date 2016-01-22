%define name python-pbr
%define version 1.8.2.dev31
%define unmangled_version %{version}
%define release 2%{?dist}

Summary: Python Build Reasonableness
Name: %{name}
Version: %{version}
Release: %{release}
Source0: pbr-%{unmangled_version}.tar.gz
License: UNKNOWN
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: OpenStack <openstack-dev@lists.openstack.org>
Url: http://pypi.python.org/pypi/pbr
BuildRequires: python, python-setuptools


# Per-distro special cases
%if 0%{?fedora} == 23
Requires: python >= 2.7
%endif

%if 0%{?fedora} == 22
Requires: python >= 2.7
%endif

%if 0%{?rhel} == 7
Requires: python >= 2.7
Requires: python-setuptools
%endif

%if 0%{?rhel} == 6
Requires: python
Requires: python-setuptools
%endif


%description
Introduction
============

PBR is a library that injects some useful and sensible default behaviors
into your setuptools run. It started off life as the chunks of code that
were copied between all of the `OpenStack`_ projects. Around the time that
OpenStack hit 18 different projects each with at least 3 active branches,
it seemed like a good time to make that code into a proper reusable library.

PBR is only mildly configurable. The basic idea is that there's a decent
way to run things and if you do, you should reap the rewards, because then
it's simple and repeatable. If you want to do things differently, cool! But
you've already got the power of Python at your fingertips, so you don't
really need PBR.

PBR builds on top of the work that `d2to1`_ started to provide for declarative
configuration. `d2to1`_ is itself an implementation of the ideas behind
`distutils2`_. Although `distutils2`_ is now abandoned in favor of work towards
`PEP 426`_ and Metadata 2.0, declarative config is still a great idea and
specifically important in trying to distribute setup code as a library
when that library itself will alter how the setup is processed. As Metadata
2.0 and other modern Python packaging PEPs come out, PBR aims to support
them as quickly as possible.

You can read more in `the documentation`_.

Running Tests
=============
The testing system is based on a combination of `tox`_ and `testr`_. The canonical
approach to running tests is to simply run the command ``tox``. This will
create virtual environments, populate them with dependencies and run all of
the tests that OpenStack CI systems run. Behind the scenes, tox is running
``testr run --parallel``, but is set up such that you can supply any additional
testr arguments that are needed to tox. For example, you can run:
``tox -- --analyze-isolation`` to cause tox to tell testr to add
``--analyze-isolation`` to its argument list.

It is also possible to run the tests inside of a virtual environment
you have created, or it is possible that you have all of the dependencies
installed locally already. If you'd like to go this route, the requirements
are listed in ``requirements.txt`` and the requirements for testing are in
``test-requirements.txt``. Installing them via pip, for instance, is simply::

  pip install -r requirements.txt -r test-requirements.txt


In you go this route, you can interact with the testr command directly.
Running ``testr run`` will run the entire test suite. ``testr run --parallel``
will run it in parallel (this is the default incantation tox uses). More
information about testr can be found at: http://wiki.openstack.org/testr

.. _OpenStack: https://www.openstack.org/
.. _`the documentation`: http://docs.openstack.org/developer/pbr/
.. _tox: http://tox.testrun.org/
.. _d2to1: https://pypi.python.org/pypi/d2to1
.. _distutils2: https://pypi.python.org/pypi/Distutils2
.. _PEP 426: http://legacy.python.org/dev/peps/pep-0426/
.. _testr: https://wiki.openstack.org/wiki/Testr
'

%prep
%setup -n pbr-%{unmangled_version} -n pbr-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
