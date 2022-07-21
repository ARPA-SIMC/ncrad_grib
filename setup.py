import os
import re

from setuptools import setup


def get_version(package):
    # Thanks to Tom Christie
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


setup(
    name="ncrad_grib",
    version=get_version('ncrad_grib'),
    install_requires=[
        "numpy", "netCDF4", "eccodes",
    ],
    packages=["ncrad_grib"],
    entry_points={
        'console_scripts': [
            'radar_grib2netcdf = ncrad_grib.radar_grib2netcdf:main',
            'radar_netcdf2grib = ncrad_grib.radar_netcdf2grib:main',
        ]
    }
)
