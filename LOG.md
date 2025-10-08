# 기술 로그

프로젝트 개발 중 배운 기술적 지식과 해결 과정을 기록합니다.

## 환경

- **플랫폼**: Jetson Nano Super (Ubuntu 22.04, aarch64)
- **개발**: macOS에서 SSH 원격 접속
- **디스플레이**: HDMI 모니터 직접 연결
- **패키지 관리**: uv

## Wayland vs X11 성능 비교

### Wayland의 장점
프레임 스킵 없이 일정한 프레임 타이밍이 필요한 경우 **Wayland가 더 안정적**입니다.

#### 왜 Wayland가 매끄러운가?
1. **컴포지터 주도 vblank 스케줄링**
   - Weston/Mutter가 디스플레이 vblank에 맞춰 리페인트 관리
   - 클라이언트는 프레임 제출만 담당

2. **Presentation-time 프로토콜**
   - 실제 화면 표시 시각 제공
   - MSC (Monitor Scan Counter) 타임스탬프
   - Presented/Discarded 피드백

3. **단일 컴포지팅 경로**
   - X11의 이중 컴포지팅 문제 없음 (X Server + Compositor)
   - 직접적인 GPU 통신

### X11에서 동일 성능 내기
X11도 올바른 설정으로 Wayland 수준 성능 가능하지만 좀 더 복잡한 작업 필요
3. **전체화면 모드**
   - Desktop compositor 우회 (언리다이렉트)

4. **순수 Xorg 세션**
   - XWayland 경로 사용 금지 (GLX 확장 보장)

### 권장사항
- **카메라 동기화**: Wayland + `opengl_camera.py`
- **X11 필수 시**: `opengl_camera_x11.py` + 추가 최적화

## Jetson Wayland + OpenGL 구성

### 지원되는 구성
```
✅ Wayland + EGL + OpenGL ES 3.2
✅ Wayland + EGL + Desktop GL 4.6
✅ Wayland + Vulkan 1.3
❌ Wayland + GLX (GLX는 X11 전용)
```

### Qt 설정
```python
os.environ['QT_QPA_PLATFORM'] = 'wayland-egl'

fmt = QSurfaceFormat()
fmt.setRenderableType(QSurfaceFormat.OpenGLES)  # EGL 사용
fmt.setVersion(3, 2)                            # OpenGL ES 3.2
fmt.setSwapInterval(1)                          # VSync
```

### EGL Wayland 확장
- `EGL_KHR_platform_wayland`
- `EGL_WL_bind_wayland_display`
- `EGL_WL_wayland_eglstream`

## 패키지 관리 (uv)

### `uv add` vs `uv pip install`

**`uv add` - 패키지 매니저 방식** (npm install과 유사)
```bash
uv add numpy
```
- ✅ `pyproject.toml`에 의존성 기록
- ✅ `uv.lock` 생성 (정확한 버전 고정)
- ✅ 재현 가능 (팀 작업, 배포)
- ❌ 다중 플랫폼 해결로 느릴 수 있음

**`uv pip install` - pip 호환 방식**
```bash
uv pip install numpy
```
- ✅ 빠르고 직접적
- ✅ 특수 인덱스 사용 간편
- ❌ `pyproject.toml` 수정 안 됨
- ❌ 의존성 기록 없음

### 패키지 인덱스

**일반 인덱스 (PyPI)**: 기본 저장소
```bash
uv add numpy  # https://pypi.org/ (자동)
```

**특수 인덱스**: 전용 저장소
```bash
# PyTorch GPU 버전 (PyPI에는 CPU만 있음)
uv pip install torch --index-url https://download.pytorch.org/whl/cu118

# Jetson ARM64 + CUDA
uv pip install torch --extra-index-url https://developer.download.nvidia.com/compute/redist/jp/v60
```

**왜 특수 인덱스가 필요한가?**
- PyTorch CUDA 버전: 용량 큼 (2-3GB), PyPI 100MB 제한
- Jetson: ARM64 + CUDA 전용 빌드
- 회사 내부 패키지

### 실전 권장사항

**일반 패키지**: `uv add`
```bash
uv add pyside6 opencv-python numpy
```

**특수 인덱스 (CUDA, ARM 등)**: `uv pip install`
```bash
# CUDA PyTorch (Jetson)
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**`uv add`로 특수 인덱스 사용** (영구 설정):
```toml
# pyproject.toml
[[tool.uv.index]]
name = "pytorch-cu118"
url = "https://download.pytorch.org/whl/cu118"

[tool.uv.sources]
torch = { index = "pytorch-cu118" }
```

### Jetson 특수 환경: 시스템 패키지 사용

**문제**: Jetson PyTorch (CUDA + ARM64)는 PyPI에 없음
- PyPI에는 x86_64 CUDA 버전만 존재
- ARM64 + CUDA 조합은 NVIDIA가 별도 제공
- uv 가상환경에서는 PyPI CPU 버전만 설치 가능 → **CUDA 사용 불가** ❌

**해결**: `--system-site-packages` + `pyproject.toml`에서 제외

#### `--system-site-packages`의 역할
```bash
uv venv --python 3.10 --system-site-packages
```
- 가상환경에서 **시스템 패키지 접근 허용**
- Python import 순서:
  1. `.venv/lib/python3.10/site-packages/` (가상환경) ← 우선
  2. `/usr/local/lib/python3.10/dist-packages/` (시스템)

#### 시스템 패키지 사용 원리

**핵심**: `pyproject.toml`에서 CUDA 관련 패키지 **제거** 필수

```toml
# pyproject.toml
dependencies = [
    "PySide6==6.8.0.2",
    # torch, numpy, opencv-python 제거 ← 중요!
    # ultralytics 제거 (torch 의존성)
]
```

**작동 방식**:
1. `pyproject.toml`에 **명시하지 않음** → 가상환경에 설치 안 됨
2. 가상환경에 없으면 → `--system-site-packages` 덕분에 시스템에서 찾음
3. 시스템 CUDA PyTorch 사용 ✅

**잘못된 예시** (작동 안 함):
```toml
dependencies = [
    "torch>=2.0.0",  # ❌ PyPI CPU 버전 설치됨
    "ultralytics>=8.3.0",  # ❌ torch를 의존성으로 요구 → CPU 버전 설치
]
# 결과: 가상환경에 CPU torch → CUDA 사용 불가
```

**올바른 예시**:
```toml
dependencies = [
    "PySide6==6.8.0.2",
    # torch, ultralytics 제거 → 시스템 CUDA 버전 사용
]
```

**확인**:
```bash
# 가상환경에서 시스템 CUDA torch 사용 확인
uv run python -c "import torch; print(torch.__version__)"
# → 2.5.0a0+872d972e41.nv24.08 (Jetson CUDA) ✅
```

**주의사항**:
- PyPI에 동일 패키지가 있으면 가상환경이 우선
- 의존성 충돌 가능 (예: numpy 1.x vs 2.x)
- 시스템 패키지와 버전 호환성 확인 필요

## Python 패키지 구조와 실행 방식

### Python vs Node.js 파일 경로 기준

**Python**: 파일 경로는 **현재 작업 디렉토리(cwd)** 기준
```python
# 실행 위치에 따라 달라짐
open("./file.txt")  # cwd 기준
YOLO("./models/model.pt")  # cwd 기준

# 스크립트 파일 기준으로 하려면
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(script_dir, "file.txt")
```

**Node.js**: `require()`/`import`는 **파일 위치** 기준
```javascript
require("./module")  // 현재 파일 기준 (모듈 시스템)
fs.readFile("./file.txt")  // cwd 기준 (파일 시스템)
```

**실전 예시**:
```bash
# 프로젝트 루트에서 실행
uv run src/yolo/convert_model.py

# 코드: YOLO("./models/model.pt")
# 찾는 경로: /project_root/models/model.pt ❌
# 실제 경로: /project_root/src/yolo/models/model.pt ✅
```

### `uv run`이 하는 일
`uv run`은 단순히 Python 인터프리터를 실행하는 것 이상의 작업을 수행합니다:
1. 가상 환경 자동 활성화
2. `PYTHONPATH` 설정
3. 프로젝트 의존성 확인
4. 실행 컨텍스트 구성

### `uv run src/my_app.py` 실행 매커니즘

**Python의 기본 동작**:
```bash
uv run src/cam/ps_camera.py
```

1. **파일 경로로 실행 시**: 그 파일이 있는 디렉토리가 `sys.path[0]`에 자동 추가됨
   - 예: `src/cam/` 디렉토리가 `sys.path[0]`에 추가
   - 같은 레벨의 모듈을 바로 import 가능

2. **네임스페이스 패키지 (PEP 420)**:
   - Python 3.3+ 부터 `__init__.py` 없이도 패키지로 인식
   - `import foo.bar` 형태로 import 가능
   - 더 유연한 프로젝트 구조

3. **`__init__.py`가 필요한 경우**:
   - 외부로 패키지를 배포할 때 (PyPI 등)
   - `python -m package` 방식으로 실행할 때
   - 패키지 초기화 코드가 필요할 때
   - 공개 API를 명시적으로 정의할 때

### sys.path 우선순위
Python은 다음 순서로 모듈을 찾습니다:
1. 실행한 파일이 있는 폴더 (`sys.path[0]`)
2. 현재 작업 디렉토리
3. `PYTHONPATH` 환경변수 경로들
4. 설치된 패키지 (site-packages)

### `sys.path.insert(0, ...)`를 사용하는 이유
서브 디렉토리에서 상위/형제 모듈 접근 시 필요합니다:

```python
# src/opengl_example/opengl_camera.py에서
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# 이제 src/ 디렉토리가 sys.path에 추가됨
from _lib.wayland_utils import setup_wayland_environment  # src/_lib/
from config import CAMERA_IP  # src/config.py
```

**왜 필요한가?**:
- `opengl_camera.py` 실행 시 `sys.path[0]` = `src/opengl_example/`
- `src/_lib/`나 `src/config.py`는 상위 디렉토리에 있음
- 상위 디렉토리를 sys.path에 추가해야 import 가능

### `uv run` vs Editable Install vs 일반 Python

**1. `uv run` (현재 사용, 권장)**
```bash
uv run src/cam/ps_camera.py
```
- ✅ 간단, 직관적
- ✅ 가상환경 자동 관리
- ✅ 설정 불필요
- ❌ `uv` 없이 실행 불가

**2. Editable Install**
```bash
uv pip install -e .
python src/cam/ps_camera.py
```
- ✅ `python` 명령만으로 실행 가능
- ✅ 패키지처럼 사용 가능
- ❌ 설치 단계 필요
- ❌ `pyproject.toml` 설정 필요

**3. 일반 Python**
```bash
python src/cam/ps_camera.py
```
- ✅ Python만 있으면 실행
- ❌ 의존성 수동 관리
- ❌ 경로 문제 발생 가능

### `__init__.py` vs `__main__.py`

**`__init__.py`**
- 패키지 초기화 파일
- `import package` 시 실행됨
- 공개 API 재노출에 사용

```python
# src/cam/__init__.py
from .ps_camera import App
__all__ = ['App']
```

**`__main__.py`**
- 패키지 실행 파일
- `python -m package` 시 실행됨

```python
# src/cam/__main__.py
from .ps_camera import main
main()
```

**현재 프로젝트의 선택**:
- `__init__.py` 없이 `uv run`으로 실행 (간결성)
- 필요한 곳에만 `sys.path.insert()` 사용
- 배포가 아닌 개발 환경에 최적화

## 카메라 관련 문제

### PoE 허브 속도 저하
**문제**: 허브 포트에 따라 GigE 속도 저하로 프레임 드랍

**해결**: 다른 허브 포트로 이동

### 카메라 IP 설정
**문제**: 설정한 IP와 확인된 IP가 다름

**원인**: 카메라 재시작 전 설정 미적용

**해결**: 
1. `set_camera_ip.py` 실행 후 1초 대기
2. 카메라 전원 재시작

## 발생한 문제와 해결

### 1. PySide6 설치 오류
**문제**: `manylinux_2_35_aarch64` vs `manylinux_2_39_aarch64` 불일치

**해결**: `PySide6==6.8.0.2` 호환 버전 사용

### 2. SSH GUI 표시 문제
**문제**: SSH 접속에서 GUI가 로컬 모니터에 표시 안 됨

**해결**: `os.environ['DISPLAY'] = ':0'` (X11) 또는 Wayland 자동 설정

### 3. libxcb-cursor 누락
**문제**: Qt xcb 플랫폼 플러그인 로드 실패

**해결**: `sudo apt install -y libxcb-cursor0`

## 성능 측정

### GPU Fence 기반 프레임 드랍 감지
```python
# paintGL 시작 전
status = GL.glClientWaitSync(self.last_fence, 0, 0)
if status == GL.GL_TIMEOUT_EXPIRED:
    # GPU가 이전 프레임을 아직 처리 중
    print("GPU 블록 감지")
```

### Wayland Presentation 모니터링
```python
# C++ 모듈 사용
monitor = WaylandPresentationMonitor()
monitor.set_callback(on_feedback)
monitor.request_feedback()

# 통계 확인
presented = monitor.presented_count()
discarded = monitor.discarded_count()
```



## C++ 통합

### pybind11 빌드
```bash
./build_cpp.sh
# 출력: src/_native/timer_module.*.so
#       src/_native/wayland_presentation.*.so
```

### Python에서 사용
```python
from _native.timer_module import HardwareTimer
from _native.wayland_presentation import WaylandPresentationMonitor
```

## 코드 품질

### 에러 처리 원칙
1. **Fallback 금지**: 요청대로 작동하지 않으면 명확한 오류
2. **오류 무시 금지**: `except: pass` 사용 금지
3. **명확한 오류 메시지**: 문제 파악 가능하도록

```python
# ❌ 잘못된 예시
try:
    risky_operation()
except:
    pass

# ✅ 올바른 예시
try:
    risky_operation()
except Exception as e:
    print(f"❌ 작업 실패: {e}")
    raise
```

## 참고 자료

- [Jetson Weston/Wayland](https://docs.nvidia.com/jetson/archives/r38.2/DeveloperGuide/SD/WindowingSystems/WestonWayland.html)
- [Wayland Presentation Protocol](https://wayland.app/protocols/presentation-time)
- [Qt Platform Native Interface](https://doc.qt.io/qt-6/qguiapplication.html#platformNativeInterface)
- [PEP 420 - Namespace Packages](https://peps.python.org/pep-0420/)
