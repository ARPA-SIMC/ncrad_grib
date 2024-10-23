# Note: define srcarchivename in Travis build only.
%{!?srcarchivename: %global srcarchivename %{name}-%{version}-%{release}}

Name:           ncrad_grib
Version:        0.2
Release:        1
Summary:        Convert radar files between GRIB and NetCDF formats

License:        GPLv3
URL:            https://github.com/ARPA-SIMC/ncrad_grib
Source0:        https://github.com/arpa-simc/%{name}/archive/v%{version}-%{release}.tar.gz#/%{srcarchivename}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
Requires:       python3
Requires:       python3-eccodes
Requires:       python3-netcdf4
Requires:       python3-numpy

%description
Convert radar files between GRIB and NetCDF formats

%prep
%setup -q -n %{srcarchivename}

%build
%py3_build

%install
%py3_install

%files
%{python3_sitelib}/%{name}
%{python3_sitelib}/%{name}*.egg-info
%{_bindir}/radar_grib2netcdf
%{_bindir}/radar_netcdf2grib
%license LICENSE

%changelog
* Wed Oct 23 2024 Emanuele Di Giacomo <edigiacomo@arpae.it> - 0.2-1
- Modified code to read every possible netcdf in the radar archive and to handle netcdf compliant with version 1.8
- Added the management of accumulated precipitation in minutes
- In the conversion from grib to netcdf the output is a netcdf compliant with version 1.8

* Thu Jul 21 2022 Emanuele Di Giacomo <edigiacomo@arpae.it> - 0.1-3
- Fixed macro

* Thu Jul 21 2022 Emanuele Di Giacomo <edigiacomo@arpae.it> - 0.1-2
- First release
