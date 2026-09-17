from setuptools import setup, find_packages

setup(
    name="sia-package",
    version="0.2.0a1",
    description="Self-Improving Agents (SIA) - A portable, host-agnostic instruction package that turns any coding assistant into a self-improving project collaborator.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="GunjanGrunge",
    url="https://github.com/GunjanGrunge/SIA_package",
    license="MIT",
    py_modules=["cli", "banner"],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "sia=cli:main",
            "sia-agent=cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.9",
)
