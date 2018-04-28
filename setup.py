from setuptools import setup, find_packages
setup(
    name="Kirbytools",
    version="0.1",
    packages=["kirby", "kirby.utils", "kirby.rom", "kirby.compression"],
    author="Dark Kirb",
    description="Tools for editing Kirby games",
    license="BSD-2clause",
    entry_points={
        "console_scripts": [
            "hal_compress = kirby.compression.hal:compress_main",
            "hal_decompress = kirby.compression.hal:decompress_main",
            "lz11_compress = kirby.compression.lz11:compress_main",
            "lz11_decompress = kirby.compression.lz11:decompress_main"
        ]
    },
    install_requires=["PyYAML>=3.12"]
)
