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
