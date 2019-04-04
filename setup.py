from setuptools import setup, find_packages


with open("README.rst", "r") as f:
    DESCRIPTION = f.read()


# read out version.
with open("lsp/_version.py", "r") as f:
    exec(f.read())


setup(
    name="lsp",
    version=__version__,
    author="WindSoilder",
    author_email="WindSoilder@outlook.com",
    url="https://github.com/WindSoilder/lsp",
    description="Sans-IO pattern, language server protocol implementation",
    long_description=DESCRIPTION,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Intended Audience :: Developers",
    ],
    packages=find_packages(".", exclude=("*tests",)),
    python_requires=">=3.6",
    license="MIT",
    zip_safe=False,
)
