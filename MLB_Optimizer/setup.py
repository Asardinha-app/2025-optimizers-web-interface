# MLB Optimizer Setup

from setuptools import setup, find_packages

setup(
    name='mlb-optimizer',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'pandas',
        'ortools',
        'numpy',
        'requests'
    ]
)