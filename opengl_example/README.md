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

### 2. vsync_frame_counter.py ⭐ 권장
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

## 기술 비교

| 특성 | frame_counter.py | vsync_frame_counter.py |
|------|------------------|------------------------|
| 위젯 타입 | QOpenGLWidget | QOpenGLWindow |
| 프레임 동기화 | QTimer (16ms) | frameSwapped (vsync) |
| 프레임 드랍 | 가능성 있음 | 최소화 |
| 버퍼링 | 기본 | Triple Buffer |
| UI 버튼 | 없음 | 종료 버튼 |
| 해상도 | 800x600 | 1024x768 |

## 필요한 패키지

- PySide6
- PyOpenGL

현재 프로젝트의 `pyproject.toml`에 이미 포함되어 있습니다.

## Jetson Nano Super 최적화

Wayland 환경에서 GPU 가속을 위해 다음 환경변수 사용 가능:
```bash
export QT_QPA_PLATFORM=wayland-egl
export DISPLAY=:0
```

SSH 접속 시에는 `DISPLAY=:0` 설정 필수입니다.