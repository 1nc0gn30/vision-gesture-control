#!/usr/bin/env python3
"""
Setup script for vision-gesture-control.
Pure Python stdlib zero-dependency package.
"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read() if hasattr(fh, "read") else ""

setup(
    name="vision-gesture-control",
    version="1.0.0",
    author="Google DeepMind Advanced Agentic Coding",
    description="Pure Python Zero-Dependency MCP Server, CLI & Material 3 Web Studio for Vision Gesture Control",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/google/vision-gesture-control",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": ["pytest>=7.0.0"],
    },
    entry_points={
        "console_scripts": [
            "vision-control=vision_gesture_control.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
    ],
)
