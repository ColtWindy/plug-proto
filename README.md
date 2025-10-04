# plug-proto

Jetson Orin Nano용 PySide6 + C++ 하드웨어 타이머 프로젝트

## 개요
이 프로젝트는 Python과 C++을 결합하여 다음 기능을 제공합니다:
- PySide6 GUI를 사용한 실시간 프레임 카운터 표시
- C++ 하드웨어 타이머를 통한 정밀한 시간 측정
- pybind11을 통한 Python-C++ 연동

## 프로젝트 구조
```
plug-proto/
├── cpp/
│   ├── timer.cpp          # 하드웨어 타이머 + pybind11 바인딩
│   └── setup.py           # 빌드 설정
├── lib/                   # 컴파일된 .so 파일 위치
├── main.py                # 메인 Python 애플리케이션
└── pyproject.toml         # 프로젝트 설정
```

## 설치 및 실행
### 0. 환경 설정
QT에서 PySide6 사용시 다음 `libxcb-cursor0`가 필요함

```bash
sudo apt update && sudo apt install -y libxcb-cursor0
```
- ssh접속시 DISPLAY 환경변수 설정 필요시: `export DISPLAY=:0`

Wayland 활성화. 자세한 내용은 다음 링크를 참고한다.
https://docs.nvidia.com/jetson/archives/r38.2/DeveloperGuide/SD/WindowingSystems/WestonWayland.html#sd-windowingsystems-westonwayland

단순 wayland실행시는 `nvstart-weston.sh`를 실행한다.

- Python버전은 3.12가 필요함

### 1. 의존성 설치
```bash
# uv 사용 (권장)
uv sync

# 또는 pip 사용
pip install PySide6 opencv-python pybind11 setuptools numpy
```

### 2. C++ 모듈 빌드
```bash
uv run python ./cpp/setup.py build_ext --build-lib lib
```

### 3. 애플리케이션 실행
```bash
uv run python main.py
```

## 기능
- **PySide6 GUI**: 안정적인 Qt 기반 GUI 창
- **프레임 카운터**: 실시간으로 프레임 번호가 화면에 표시됩니다
- **성능 모니터링**: FPS, 경과 시간, 타이머 타입 정보 표시
- **하드웨어 타이머**: C++로 구현된 고정밀 타이머 사용
- **카메라 지원**: 웹캠이 없을 경우 더미 프레임으로 동작

## 조작법
- 창 닫기 버튼으로 애플리케이션 종료

## 개발 환경
- Ubuntu (Jetson Orin Nano)
- Python 3.11+
- PySide6 6.8+
- OpenCV 4.12+
- pybind11 3.0+

## Wayland vs X11 성능 차이
프레임 스킵 없이 ms-단위로 일정한 프레임 타이밍이 필요한 경우, **Wayland가 X11보다 안정적**입니다.

### 왜 Wayland가 더 매끄러운가?
- **컴포지터 주도 vblank 스케줄링**: Weston/Mutter 등이 디스플레이 vblank 타이밍에 맞춰 리페인트 루프를 관리
- **presentation-time 프로토콜**: 실제 화면 표시 시각과 MSC(모니터 스캔 카운터) 타임스탬프를 제공
- **단일 컴포지팅 경로**: X11의 이중 컴포지팅(X Server + Compositor) 문제가 없음

### X11에서 동일 성능을 내려면?
X11도 올바른 설정으로 Wayland 수준의 성능을 낼 수 있습니다:
1. **GLX_OML_sync_control 확장 사용**: `glXWaitForMscOML()`로 vblank에 직접 동기화
2. **환경변수 설정**: `__GL_SYNC_TO_VBLANK=1`, `__GL_MaxFramesAllowed=1` (triple buffering 방지)
3. **전체화면 모드**: Desktop compositor 우회 (언리다이렉트)
4. **순수 Xorg 세션**: XWayland 경로 사용 금지 (GLX 확장 보장)

### 권장사항
- **카메라 동기화 앱**: Wayland 사용 권장 (`nvstart-weston.sh` + `QT_QPA_PLATFORM=wayland-egl`)
- **X11 필수 시**: `opengl_camera_x11.py` 참고 (추가 최적화 필요)
