import os,setuptools
import Yinotify
_DESCRIPTION = "Based on pyinotfy, simplify the module by removing unused class and add new useful function to implement the callback"

setuptools.setup(
    name='Yinotify',
    version=Yinotify.__version__,
    description=_DESCRIPTION,
    long_description=open('README.rst').read(),
    classifiers=[
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6"
        ],
    keywords='Yinotify',
    packages=setuptools.find_packages(exclude=['tests']),
    url='https://github.com/peter-zyj/Yinotify',
    author='Yijun Zhu',
    author_email='peter_zyj@hotmail.com',
    license='GPL 2',
    zip_safe=True,
    platforms=["Linux"]

)

