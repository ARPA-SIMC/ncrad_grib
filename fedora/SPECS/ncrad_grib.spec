# Note: define srcarchivename in Travis build only.
%{!?srcarchivename: %global srcarchivename %{name}-%{version}-%{release}}

Name:           ncrad_grib
Version:        0.1
Release:        2
Summary:        Convert radar files between GRIB and NetCDF formats

License:        GPLv3
URL:            https://github.com/ARPA-SIMC/ncrad_grib
Source0:        https://github.com/arpa-simc/%{name}/archive/v%{version}-%{release}.tar.gz#/%{srcarchivename}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
Requires:       python3
Requires:       python3-eccodes
Requires:       python3-netcdf4
Requires:       python3-numpy

%description
Convert radar files between GRIB and NetCDF formats

%prep
%setup -q -n %{srcarchivename}

%build
%pyproject_wheel

%install
%pyproject_install

%files
%{python3_sitelib}/%{name}
%{python3_sitelib}/%{name}*.dist-info
%{_bindir}/radar_grib2netcdf
%{_bindir}/radar_netcdf2grib
%license LICENSE

%changelog
* Thu Jul 21 2022 Emanuele Di Giacomo <edigiacomo@arpae.it> - 0.1-2
- First release
