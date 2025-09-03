from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup
import os

ext_modules = [
    Pybind11Extension(
        "timer_module",
        [os.path.join(os.path.dirname(__file__), "timer.cpp")],
        cxx_std=14,
    ),
]

setup(
    name="timer_module",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
