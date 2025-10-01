from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup
import os

cpp_dir = os.path.dirname(__file__)

ext_modules = [
    Pybind11Extension(
        "timer_module",
        [os.path.join(cpp_dir, "timer.cpp")],
        cxx_std=14,
    ),
    Pybind11Extension(
        "wayland_presentation",
        [os.path.join(cpp_dir, "wayland_presentation.cpp")],
        cxx_std=17,
        include_dirs=[],
        libraries=[],
    ),
]

setup(
    name="cpp_modules",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
