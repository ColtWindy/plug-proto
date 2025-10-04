# 프로젝트 개발 로그

## 환경

- **플랫폼**: Jetson Orin Nano (Ubuntu 22.04, aarch64)
- **개발 환경**: macOS에서 SSH 원격 접속
- **디스플레이**: Jetson에 HDMI 모니터 직접 연결
- **패키지 관리**: uv

## 발생한 문제들과 해결 과정

### 1. PySide6 설치 문제

**문제**: uv가 자동으로 선택한 PySide6 최신 버전(6.9.x)이 `manylinux_2_35_aarch64` 플랫폼에서 wheel 호환성 오류

```
error: Distribution `pyside6==6.9.2` can't be installed because it doesn't have a source distribution or wheel for the current platform
hint: You're on Linux (`manylinux_2_35_aarch64`), but `pyside6` (v6.9.2) only has wheels for: `manylinux_2_28_x86_64`, `manylinux_2_39_aarch64`
```

**원인**: PySide6 6.9.x 버전은 `manylinux_2_39_aarch64`를 요구하지만 Jetson은 `manylinux_2_35_aarch64` 환경

**해결**:

- 시스템 Qt6 설치: `sudo apt install qt6-base-dev qt6-tools-dev`
- 호환되는 안정 버전 사용: `PySide6==6.8.0.2` (실제 최신 안정 버전)

### 4. SSH 접속 시 GUI 표시 문제

**문제**: SSH 원격 접속에서 GUI가 Jetson 로컬 모니터에 표시되지 않음

**원인**: SSH 세션에서는 DISPLAY 환경변수가 설정되지 않음

**해결**: 코드에 `os.environ['DISPLAY'] = ':0'` 추가하여 Jetson 로컬 디스플레이로 강제 지정

### 5. libxcb-cursor 라이브러리 누락

**문제**: Qt xcb 플랫폼 플러그인 로드 실패

```
libxcb-cursor.so.0: cannot open shared object file: No such file or directory
qt.qpa.plugin: From 6.5.0, xcb-cursor0 or libxcb-cursor0 is needed to load the Qt xcb platform plugin
```

**해결**: `sudo apt install -y libxcb-cursor0`

### 6. Qt 플러그인 경고

**문제**: `This plugin does not support propagateSizeHints()` 등 무해한 경고 메시지

**해결**: `os.environ['QT_LOGGING_RULES'] = 'qt.qpa.plugin=false'`

## 최종 해결책 요약

### 핵심 설정 (main.py 내부)

```python
# 젯슨 로컬 디스플레이 환경 설정 (SSH 접속 시)
os.environ['DISPLAY'] = ':0'

# Qt 로깅 경고 억제
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.plugin=false'
```

### 필수 시스템 패키지

```bash
sudo apt install -y qt6-base-dev qt6-tools-dev libxcb-cursor0
```

### 프로젝트 의존성 (pyproject.toml)

```toml
dependencies = [
    "PySide6==6.8.0.2",  # 호환 버전 고정
    "opencv-python>=4.12.0.88",
    "pybind11>=3.0.1",
    "setuptools>=80.9.0",
    "numpy>=2.0.0",
]
```

### PoE 허브문제

- 허브 연결시 포트에 따라 GigE속도가 저하되어 프레임이 저하되는 문제가 있음. 해결책으로 허브 포트 이동

## 핵심 교훈

1. **Jetson aarch64**: manylinux 버전 호환성 확인 필수 (`2_35` vs `2_39`)
2. **SSH + GUI**: 원격 접속 시 `DISPLAY=:0` 설정으로 로컬 모니터 출력
3. **Qt 의존성**: `libxcb-cursor0` 등 시스템 라이브러리 사전 설치 필요

## 최종 상태

✅ SSH 원격 접속에서 `uv run python main.py` 실행 시 Jetson HDMI 모니터에 GUI 정상 표시
✅ C++ 하드웨어 타이머 모듈과 PySide6 GUI 완벽 연동
✅ 800x600 창에서 실시간 프레임 카운터 동작

### 파이썬이 코드를 찾는 법

보통 세 군데에서 찾는다.

- 지금 실행한 파일이 있는 폴더
- 현재 폴더(작업 디렉토리)
- 설치 된 패키지들(site-packages)

'editable 설치'는 site-packages에 링크를 만들어서 내 소스 폴더를 가리키게 함. 따라서 코드를 수정하면 재설치 없이도 바로 반영 됨.

### `uv run` vs editable install

자, `uv run`을 사용하면, `editable install` 없이 사용할 수 있으며 간단하고 직관적이다. 단, `uv`없이 `python` 명령만으로 실행할수는 없다.

반면 `editable install`을 사용하면, `uv run` 없이 `python` 명령만으로 실행할 수 있다.

### uv를 사용하는 경우, python 만 실행하는 경우
uv를 사용하고 `pyproject.toml`을 사용하는 경우, `python app.py`와 같이 실행하는 대신 `uv run app.py`와 같이 실행한다. `uv`는 `PYTHONPATH`를 설정하거나 하는등의 일을 한다. 

### `uv run src/my_app.py` 실행시 작동하는 매커니즘
- `파일 경로로 실행할 때, 그 파일이 있는 디렉터리를 sys.path[0]에 자동으로 넣음`
- 파이썬 3.3+에서는 __init__.py가 없어도 네임스페이스 패키지(PEP 420)를 지원하므로, `import foo.bar`와 같이 읽을 수 있다.
- 단, `init`반드시 필요한 경우는, 외부로 export 할 때나, `uv run -m` 옵션을 사용해서 실행할 때 등은 필요하다.
- 최소한의 안정성으로는 루트의 `__init__.py`를 만들어 두면 좋다.

### `pyproject.toml`

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["*"]
```
이 설정은 배포하지 않는 경우는 필요가 없다.

### `__init__.py` vs `__main__.py`

- `__init__.py`는 패키지를 초기화하는 파일. 패키지를 import할 때 실행되는 파일
  - 공개 api 재노출
- `__main__.py`는 패키지를 실행하는 파일
  - `python -m <package_name>` 은 `__main__.py` 파일을 실행 하는 것이다. 일반 파이썬파일 (`.py`)와 구분하기 위해 `-m` 옵션을 사용한다.

### 결론

- 가능한 `__init__.py`를 만드는 대신 `uv`를 사용한다.
- `__init__.py`는 모듈 초기화나 `__all__` 정의를 위해 사용한다.

### Python 프로젝트 패키지 구조

파이썬에서 디렉토리가 분리 되어 있는 경우는
