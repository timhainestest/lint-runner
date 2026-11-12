import os
from setuptools import setup
setup(name="ci-sandbox-pkg",
      version=os.environ.get("BUILD_VERSION", "0.0.0"),
      packages=["ci_sandbox_pkg"],
      package_data={"ci_sandbox_pkg": ["marker.txt"]},
      include_package_data=True)
