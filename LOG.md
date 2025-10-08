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

## Python 패키지 구조와 실행 방식

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
