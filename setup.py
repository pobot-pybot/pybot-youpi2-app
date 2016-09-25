from setuptools import setup, find_packages

setup(
    name='pybot-youpi2-app',
    setup_requires=['setuptools_scm'],
    use_scm_version=True,
    namespace_packages=['pybot', 'pybot.youpi2'],
    packages=find_packages("src"),
    package_dir={'': 'src'},
    url='',
    license='',
    author='Eric Pascual',
    author_email='eric@pobot.org',
    install_requires=['pybot-core', 'pybot-youpi2', 'nros-youpi2'],
    download_url='https://github.com/Pobot/PyBot',
    description='Youpi2 base classes for application development',
)
