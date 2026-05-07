from setuptools import setup, find_packages

setup(
    name="kora",
    version="0.3.0",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy",
        "requests",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "kora-service=kora.service:main",
            "kora-simulation=kora.simulation:main",
        ],
    },
)
