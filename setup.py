from setuptools import setup, find_packages
setup(
        name="Kirbytools",
        version="0.1",
        packages=["kirby"],
        author="Dark Kirb",
        description="Tools for editing games using the Return to Dream Land engine",
        license="BSD-2clause",
        entry_points={
            'console_scripts':["read_yaml=kirby.xyaml:c_read_yaml",
                               "write_yaml=kirby.xyaml:c_write_yaml"]
        },
        install_requires=["PyYAML>=3.12"]
        )

