import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="PyRMVtransport",
    version="0.2.5",
    author="cgtobi",
    author_email="cgtobi@gmail.com",
    python_requires=">=3.5.3",
    description="Get transport information from opendata.rmv.de",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cgtobi/PyRMVtransport",
    packages=setuptools.find_packages(exclude=("tests",)),
    install_requires=["lxml", "aiohttp"],
    license="MIT",
    classifiers=(
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ),
)
