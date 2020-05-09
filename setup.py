from setuptools import setup, find_packages


setup(
    name='kpopnet',
    version='0.0.0',
    author='Kagami Hiiragi',
    author_email='kagami@genshiken.org',
    url='https://github.com/kpopnet/kpopnet',
    description='kpopnet web spiders and utils',
    license='CC0',
    packages=find_packages(),
    entry_points={'console_scripts': ['kpopnet = kpopnet.cli:main']},
    install_requires=['docopt>=0.6.2', 'scrapy>=2.1.0', 'Pillow>=7.1.2'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
)
