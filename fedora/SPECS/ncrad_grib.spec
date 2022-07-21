# Note: define srcarchivename in Travis build only.
%{!?srcarchivename: %global srcarchivename %{name}-%{version}-%{release}}

Name:           ncrad_grib
Version:        0.1
Release:        1%{?dist}
Summary:        Convert radar files between GRIB and NetCDF formats

License:        GPLv3
URL:            https://github.com/ARPA-SIMC/ncrad_grib
Source0:        https://github.com/arpa-simc/%{name}/archive/v%{version}-%{release}.tar.gz#/%{srcarchivename}.tar.gz

BuildRequires:  python3
Requires:       python3
Requires:       python3-eccodes
Requires:       python3-netcdf4
Requires:       python3-numpy

%description
Convert radar files between GRIB and NetCDF formats

%prep
%autosetup

%build
%configure
%make_build


%install
%make_install


%files
%license LICENSE


%changelog
* Thu Jul 21 2022 Emanuele Di Giacomo <edigiacomo@arpae.it>
- First release
