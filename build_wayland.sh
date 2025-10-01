#!/bin/bash
#coding=utf-8
# Wayland Presentation C++ 모듈 빌드 스크립트

set -e

echo "🔨 Wayland Presentation C++ 모듈 빌드 중..."

# 프로젝트 루트로 이동
cd "$(dirname "$0")"

# C++ 모듈 빌드
echo "📦 pybind11 확장 빌드..."
uv run python ./cpp/setup.py build_ext --build-lib lib

echo "✅ 빌드 완료!"
echo "📍 모듈 위치: lib/wayland_presentation.*.so"

# 빌드된 파일 확인
ls -lh lib/*.so

