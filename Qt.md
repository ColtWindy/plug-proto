### 용어

- Zero-copy: 데이터 복사 없이 전송하는 기법, 카메라 프레임이 DMA-BUF로 전달되고 앱은 그 FD(File Descriptor)만 사용해서 처리.
  - `mmap()`: 지정한 파일 디스크립터(fd)로 부터 시작 위치(offset)에서 크기(length)만큼 영역을 현재 프로세스 주소 공간에 매핑, 이후 `munmap()`으로 해제.
  - `sendfile()`: 네트워크 전송시 사용, DMA복사와 CPU복사가 발생하지만, 오버헤드는 줄어듬
- BFO (Frame Buffer Object): OpenGL에서 오프스크린 렌더 타겟, 즉, FBO에 먼저 렌더하고 나중에 화면으로 컴포즈한다. `QOpenGLWidget`에서는 내부적으로 FBO -> 윈도우로 복사가 기본
- Wayland vs Weston
  - Wayland: 디스플레이 서버/클라이언트 프로토콜 (표준)
  - Weston: 구현체, 실제로는 GNOME/KDE등 다양한 컴포지터가 있고, 모두 Wayland 프로토콜을 따른다. 포인트는 앱이 직접 화면에 그리지 않고, 컴포지터가 앱들의 버퍼를 합성해 최종 프레임을 만든다는 것이다.

### QWidget 큰 창에서 프레임 드랍이 발생하는 매커니즘

1. QBackingStore(CPU 메모리)에 QPainter로 그림: 큰 창일수록 필셀 채우기/알파블렌딩 비용이 폭발
2. 완성된 이미지를 플랫폼 버퍼로 복사/전송(Wayland에선 보통 `wl_shm` 공유메모리, 혹은 내부 최적화)
3. 컴포지터가 합성 -> 디스플레이로 출력

여기서 드랍/스킵이 발생하는 주된 이유

- 픽셀 채우기 자치게 무겁다: 고해상도는 16.6ms 내에 끝내기 어렵다.
- 대용량 복사: 백킹스토어 -> 플랫폼 버퍼 복사 / 변환이 병목.
- 합성 타이밍 미스: 다음 VSync 전에 commit을 못하면 한 프레임을 건너뛴다(스킵).
- `QOpenGLWidget`을 써도 FBO -> 윈도우 블릿이 추가되어 큰 창에서 병목(특히 Wayland 합성과 겹치면 더욱)

### 다 못그려도 프레임 드랍이 없으려면

핵심은 Vsync에 맞춰 항상 무언가를 커밋하는 것. 내용이 덜 그려졌으면 이전 프레임을 재사용해도 된다.

아키텍쳐 원칙

- 프레임 페이싱을 표시기준으로
  - `QOpenGLWindow`/`QQuickWindow`의 `frameSwapped` 신호를 기준으로 다음 `update()`예약.
- 프로듀서(그리기/처리)와 프레젠테이션(표시) 분리
  - 그리기는 워커 쓰레드/비동기로 진행, 표시 쓰레드는 항상 제때 커밋
  - 표시 시점에 새 프레임이 준비 안됐으면 이전 프레임을 재사용
- Zero-copy 경로 채택
  - 비디오/카메라등 대용량은 DMA-BUF -> EGLIMage 텍스처로 바로쓰기
  - QWidget에서는 어렵고, `QOpenGLWidget`/`Qt Quick + 외부 텍스쳐`가 현실적
- Triple-buffer로 스톨 방지
  - 더블버퍼는 GPU가 막히면 앱 쓰레드가 swap에서 블록 -> 밀림
  - 트리플 버퍼는 1프레임 지연이 있지만, 좀 더 여유 있음

추천
- QOpenGLWindow로 전환: OpenGLWidget보다 Window가 더 나음.

### QTWidget
- `update()`: 이 함수는 즉시 repaint를 발생시키지 않음. 대신, 메인이벤트루프에 스케쥴 됨. 여러번의 `update()` 호출은 보통 한 번만의 `pinatEvent()`를 호출 함. 보통 QT는 위젯영역을 `paintEvent()`로 그리기 전에 영역을 삭제하지만, `Qt::WA_OpaquePaintEvent` 플래그가 있으면 불투명 컬러로 칠함. 

### `Qt::WA_PaintOnScreen`

- QWidget에 붙이는 오래된 플래그로, 백킹 스토어(더블버퍼)를 쓰지 말고 직접 화면에 그리겠다는 힌트를 주는 속성.
- 요즘, Wayland/Weston, Qt 5/6 등에서는 효과가 없거나 무시. Wayland에서는 모든 창이 합성되기 때문에 직접 화면에 직결해서 그리기 라는 개념 자체가 없음.
- 현대 Qt에서 직접 제어 렌더링이 필요하면, QOpenGLWindow, QOpenGLWidget 같은 전용 경로를 쓸 것.

QWidget 기반에서는 보통 백킹 스토어에 그려두고 노출/리사이즈시 그 버퍼를 합성함(깜빡임 방지). `setAttribute(Qt::WA_PaintOnScreen, true)`를 켜면 `paintEvent()`동안 바로 그린다는 의도를 표시

지금 무시되는 이유:

- Wayland: 모든 창은 컴포지터가 소유한 버퍼로 함성 됨. 앱이 "화면에 직접" 그릴 권한이 없음
- 현재 Qt(5/6): 백킹 스토어 + 합성이 기본, GPU 경로는 `QOpenGLWidget`이나 `QOpenGLWindow` 처렴 별도 파이프라인으로 제공 됨. 직접 그리기가 필요하면 전용 클래스를 사용하는게 정석
- 플랫폼별 제약: MacOS / Wayland / Windows 에서는 `WA_PaintOnScreen` 이 효과가 없거나 부분적으로만 동작함

### `QT::WA_OpaquePaintEvent`
- 위젯은 자신의 영역 전체를 불투명으로 칠한다는 의미, 투명합성이나 이주기를 건너뛸수 있어 메모리 복사 감소, 부하를 완화. 잔상이나 쓰레기가 남을 수 있어서, 전체를 채우는 경우만 사용

### QTimer
중요, 자신이 속한 스레드의 이벤트 루프에서 `timeout` 이벤트 발생, 워커 쓰레드에서 쓰려면 `moveToThread()` + 그 스레드에 `QEventLoop` 넣어야 함.

- `setSingleShot(True)`로 타이머 한번만 실행
- `timeout.connect()`으로 콜백 연결
- `timeout.disconnect()`으로 콜백 연결 해제
- `start(16)`으로 16ms마다 실행
- `isActive()`로 타이머 활성화 여부 확인
- `stop()`으로 타이머 중지
- `start()`으로 타이머 재시작

```python
QTimer.singleShot(250, self.on_once)  # 250ms 후 1회 호출
# 또는
t = QTimer(); t.setSingleShot(True)
t.timeout.connect(lambda: print("once")); t.start(250)
```


### 고성능 제어

- OpenGL(권장): QOpenGLWindow, QOpenGLWidget
- QtQuick
- 완전 수동 (버퍼 / 콜백 / 타이밍): Wayland 서브서피스 + 직접 attach / commit

### 프레임 드랍/스킵을 줄이고 싶다면 타이머 기반 루프 대신

- `QOpenGLWindow::frameSwapped`에서 다음 업데이트 예약,
- Wayland라면 `wl_surface::frame` 콜백 기준으로 페이싱하는게 가장 확실

#### 파이썬에서 추천하는 방법

- PySide6 + QOpenGLWindow: Wayland/Wetson에서도 잘 동작함. 스왑 동작/페이싱을 사용할 수 있음. 텍스쳐와 FBO를 직접 다루므로 실질적으로 내 버퍼를 제어하는 느낌
- paywayland로 작은 투명 1x1 매핑(이미 구현한 방법) `surface.frame()` 콜백을 받아서 `QtSignal`로 알림. 단, 진짜 버퍼 attach/commit은 Qt가 진행함
- Qt 없이 SHM / dmabuf 버퍼를 궅여 커밋. Qt UI와 합치기 어려움.

### IP 카메라의 Zero-copy
- zero-copy는 보통 디코딩 이후에 픽셀 데이터를 CPU로 복사하지 않고, 바로 GPU/디스플레이로 넘기는 뜻
- 하드웨어 디코더로 디코드 -> GPU 메모리 (NVMM/dmabuf)에 프레임 생성 -> 그 dmabuf FD(File Descriptor)를 EGLImage/GL 텍스쳐로 import > QT/Wayland에서 그 텍스쳐를 바로 그리기
- 보통은 디코드 이후만 zero-copy면 충분히 빠름

### 윈도우 블릿(blit)
- BLIT: Block Image Transfer의 줄임말. 한 버퍼의 픽셀을 다른 버퍼로 복사하는 것
- Qt에서, QOpenGLWidget 내부 FBO에서 그린 뒤, 윈도우 표면으로 blit(복사)함. 큰 창일수록 비용 증가
- 일반 QWidget도 백킹 스토어 -> 프레임 버퍼 복사단계가 사실상 블릿이라고 볼 수 있음

### `wl_shm`
- Wayland의 공유 메모리(shm) 버퍼 프로토콜. 클라이언트가 `tmpfile/memfd`로 공유 메모리를 만들고, 그걸 `wl_shm_pool` -> `wl_buffer`로 등록해서 CPU가 직접 필셀을 써서 화면을 보이게 한다.
- 특징으로는 CPU경로라서, 고해상도/고프레임에선 CPU페인트 + 대용량 복사가 병목이 됨
- zero-copy가 아님
- 간단한 위젯등 작은 그리기, 대용량은 `wl_shm`대신 `linux-dmabuf` + EGL 경로가 권장 됨(zero-copy에 가까움)
