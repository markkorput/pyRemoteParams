from setuptools import setup

long_description = ''
with open(os.path.join(os.path.dirname(__name__), 'README.md')) as f:
    long_description = f.read()

setup(name='remote_params',
      version='0.0.2',
      description='Remote controllable params',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='http://github.com/markkorput/pyremoteparams',
      author='Mark van de Korput',
      author_email='dr.theman@gmail.com',
      license='MIT',
      install_requires=[
            'evento>=1.0.2',
            # 'oscpy' # added embedded copy of oscpy, with bind_all patch
            'websockets>=8.1'
      ],
      zip_safe=True,
      # include_package_data=True,
      test_suite='nose.collector',
      tests_require=['nose'],
      classifiers=[
            'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
            'License :: OSI Approved :: MIT License',   # Again, pick a license
            'Programming Language :: Python :: 3',      #Specify which pyhton versions that you want to support
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
      ])

