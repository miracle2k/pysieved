# spec file for RPM
# Contributed by Farkas Levente <lfarkas@bppiac.hu>
#
# Copy this up one directory (out of contrib/) before trying to build an
# RPM!
#
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary:       Python Managesieve Server
Name:          pysieved
Version:       1.0
Release:       0
License:       GPL
Group:         System Environment/Daemons
URL:           http://woozle.org/~neale/src/pysieved/
Source0:       %{name}-%{version}.tar.gz
#Source0:       %{name}-HEAD.tar.gz
#Patch:         pysieved-dovecot.patch
BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-root
BuildRequires: python
BuildArch:     noarch

%description
Python Managesieve Server

%prep
%setup -q -n %{name}
#%patch -p1

%build
sed -i "s|/usr/local/sbin/pysieved.py|%{_sbindir}/%{name}|" contrib/pysieved.xinetd
sed -i "s|--inetd|--inetd --config %{_sysconfdir}/pysieved.ini|" contrib/pysieved.xinetd
sed -i "s|/usr/lib/dovecot/sievec|/usr/libexec/dovecot/sievec|" pysieved.ini
sed -i "s|/usr/lib/dovecot/sievec|/usr/libexec/dovecot/sievec|" plugins/dovecot.py

%install
%{__mkdir_p} $RPM_BUILD_ROOT%{python_sitelib}/%{name}
for i in plugins *.py ; do
	%{__cp} -a $i $RPM_BUILD_ROOT%{python_sitelib}/%{name}/
done
%{__mkdir_p} $RPM_BUILD_ROOT%{_sysconfdir}
install -p -m640 pysieved.ini $RPM_BUILD_ROOT%{_sysconfdir}/
ln -s ../../../../..%{_sysconfdir}/pysieved.ini $RPM_BUILD_ROOT%{python_sitelib}/%{name}/%{name}.ini
%{__mkdir_p} $RPM_BUILD_ROOT%{_sbindir}
ln -s ../../%{python_sitelib}/%{name}/%{name}.py $RPM_BUILD_ROOT%{_sbindir}/%{name}
%{__mkdir_p} $RPM_BUILD_ROOT%{_sysconfdir}/xinetd.d
install -p -m644 contrib/pysieved.xinetd $RPM_BUILD_ROOT%{_sysconfdir}/xinetd.d/%{name}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc COPYING README README.Dovecot THANKS
%config %attr(640,mail,mail) %{_sysconfdir}/%{name}.ini
%config %attr(644,root,root) %{_sysconfdir}/xinetd.d/%{name}
%{python_sitelib}/%{name}
%{_sbindir}/%{name}

%changelog
* Mon Jul 9 2007  <lfarkas@lfarkas.org>
- Initial build.
