from setuptools import setup

setup(name='remote_params',
      version='0.0.1',
      description='Remote controllable params',
      url='http://github.com/markkorput/pyremoteparams',
      author='Mark van de Korput',
      author_email='dr.theman@gmail.com',
      license='MIT',
      install_requires=[
            'evento>=1.0.2',
            # 'oscpy' # added embedded copy of oscpy, with some bind_all patch
            'websockets>=8.1'
      ],
      zip_safe=True,
      test_suite='nose.collector',
      tests_require=['nose'],)
