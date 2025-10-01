# Wayland Presentation 프로토콜 통합

## 개요

Qt OpenGL 윈도우에서 `wp_presentation` 프로토콜을 사용하여 정확한 프레임 표시 추적을 구현합니다.

## 아키텍처

### 문제점
- PySide6에서 Qt가 사용하는 `wl_surface*` 포인터에 직접 접근 불가
- `platformNativeInterface()`가 Wayland 네이티브 리소스를 제공하지 않음
- pywayland로 별도 surface를 생성하면 Qt 윈도우와 무관한 데이터만 수집

### 해결책: C++ 헬퍼
```
┌─────────────────────────────────────────┐
│  Python (opengl_camera.py)              │
│  ┌─────────────────────────────────┐   │
│  │ PresentationMonitor             │   │
│  │  - C++ 모듈 호출                 │   │
│  │  - 콜백 처리                     │   │
│  └──────────┬──────────────────────┘   │
└─────────────┼───────────────────────────┘
              │ pybind11
┌─────────────▼───────────────────────────┐
│  C++ (wayland_presentation.cpp)         │
│  ┌─────────────────────────────────┐   │
│  │ WaylandPresentationMonitor      │   │
│  │  - Qt wl_surface* 접근           │   │
│  │  - wp_presentation 피드백        │   │
│  │  - 통계 수집                     │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## 구현 단계

### Phase 1: 기본 구조 (현재)
✅ C++ 모듈 뼈대 작성
- `WaylandPresentationMonitor` 클래스
- pybind11 바인딩
- Python 콜백 인터페이스

✅ 시뮬레이션 모드
- `simulate_presented()`: frameSwapped와 동기화
- 통계 수집 및 표시
- 플래그 파싱 (VSYNC, ZERO_COPY 등)

### Phase 2: Qt Native 리소스 접근 (TODO)
Qt의 실제 `wl_surface*` 포인터 획득:

```cpp
// Qt 6.x
#include <QtGui/qpa/qplatformnativeinterface.h>

void* get_qt_wl_surface(QWindow* window) {
    auto *pni = QGuiApplication::platformNativeInterface();
    return pni->nativeResourceForWindow("surface", window);
}
```

필요한 추가 작업:
- Qt 헤더 의존성 추가 (`Qt6::Gui`, `Qt6::WaylandClient`)
- CMake 또는 setup.py에 Qt 경로 설정

### Phase 3: 실제 wp_presentation 연동 (TODO)
libwayland-client를 통한 프로토콜 처리:

```cpp
// wp_presentation feedback 등록
auto *feedback = wp_presentation_feedback(wp_pres, wl_surf);
wp_presentation_feedback_add_listener(feedback, &listener, this);
```

필요한 추가 작업:
- `wayland-client` 라이브러리 링크
- `wayland-protocols` (presentation-time 프로토콜)
- 이벤트 루프 통합 (Qt 메인루프와 동기화)

## 현재 기능

### 제공하는 정보
1. **프레임 카운트**
   - `presented_count`: 표시된 프레임 수
   - `discarded_count`: 폐기된 프레임 수

2. **시퀀스 번호**
   - `last_sequence`: 마지막 표시 프레임의 시퀀스 (MSC)

3. **타임스탬프**
   - `last_timestamp_ns`: 실제 표시 시각 (나노초)

4. **플래그**
   - `vsync_synced_count`: VSync 동기화 프레임 수
   - `zero_copy_count`: Zero-copy 프레임 수

### 화면 표시 예시
```
Frame: 245 | 카메라화면 | GPU: 0 | Seq: 245 | P:245 D:0 | V:245 Z:0
```
- `Seq`: 시퀀스 번호
- `P/D`: Presented/Discarded 카운트
- `V/Z`: VSync/ZeroCopy 카운트

## 빌드 및 실행

### 1. C++ 모듈 빌드
```bash
chmod +x build_wayland.sh
./build_wayland.sh
```

또는 직접:
```bash
uv run python ./cpp/setup.py build_ext --build-lib lib
```

### 2. 실행
```bash
cd opengl_example
uv run python opengl_camera.py
```

### 3. 빌드 확인
```bash
ls -lh lib/wayland_presentation.*.so
```

## 제약사항

### 현재 구현 (시뮬레이션 모드)
- ⚠️ **Qt 윈도우와 직접 연동되지 않음**
- `frameSwapped` 시그널과 동기화하여 통계 생성
- 실제 compositor의 presented/discarded 이벤트를 받지 않음

### 완전한 구현을 위해 필요한 것
1. **Qt 헤더 통합**
   - PySide6 개발 헤더
   - Qt6WaylandClient 모듈

2. **Wayland 프로토콜 바인딩**
   - libwayland-client
   - wayland-protocols (presentation-time)

3. **이벤트 루프 통합**
   - Qt 이벤트 루프에서 Wayland 이벤트 처리
   - 또는 별도 스레드로 wl_display_dispatch

## 향후 개선

### 옵션 1: Qt 헤더 + libwayland 완전 통합
- 실제 Qt wl_surface 사용
- 실제 wp_presentation 피드백
- **장점**: 정확한 데이터
- **단점**: 복잡한 빌드 설정

### 옵션 2: QML/C++ 하이브리드
- QML로 Wayland 리소스 접근
- C++로 프로토콜 처리
- **장점**: Qt 통합 용이
- **단점**: QML 의존성

### 옵션 3: 현재 방식 개선
- frameSwapped + GPU fence 조합
- OpenGL sync 객체 활용
- **장점**: 의존성 최소
- **단점**: compositor 수준 정보 부재

## 참고 자료

- [Wayland Presentation Protocol](https://wayland.app/protocols/presentation-time)
- [Qt Platform Native Interface](https://doc.qt.io/qt-6/qguiapplication.html#platformNativeInterface)
- [PySide6 Native Resources](https://doc.qt.io/qtforpython-6/overviews/native-interfaces.html)

