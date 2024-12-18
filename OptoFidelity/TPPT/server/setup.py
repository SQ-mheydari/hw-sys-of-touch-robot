from setuptools import setup, find_packages

setup(name='tntserver',
      version="0.0.1",
      description='TnT Server Mini',
      url='http://www.optofidelity.com',
      author='OptoFidelity',
      author_email='sales@optofidelity.com',
      license='Commercial',
      packages=find_packages(exclude=['docs', 'tests*']),
      package_data={
            'configuration': ['start.txt'],
            'tntserver.drivers.sensors': ['FUTEK USB DLL.dll']
      },
      tests_require=[
            'pytest'
      ]
      zip_safe=False)
