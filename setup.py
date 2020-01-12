from setuptools import setup

setup(name='remote_params',
      version='0.0.1',
      description='Remote controllable params',
      url='http://github.com/markkorput/pyremoteparams',
      author='Mark van de Korput',
      author_email='dr.theman@gmail.com',
      license='MIT',
      install_requires=[
            'evento'],
      zip_safe=True,
      test_suite='nose.collector',
      tests_require=['nose'],)
