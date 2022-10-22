from setuptools import setup

setup(
    name="hpp-ray",
    version="0.1.0",
    py_modules=["src"],
    install_requires=["click", "pygit2", "tqdm"],
    entry_points={
        "console_scripts": [
            "hpp-ray = src.__main__:cli",
        ],
    },
)
