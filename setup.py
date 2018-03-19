from setuptools import setup, find_packages
setup(
        name="Kirbytools",
        version="0.1",
        packages=["kirby","kirby.utils"],
        author="Dark Kirb",
        description="Tools for editing games using the Return to Dream Land engine",
        license="BSD-2clause",
        entry_points={},
        install_requires=["PyYAML>=3.12"]
        )

