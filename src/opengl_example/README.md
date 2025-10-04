# QOpenGL 예제 모음

PySide6의 QOpenGL을 사용한 프레임 렌더링 예제들입니다.

## 예제 목록

### 1. frame_counter.py
기본적인 QOpenGLWidget 예제입니다.
- QTimer 기반 (60 FPS 목표)
- 간단한 프레임 카운터

```bash
uv run opengl_example/frame_counter.py
```

### 2. vsync_frame_counter.py ⭐ 
**프레임 드랍 방지** QOpenGLWindow 예제입니다.
- `frameSwapped` 시그널 기반 vsync 동기화
- 트리플 버퍼링으로 스톨 완화
- 프레임 드랍/스킵 최소화
- 종료 버튼 UI 포함
- 1024x768 해상도

```bash
uv run opengl_example/vsync_frame_counter.py
```

**주요 특징:**
- VSync ON: 화면 갱신율과 완벽 동기화
- Triple Buffer: GPU 대기 시간 감소
- frameSwapped 콜백: 표시 완료 후 즉시 다음 프레임 예약

**종료 방법:**
- 툴바의 "종료" 버튼 클릭
- `Q` 키 또는 `ESC` 키

### 3. opengl_camera.py 🎥 실전 응용
**QOpenGLWindow 기반 카메라 애플리케이션**
- frameSwapped 시그널로 프레임 드랍 방지
- Mindvision 카메라 통합
- 실시간 게인/노출시간 제어
- VSync 완벽 동기화

```bash
uv run opengl_example/opengl_camera.py
```

**주요 특징:**
- 프레임 드랍 없는 카메라 표시
- 실시간 카메라 제어 (게인, 노출시간)
- OpenGL ES 3.2 + EGL + Wayland
- 1024x768 해상도

## 기술 비교

| 특성 | frame_counter.py | vsync_frame_counter.py | opengl_camera.py |
|------|------------------|------------------------|------------------|
| 위젯 타입 | QOpenGLWidget | QOpenGLWindow | QOpenGLWindow |
| 프레임 동기화 | QTimer (16ms) | frameSwapped (vsync) | frameSwapped (vsync) |
| 프레임 드랍 | 가능성 있음 | 최소화 | 최소화 |
| 버퍼링 | Double | Triple | Double |
| UI 컨트롤 | 없음 | 종료 버튼 | 카메라 제어 + 종료 |
| 용도 | 학습용 | 데모 | 실전 카메라 |

## 필요한 패키지

- PySide6
- PyOpenGL
- opencv-python (카메라용)
- mvsdk (Mindvision 카메라 SDK)

현재 프로젝트의 `pyproject.toml`에 이미 포함되어 있습니다.

## Jetson Nano Super 최적화

### Wayland + OpenGL ES 3.2 설정
코드에서 자동으로 설정됩니다:
```python
os.environ['QT_QPA_PLATFORM'] = 'wayland-egl'
fmt.setRenderableType(QSurfaceFormat.OpenGLES)
fmt.setVersion(3, 2)
```

### 실행 환경
Weston(Wayland compositor)이 실행 중이어야 합니다:
```bash
# Wayland 확인
ls /run/user/$(id -u)/wayland-*
```

SSH 접속 시 Weston을 먼저 시작한 후 예제를 실행하세요.