#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="multitaskflow",
    version="0.1.0",
    author="Polaris",
    author_email="polaris0532@outlook.com",
    description="一个用于管理和监控多个任务执行的Python工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Polaris-F/MultiTaskFlow",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "pyyaml>=5.1",
        "psutil>=5.8.0",
        "python-dotenv>=0.19.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "taskflow=multitaskflow.task_flow:main",
        ],
    },
) 