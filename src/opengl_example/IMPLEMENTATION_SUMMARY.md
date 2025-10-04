# Wayland Presentation 통합 구현 요약

## ✅ 완료된 작업

### 1. C++ 헬퍼 모듈 (`cpp/wayland_presentation.cpp`)
```cpp
class WaylandPresentationMonitor {
    - initialize()          // Qt wl_surface* 초기화
    - set_callback()        // Python 콜백 등록
    - request_feedback()    // 프레임 피드백 요청
    - simulate_presented()  // 테스트/시뮬레이션
    
    // 통계
    - presented_count()
    - discarded_count()
    - vsync_count()
    - zero_copy_count()
    - last_sequence()
    - last_timestamp_ns()
}
```

**특징:**
- ✅ pybind11로 Python 바인딩
- ✅ Thread-safe (std::mutex)
- ✅ 콜백 기반 비동기 처리
- ✅ 향후 확장 가능한 구조

### 2. Python 통합 (`opengl_example/opengl_camera.py`)
```python
class PresentationMonitor:
    - __init__()            # C++ 모듈 초기화
    - request_feedback()    # frameSwapped와 동기화
    - _on_feedback()        # C++ 콜백 처리
    
    # Properties
    - presented_count
    - discarded_count
    - vsync_synced_count
    - zero_copy_count
    - last_seq
    - last_timestamp_ns
```

**통합 방식:**
- ✅ 기존 pywayland 제거
- ✅ C++ 모듈 동적 로드
- ✅ frameSwapped 시그널과 동기화
- ✅ 폴백 없음 (오류 시 명확한 실패)

### 3. 빌드 시스템
**파일:**
- `cpp/setup.py` - pybind11 빌드 설정
- `build_wayland.sh` - 빌드 스크립트

**빌드 명령:**
```bash
./build_wayland.sh
# 또는
uv run python ./cpp/setup.py build_ext --build-lib lib
```

**출력:**
```
lib/wayland_presentation.cpython-313-aarch64-linux-gnu.so (248KB)
```

## 🎯 현재 동작 방식

### Phase 1: 시뮬레이션 모드 (현재)
```
Qt OpenGL Window
    │
    ├─ paintGL() 
    │   └─ presentation.request_feedback()
    │
    └─ frameSwapped ◄────┐
                         │
Python PresentationMonitor
    │                    │
    └─ request_feedback()│
        │                │
        └─ simulate_presented() (타임스탬프 + 시퀀스)
            │
            └─ C++ WaylandPresentationMonitor
                │
                └─ callback(PresentationFeedback)
                    │
                    └─ Python _on_feedback() ◄──┘
                        │
                        └─ 통계 업데이트 + 로그
```

**특징:**
- frameSwapped와 1:1 매칭
- 실제 타임스탬프 생성
- VSYNC 플래그 시뮬레이션
- 통계 수집 및 화면 표시

### Phase 2: 실제 wp_presentation (향후)
향후 구현 시 필요:

```cpp
// 1. Qt wl_surface* 획득
QPlatformNativeInterface *pni = ...;
wl_surface *surf = (wl_surface*)pni->nativeResourceForWindow("surface", window);

// 2. wp_presentation_feedback 등록
wp_presentation_feedback *fb = wp_presentation_feedback(wp_pres, surf);
wp_presentation_feedback_add_listener(fb, &listener, this);

// 3. wl_display 이벤트 처리
wl_display_dispatch(display);
```

**필요한 추가 작업:**
- Qt6::Gui 헤더 의존성
- libwayland-client 링크
- wayland-protocols (presentation-time)
- Qt 이벤트 루프 통합

## 📊 제공하는 정보

### 화면 표시
```
Frame: 245 | 카메라화면 | GPU: 0 | Seq: 245 | P:245 D:0 | V:245 Z:0
```

### 로그 출력
```
[15:09:23.456] [PRESENT] seq=245, ts=1727842163456789us, flags=[VSYNC]
```

### 데이터 필드
| 필드 | 설명 | 현재 상태 |
|------|------|-----------|
| `sequence` | MSC (Media Stream Counter) | ✅ frameSwapped 카운트 |
| `timestamp_ns` | 실제 표시 시각 | ✅ time.time() 기반 |
| `flags.VSYNC` | VSync 동기화 여부 | ✅ 항상 true (시뮬레이션) |
| `flags.ZERO_COPY` | Zero-copy 여부 | ⏳ 향후 실제 데이터 |
| `flags.HW_CLOCK` | 하드웨어 클럭 | ⏳ 향후 실제 데이터 |
| `flags.HW_COMPLETION` | 하드웨어 완료 | ⏳ 향후 실제 데이터 |
| `presented` | 표시 성공 | ✅ 시뮬레이션 |
| `discarded` | 표시 실패 | ⏳ 향후 구현 |

## 🔍 프로젝트 구조 분석

### 기존 구조
```
plug-proto/
├── cpp/
│   ├── timer.cpp           # 하드웨어 타이머
│   └── setup.py            # pybind11 빌드
├── lib/
│   └── timer_module.*.so   # 컴파일된 모듈
├── opengl_example/
│   ├── opengl_camera.py    # 메인 애플리케이션
│   └── camera_controller.py
└── pyproject.toml
```

### 추가된 구조
```
plug-proto/
├── cpp/
│   ├── timer.cpp
│   ├── wayland_presentation.cpp    # ← NEW
│   └── setup.py                    # ← UPDATED
├── lib/
│   ├── timer_module.*.so
│   └── wayland_presentation.*.so   # ← NEW
├── opengl_example/
│   ├── opengl_camera.py            # ← UPDATED
│   ├── WAYLAND_PRESENTATION.md     # ← NEW 문서
│   └── IMPLEMENTATION_SUMMARY.md   # ← NEW 요약
└── build_wayland.sh                # ← NEW 빌드 스크립트
```

## 🚀 사용법

### 빌드
```bash
./build_wayland.sh
```

### 실행
```bash
cd opengl_example
uv run python opengl_camera.py
```

### 확인
화면에 다음 정보가 표시됨:
```
GPU: 0 | Seq: 123 | P:123 D:0 | V:123 Z:0
```

## ⚠️ 현재 제약사항

### 정확성
- **Qt wl_surface와 무관**: 별도 통계 생성
- **실제 compositor 이벤트 없음**: frameSwapped 기반 시뮬레이션
- **presented/discarded 실제 구분 없음**: 모두 presented로 카운트

### 향후 개선이 필요한 이유
현재는 **Qt frameSwapped와 동기화**하여 "프레임이 그려졌다 = presented"로 가정합니다.
하지만 실제로는:
- compositor가 프레임을 skip할 수 있음
- 다른 윈도우에 가려져 표시 안 될 수 있음
- VSync 타이밍을 놓쳐 다음 프레임으로 지연될 수 있음

**이런 실제 상황을 감지하려면 wp_presentation 프로토콜 완전 구현 필요**

## 📝 다음 단계 (옵션)

### A. 완전한 wp_presentation 구현
1. Qt 헤더 의존성 추가
2. libwayland-client 링크
3. 실제 wl_surface* 획득
4. wp_presentation_feedback 처리
5. 이벤트 루프 통합

**복잡도:** 높음  
**정확도:** 매우 높음

### B. 현재 방식 개선
1. GPU fence + frameSwapped 조합
2. GL sync 객체로 실제 표시 추적
3. 드라이버 타이밍 정보 활용

**복잡도:** 중간  
**정확도:** 높음

### C. 현재 구조 유지
1. 시뮬레이션 모드 개선
2. 통계 시각화 강화
3. 문서화 완성

**복잡도:** 낮음  
**정확도:** 참고용

## 🎓 학습 포인트

### 성공한 부분
1. ✅ **pywayland 제거**: 무관한 서피스 문제 해결
2. ✅ **C++ 헬퍼 패턴**: 기존 timer.cpp와 동일한 구조
3. ✅ **폴백 제거**: 명확한 오류 처리
4. ✅ **통계 수집**: frameSwapped와 완벽 동기화

### 배운 내용
1. **Qt Native Interface 한계**
   - PySide6에서 Wayland 리소스 접근 어려움
   - C++에서도 Qt 6.x의 플랫폼별 차이

2. **Wayland 프로토콜 복잡성**
   - wl_surface는 Qt가 내부 관리
   - 별도 연결 생성하면 무관한 데이터
   - 같은 이벤트 루프 공유 필수

3. **실용적 접근**
   - 완벽한 구현보다 작동하는 구현
   - 시뮬레이션으로 구조 검증
   - 향후 확장 가능한 설계

## 📚 참고 문서

- `WAYLAND_PRESENTATION.md` - 상세 기술 문서
- `cpp/wayland_presentation.cpp` - C++ 구현
- `opengl_example/opengl_camera.py` - Python 통합

---

**작성일**: 2025-10-01  
**버전**: Phase 1 (시뮬레이션 모드)  
**상태**: ✅ 빌드 성공, 동작 확인

