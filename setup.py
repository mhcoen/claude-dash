#!/usr/bin/env python
"""Setup script for claude-dash"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="claude-dash",
    version="1.0.0",
    author="Michael Coen",
    author_email="mhcoen@gmail.com",
    description="Know exactly when your Claude Code session will run out",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mhcoen/claude-dash",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyQt6>=6.4.0",
        "pyqt6-tools>=6.4.0",
    ],
    entry_points={
        "console_scripts": [
            "claude-dash=claude_dash.main:main",
        ],
    },
)