
from setuptools import setup

setup(
   name='rijkswaterstaat',
   version='0.1',
   description='packages for getting rijkswaterstaat data',
   author='Isaac Williams',
   author_email='isaac.williams.devel@gmail.com',
   include_package_data=True,
   packages=['waterinfo', 'opendap'],
   install_requires=[
       'bs4',
       'netCDF4',
       'pandas',
       'pytz',
       'pyproj',
       'requests',
       'sqlalchemy',
       ],  # external packages as dependencies
)
