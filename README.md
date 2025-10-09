# plug-proto

Jetson Nano Super용 PySide6 카메라 동기화 프로젝트

## 개요

Mindvision GigE 카메라와 디스플레이 VSync를 정밀하게 동기화하여 프레임 드랍 없는 영상 표시를 구현합니다.

## 프로젝트 구조

```
plug-proto/
├── src/
│   ├── cam/
│   │   ├── ps_camera.py              # 메인 카메라 애플리케이션
│   │   └── ps_camera_modules/        # 카메라 모듈들
│   ├── opengl_example/
│   │   ├── opengl_camera.py          # OpenGL 카메라 (Wayland)
│   │   ├── opengl_camera_x11.py      # OpenGL 카메라 (X11)
│   │   └── camera_controller.py      # 카메라 제어
│   ├── set_camera_ip.py              # 카메라 IP 설정 도구
│   ├── config.py                     # 카메라 설정 (IP, 서브넷, 게이트웨이)
│   ├── _lib/
│   │   ├── mvsdk.py                  # Mindvision SDK
│   │   └── wayland_utils.py          # Wayland 환경 설정
│   └── _native/                      # C++ 컴파일된 모듈
├── cpp/
│   ├── timer.cpp                     # 하드웨어 타이머
│   ├── wayland_presentation.cpp      # Wayland presentation 모니터
│   └── setup.py                      # C++ 빌드 설정
├── config.py                         # 프로젝트 설정
└── pyproject.toml                    # 패키지 설정
```

## 환경 설정

### 필수 시스템 패키지
QT에서 PySide6 사용시 다음 `libxcb-cursor0` 패키지 설치 필요
```bash
sudo apt update && sudo apt install -y libxcb-cursor0
```

### Python 환경
- Python 3.12+ 필요
- uv 패키지 매니저 사용

### Wayland 활성화 (권장)
```bash
nvstart-weston.sh
```
자세한 내용: [Jetson Weston/Wayland](https://docs.nvidia.com/jetson/archives/r38.2/DeveloperGuide/SD/WindowingSystems/WestonWayland.html)

### SSH 접속 시
```bash
export DISPLAY=:0  # X11 사용 시
# Wayland는 자동 설정됨
```

## 설치

```bash
# 1. 의존성 설치
uv sync

# 2. C++ 모듈 빌드
./build_cpp.sh
```

## 카메라 설정

### 1. 카메라 IP 주소 설정
`config.py` 파일 수정:
```python
CAMERA_IP = "192.168.0.100"
SUBNET_MASK = "255.255.255.0"
GATEWAY = "192.168.0.1"
```

### 2. 카메라 IP 설정 적용
```bash
uv run src/set_camera_ip.py
```

## 실행

### 1. 메인 카메라 애플리케이션 (QPainter, Wayland) ⭐ 권장
```bash
uv run src/cam/ps_camera.py
```
**특징**:
- VSync 동기화로 프레임 드랍 없음
- 프레임 번호 표시
- 게인/노출시간 실시간 조정
- 검은 화면 ↔ 카메라 화면 교대 표시

### 2. OpenGL 카메라 (Wayland)
```bash
uv run src/opengl_example/opengl_camera.py
```
**특징**:
- OpenGL ES 3.2 + EGL + Wayland
- GPU fence 기반 프레임 드랍 감지
- Wayland presentation protocol 모니터링
- 부하 테스트 모드

### 3. OpenGL 카메라 (X11)
```bash
uv run src/opengl_example/opengl_camera_x11.py
```
**특징**:
- OpenGL 4.6 + X11
- GLX 기반 렌더링
- X11 환경에서 사용 시

### 4. OpenGL 예제 (학습용)
```bash
# 기본 프레임 카운터
uv run src/opengl_example/frame_counter.py

# VSync 동기화 프레임 카운터
uv run src/opengl_example/vsync_frame_counter.py
```

## 기능

### 프레임 동기화
- **VSync 기반**: 디스플레이 수직 동기화에 맞춘 카메라 트리거
- **프레임 드랍 감지**: GPU fence와 Wayland presentation으로 실시간 감지
- **타이밍 조정**: 노출시간, VSync 딜레이 슬라이더로 미세 조정

### 카메라 제어
- 게인 조정 (0-100)
- 노출시간 조정 (1-30ms)
- 소프트 트리거 모드

### 모니터링
- 프레임 번호, FPS
- GPU 블록 카운트
- Presented/Discarded 프레임 통계
- VSync 동기화 상태

## 개발 환경

- **플랫폼**: Jetson Nano Super (Ubuntu 22.04, ARM64)
- **디스플레이**: Wayland (권장) 또는 X11
- **카메라**: Mindvision GigE Camera (MV-GE134GC-IT)
- **패키지 관리**: uv

## 성능 최적화

### ⚡ Jetson 성능 모드 설정 (필수)

**최고 성능을 위해 반드시 실행하세요:**

```bash
# 최대 전원 모드 + 최대 클럭 활성화
sudo nvpmodel -m 2 && sudo jetson_clocks
```

**명령어 설명**:
- `nvpmodel -m 2`: 전원 모드를 최대 성능 모드로 설정
  - Orin Nano Super: 모드 2 = 15W (모든 CPU/GPU 코어 활성화)
  - 다른 모드는 전력 절약을 위해 성능 제한
- `jetson_clocks`: 모든 CPU, GPU 클럭을 최대 주파수로 고정
  - 기본 상태는 동적 클럭 조정 (DVFS) → 성능 변동
  - 고정 클럭 → 일관된 최고 성능

**성능 차이 (YOLO 추론 기준)**:
- 기본 모드: ~150-200ms (불안정)
- 최적화 모드: ~60-112ms (안정적) ⚡

**재부팅 시 재설정 필요**:
```bash
# 부팅 시 자동 실행하려면 (선택사항)
echo "sudo nvpmodel -m 2" >> ~/.bashrc
echo "sudo jetson_clocks" >> ~/.bashrc
```

### Wayland (권장)
- 컴포지터 주도 VSync 스케줄링
- Presentation-time 프로토콜로 정확한 타이밍
- 프레임 드랍 최소화

### X11 (대안)
- GLX_OML_sync_control 확장 필요
- `__GL_SYNC_TO_VBLANK=1` 환경변수 설정
- 전체화면 모드 권장

자세한 내용은 `LOG.md` 참조.

**참고**: [NVIDIA Jetson 성능 최적화](https://docs.ultralytics.com/ko/guides/nvidia-jetson/#nvidia-jetson-사용-시-모범-사례)

## 문제 해결

### 카메라를 찾을 수 없음
1. 네트워크 연결 확인 (GigE 포트)
2. 카메라 IP 설정 확인 (`config.py`)
3. `uv run src/set_camera_ip.py` 실행

### Wayland 디스플레이를 찾을 수 없음
```bash
nvstart-weston.sh
```

### libxcb-cursor 오류
```bash
sudo apt install -y libxcb-cursor0
```

