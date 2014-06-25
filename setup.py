from distutils.core import setup

setup(
    name='rgcompare',
    version='0.2',
    maintainer='J. Falke',
    maintainer_email='johannesfalke@gmail.com',
    url='https://github.com/mueslo/rgcompare',
    license='LICENSE',
    description='A robot comparison tool for rgkit.',
    long_description=open('README.rst').read(),
    py_modules=['rgcompare'],
    entry_points={
        'console_scripts': [
            'rgcompare = rgcompare:main'
        ]
    },
    install_requires=[
        "rgkit >= 0.4.1",
        "numpy >= 1.8.1",
        "matplotlib >= 1.3.1",
    ],
)
