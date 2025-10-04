#coding=utf-8
"""C++ 네이티브 확장 모듈"""

# 간편한 import를 위한 재export
try:
    from .timer_module import *
except ImportError as e:
    print(f"⚠️  timer_module을 불러올 수 없습니다: {e}")
    print("   빌드가 필요할 수 있습니다: ./build_cpp.sh")

try:
    from .wayland_presentation import *
except ImportError as e:
    print(f"⚠️  wayland_presentation을 불러올 수 없습니다: {e}")
    print("   빌드가 필요할 수 있습니다: ./build_cpp.sh")

