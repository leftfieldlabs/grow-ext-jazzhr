from setuptools import setup


setup(
    name='grow-ext-jazzhr',
    version='1.0.0',
    license='MIT',
    author='Eric Lee',
    author_email='eric@leftfieldlabs.com',
    packages=[
        'jazzhr',
    ],
    install_requires = [
        'bleach',
    ],
)
