from setuptools import setup, find_packages

setup(
    name="xwrl6432-adc-reader",
    version="0.1.0",
    description="Real-time ADC reader for xWRL6432 mmWave radar via DCA1000",
    author="Leon Braungardt",
    packages=find_packages(exclude=["examples", "radar_config"]),
    install_requires=[
        "numpy",
        "pyserial",
        "tqdm"
    ],
    python_requires=">=3.10",
)