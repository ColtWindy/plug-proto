#coding=utf-8
import sys
import os
import queue
import threading

from pathlib import Path
import numpy as np
import cv2
from _lib import mvsdk
from _lib.wayland_utils import setup_wayland_environment
from ultralytics import YOLO
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, 
                                QPushButton, QHBoxLayout, QSizePolicy, QComboBox, QSlider, 
                                QCheckBox, QGroupBox, QGridLayout)
from PySide6.QtCore import QTimer, Qt, Signal, QObject
from PySide6.QtGui import QImage, QPixmap
from config import CAMERA_IP
import time

# Wayland 환경 설정
wayland_display, xdg_runtime_dir = setup_wayland_environment()

if not wayland_display:
    print("❌ 사용 가능한 Wayland 디스플레이를 찾을 수 없습니다")
    sys.exit(1)
else:
    print(f"✅ Wayland 디스플레이: {wayland_display}")

socket_path = os.path.join(xdg_runtime_dir, wayland_display)
if not os.path.exists(socket_path):
    print(f"❌ Wayland 소켓이 존재하지 않습니다: {socket_path}")
    sys.exit(1)
else:
    print(f"✅ Wayland 소켓 확인: {socket_path}")

# 카메라 설정 정보
TARGET_CAMERA_IP = CAMERA_IP


class CameraSignals(QObject):
    """카메라 프레임 시그널"""
    frame_ready = Signal(np.ndarray)  # 카메라 프레임 (BGR)


class InferenceWorker:
    """비동기 YOLO 추론 워커"""
    def __init__(self, model):
        self.model = model
        self.running = False
        self.thread = None
        self.input_queue = queue.Queue(maxsize=2)  # 최대 2개 프레임 버퍼
        self.output_queue = queue.Queue(maxsize=2)
        
    def start(self):
        """워커 시작"""
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """워커 종료"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def submit(self, frame_bgr):
        """추론 요청 (넘치면 드롭)"""
        try:
            self.input_queue.put_nowait(frame_bgr)
        except queue.Full:
            pass  # 프레임 드롭
    
    def get_result(self):
        """추론 결과 가져오기 (non-blocking)"""
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None
    
    def _worker_loop(self):
        """워커 루프 (별도 스레드)"""
        while self.running:
            try:
                frame_bgr = self.input_queue.get(timeout=0.1)
                
                # YOLO 추론
                start_time = time.time()
                results = self.model(frame_bgr, verbose=False)
                infer_time = (time.time() - start_time) * 1000
                
                # 결과를 프레임에 그리기
                annotated_frame = results[0].plot()
                detected_count = len(results[0].boxes)
                
                # 결과 큐에 넣기 (넘치면 드롭)
                try:
                    self.output_queue.put_nowait((annotated_frame, infer_time, detected_count))
                except queue.Full:
                    pass
            except queue.Empty:
                continue


class YOLOCameraWindow(QMainWindow):
    """YOLO 카메라 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO Inference - MindVision Camera")
        self.setGeometry(100, 100, 1280, 720)
        
        # 카메라 변수
        self.hCamera = None
        self.pFrameBuffer = None
        self.camera_capability = None
        self.frame_count = 0
        self.is_running = False
        
        # 노출 시간 범위
        self.exposure_min = 0
        self.exposure_max_hw = 0
        
        # FPS 계산용
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.current_fps = 0.0
        
        # 스케일 캐시 (성능 최적화)
        self._scaled_cache = None
        self._cache_key = None  # (width, height, image_id)
        
        # 카메라 시그널
        self.camera_signals = CameraSignals()
        self.camera_signals.frame_ready.connect(self.on_camera_frame)
        
        # 추론 워커
        self.inference_worker = None
        self.last_infer_time = 0.0
        self.infer_times = []  # 추론 시간 기록 (평균 계산용)
        self.avg_infer_time = 0.0
        
        # 카메라 콜백
        self.camera_callback = None
        
        # 트리거 제어
        self.trigger_thread = None
        self.trigger_running = False
        self.target_fps = 30  # 기본 FPS
        
        # 이미지 정보
        self.frame_width = 0
        self.frame_height = 0

        # UI 초기화
        self.init_ui()
        
        # 타이머 설정 (UI 업데이트용)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        
        # 카메라 및 YOLO 초기화
        self.init_camera()
        self.init_yolo()
        
    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # 왼쪽: 비디오 영역
        video_layout = QVBoxLayout()
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_layout.addWidget(self.video_label, stretch=1)
        
        self.status_label = QLabel("초기화 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        video_layout.addWidget(self.status_label)
        
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("시작")
        self.start_button.clicked.connect(self.start_capture)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("중지")
        self.stop_button.clicked.connect(self.stop_capture)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        self.quit_button = QPushButton("종료")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.quit_button)
        
        video_layout.addLayout(button_layout)
        main_layout.addLayout(video_layout, stretch=3)
        
        # 오른쪽: 카메라 컨트롤 패널
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, stretch=1)
        
        central_widget.setLayout(main_layout)
    
    def create_control_panel(self):
        """카메라 컨트롤 패널 생성"""
        control_group = QGroupBox("설정")
        layout = QGridLayout()
        
        row = 0
        
        # 모델 선택
        layout.addWidget(QLabel("모델:"), row, 0)
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_combo, row, 1)
        row += 1
        
        # 카메라 해상도 선택
        layout.addWidget(QLabel("카메라 해상도:"), row, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.currentIndexChanged.connect(self.on_resolution_changed)
        self.resolution_combo.setEnabled(False)
        layout.addWidget(self.resolution_combo, row, 1)
        row += 1
        
        # FPS 설정
        layout.addWidget(QLabel("타겟 FPS:"), row, 0)
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setMinimum(15)
        self.fps_slider.setMaximum(60)
        self.fps_slider.setValue(30)
        self.fps_slider.valueChanged.connect(self.on_fps_changed)
        self.fps_slider.setEnabled(False)
        layout.addWidget(self.fps_slider, row, 1)
        row += 1
        
        self.fps_label = QLabel("30 FPS")
        self.fps_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.fps_label, row, 0, 1, 2)
        row += 1
        
        # 노출 시간 (수동)
        layout.addWidget(QLabel("노출 시간 (ms):"), row, 0)
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.valueChanged.connect(self.on_exposure_changed)
        self.exposure_slider.setEnabled(False)
        layout.addWidget(self.exposure_slider, row, 1)
        row += 1
        
        self.exposure_label = QLabel("0 ms")
        self.exposure_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.exposure_label, row, 0, 1, 2)
        row += 1
        
        # 게인
        layout.addWidget(QLabel("게인:"), row, 0)
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.valueChanged.connect(self.on_gain_changed)
        self.gain_slider.setEnabled(False)
        layout.addWidget(self.gain_slider, row, 1)
        row += 1
        
        self.gain_label = QLabel("0")
        self.gain_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.gain_label, row, 0, 1, 2)
        row += 1
        
        layout.setRowStretch(row, 1)
        control_group.setLayout(layout)
        control_group.setMaximumWidth(300)
        
        return control_group
    
    def init_camera(self):
        """카메라 초기화"""
        try:
            # SDK 및 카메라 초기화
            mvsdk.CameraSdkInit(1)
            camera_list = mvsdk.CameraEnumerateDevice()
            
            if len(camera_list) == 0:
                raise Exception("카메라를 찾을 수 없습니다.")
            
            target_camera = camera_list[0]
            self.hCamera = mvsdk.CameraInit(target_camera, -1, -1)
            print(f"✅ 카메라: {target_camera.GetFriendlyName()}")
            
            # 카메라 정보 가져오기
            self.camera_capability = mvsdk.CameraGetCapability(self.hCamera)
            
            # 카메라 설정
            mvsdk.CameraSetWbMode(self.hCamera, True)
            
            # 프레임 버퍼 할당
            FrameBufferSize = self.camera_capability.sResolutionRange.iWidthMax * self.camera_capability.sResolutionRange.iHeightMax * 3
            self.pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)
            
            # 수동 트리거 모드
            mvsdk.CameraSetTriggerMode(self.hCamera, 1)
            
            # 카메라 콜백 등록 (프레임 자동 수신)
            self.camera_callback = mvsdk.CAMERA_SNAP_PROC(self._camera_callback)
            mvsdk.CameraSetCallbackFunction(self.hCamera, self.camera_callback, 0)
            
            # 카메라 재생 시작
            mvsdk.CameraPlay(self.hCamera)
            print("✅ 콜백 모드 + 수동 트리거")
            
            # UI 컨트롤 초기화
            self.init_camera_controls()
            
            self.status_label.setText("카메라 준비 완료 - 시작 버튼을 클릭하세요")
            
        except Exception as e:
            print(f"❌ 카메라 초기화 실패: {e}")
            self.status_label.setText(f"카메라 초기화 실패: {e}")
            self.start_button.setEnabled(False)
    
    def init_camera_controls(self):
        """카메라 컨트롤 UI 초기화"""
        if self.hCamera is None or self.camera_capability is None:
            return
        
        try:
            # 해상도 목록 가져오기
            preset_sizes = mvsdk.CameraGetImageResolution(self.hCamera)
            self.resolution_combo.clear()
            
            # capability에서 미리 설정된 해상도 목록 가져오기
            resolution_count = self.camera_capability.iImageSizeDesc
            current_index = 0
            
            for i in range(resolution_count):
                desc = self.camera_capability.pImageSizeDesc[i]
                desc_text = desc.GetDescription()
                resolution_text = f"{desc_text} ({desc.iWidth}x{desc.iHeight})"
                self.resolution_combo.addItem(resolution_text, desc)
                if desc.iWidth == preset_sizes.iWidth and desc.iHeight == preset_sizes.iHeight:
                    current_index = i
            
            self.resolution_combo.setCurrentIndex(current_index)
            self.resolution_combo.setEnabled(True)
            
            # 노출 범위 설정
            exp_range = self.camera_capability.sExposeDesc
            self.exposure_min = exp_range.uiExposeTimeMin
            self.exposure_max_hw = exp_range.uiExposeTimeMax
            
            # FPS에 따른 노출 시간 계산 (수동 모드, ms 단위)
            target_fps = self.fps_slider.value()
            max_exposure_ms = int(1000 / target_fps * 0.8)  # 80% 여유 (ms)
            
            # 슬라이더 설정 (ms 단위)
            self.exposure_slider.setMinimum(1)  # 최소 1ms
            self.exposure_slider.setMaximum(max_exposure_ms)
            self.exposure_slider.setValue(max_exposure_ms // 2)  # 절반 값으로 시작
            self.exposure_label.setText(f"{max_exposure_ms // 2} ms")
            
            # 수동 노출 모드 설정
            mvsdk.CameraSetAeState(self.hCamera, False)
            initial_exposure_us = (max_exposure_ms // 2) * 1000
            mvsdk.CameraSetExposureTime(self.hCamera, float(initial_exposure_us))
            print(f"✅ 수동 노출: {max_exposure_ms // 2}ms")
            
            # 게인 슬라이더 설정
            gain_range = self.camera_capability.sRgbGainRange
            self.gain_slider.setMinimum(gain_range.iRGainMin)
            self.gain_slider.setMaximum(gain_range.iRGainMax)
            r_gain, g_gain, b_gain = mvsdk.CameraGetGain(self.hCamera)
            self.gain_slider.setValue(r_gain)
            self.gain_label.setText(f"{r_gain}")
            
            # 컨트롤 활성화
            self.fps_slider.setEnabled(True)
            self.exposure_slider.setEnabled(True)
            self.gain_slider.setEnabled(True)
            
        except Exception as e:
            print(f"❌ 컨트롤 초기화 실패: {e}")
    
    def on_model_changed(self, index):
        """모델 변경"""
        if index < 0:
            return
        
        model_path = self.model_combo.itemData(index)
        if model_path:
            self.model = YOLO(model_path)
            print(f"✅ 모델: {Path(model_path).name}")
    
    def on_resolution_changed(self, index):
        """카메라 해상도 변경"""
        if self.hCamera is None or self.is_running:
            return
        
        resolution = self.resolution_combo.itemData(index)
        if resolution:
            mvsdk.CameraStop(self.hCamera)
            mvsdk.CameraSetImageResolution(self.hCamera, resolution)
            mvsdk.CameraPlay(self.hCamera)
            
            self.frame_width = 0
            self.frame_height = 0
            print(f"✅ 해상도: {resolution.iWidth}x{resolution.iHeight}")
    
    def on_fps_changed(self, fps):
        """FPS 변경"""
        if self.hCamera is None:
            return
        
        self.fps_label.setText(f"{fps} FPS")
        self.target_fps = fps
        
        # FPS에 따른 최대 노출 계산 (ms)
        max_exposure_ms = int(1000 / fps * 0.8)
        self.exposure_slider.setMaximum(max_exposure_ms)
        
        if self.exposure_slider.value() > max_exposure_ms:
            self.exposure_slider.setValue(max_exposure_ms)
    
    def on_exposure_changed(self, value_ms):
        """노출 시간 변경 (ms → μs)"""
        if self.hCamera is None:
            return
        
        # 노출 시간이 FPS 간격보다 길면 경고
        fps_interval_ms = 1000 / self.target_fps
        if value_ms > fps_interval_ms * 0.8:
            self.exposure_label.setText(f"{value_ms} ms ⚠️")
            self.exposure_label.setStyleSheet("color: red;")
        else:
            self.exposure_label.setText(f"{value_ms} ms")
            self.exposure_label.setStyleSheet("")
        
        exposure_us = value_ms * 1000
        mvsdk.CameraSetExposureTime(self.hCamera, float(exposure_us))
    
    def on_gain_changed(self, value):
        """게인 변경"""
        if self.hCamera is None:
            return
        
        mvsdk.CameraSetGain(self.hCamera, value, value, value)
        self.gain_label.setText(f"{value}")
    
    def init_yolo(self):
        """YOLO 모델 초기화"""
        try:
            models_dir = Path(__file__).parent / "models"
            engine_files = sorted(models_dir.glob("*.engine"))
            
            if not engine_files:
                self.status_label.setText("모델 파일(.engine)을 찾을 수 없습니다")
                self.start_button.setEnabled(False)
                return
            
            for model_file in engine_files:
                self.model_combo.addItem(model_file.name, str(model_file))
            
            # 첫 번째 모델 로드
            first_model = str(engine_files[0])
            self.model = YOLO(first_model)
            print(f"✅ 모델: {engine_files[0].name}")
            
        except Exception as e:
            print(f"❌ 모델 로드 실패: {e}")
            self.status_label.setText(f"모델 로드 실패: {e}")
            self.start_button.setEnabled(False)
    
    def _camera_callback(self, hCamera, pRawData, pFrameHead, pContext):
        """카메라 프레임 콜백 (SDK 스레드에서 호출 - 빠르게 처리)"""
        if not self.is_running:
            return
        
        try:
            # 이미지 변환 (최소한의 처리만)
            mvsdk.CameraImageProcess(hCamera, pRawData, self.pFrameBuffer, pFrameHead.contents)
            
            # numpy 배열로 변환
            frame_head = pFrameHead.contents
            frame_data = (mvsdk.c_ubyte * frame_head.uBytes).from_address(self.pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8).copy()  # 복사본 생성
            frame = frame.reshape((frame_head.iHeight, frame_head.iWidth, 3))
            
            # BGR로 변환 후 즉시 시그널 발생 (콜백 블로킹 최소화)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.camera_signals.frame_ready.emit(frame_bgr)
            
        except Exception as e:
            print(f"⚠️ 콜백 오류: {e}")
    
    def _trigger_loop(self):
        """트리거 루프 (FPS 제어)"""
        next_trigger_time = time.perf_counter()
        
        while self.trigger_running and self.hCamera:
            try:
                current_time = time.perf_counter()
                trigger_interval = 1.0 / self.target_fps  # 매번 계산 (실시간 반영)
                
                # 트리거 시간이 되었으면 발생
                if current_time >= next_trigger_time:
                    mvsdk.CameraSoftTrigger(self.hCamera)
                    next_trigger_time = current_time + trigger_interval
                
                # 짧은 sleep (CPU 절약)
                time.sleep(0.0001)
                    
            except Exception as e:
                print(f"⚠️ 트리거 오류: {e}")
                break
    
    def on_camera_frame(self, frame_bgr):
        """카메라 프레임 콜백 (메인 스레드)"""
        if not self.is_running or self.inference_worker is None:
            return
        
        # 프레임 크기 저장
        if self.frame_width == 0 or self.frame_height == 0:
            self.frame_height, self.frame_width = frame_bgr.shape[:2]
        
        # FPS 계산
        self.fps_frame_count += 1
        elapsed_time = time.time() - self.fps_start_time
        if elapsed_time >= 1.0:
            self.current_fps = self.fps_frame_count / elapsed_time
            self.fps_start_time = time.time()
            self.fps_frame_count = 0
        
        # 추론 워커에 제출
        self.inference_worker.submit(frame_bgr)
    
    def update_display(self):
        """디스플레이 업데이트 (추론 결과 반영)"""
        if not self.is_running:
            return
        
        # 추론 결과 가져오기
        result = self.inference_worker.get_result()
        if result is None:
            return
        
        annotated_frame, infer_time, detected_count = result
        self.last_infer_time = infer_time
        
        # 평균 추론 시간 계산 (최근 30개 평균)
        self.infer_times.append(infer_time)
        if len(self.infer_times) > 30:
            self.infer_times.pop(0)
        self.avg_infer_time = sum(self.infer_times) / len(self.infer_times)
        
        # BGR을 RGB로 변환
        annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        
        # QImage로 변환
        height, width, channel = annotated_frame_rgb.shape
        bytes_per_line = 3 * width
        q_image = QImage(annotated_frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()
        
        # QPixmap으로 변환 및 캐시 사용
        pixmap = QPixmap.fromImage(q_image)
        label_size = self.video_label.size()
        cache_key = (label_size.width(), label_size.height(), pixmap.cacheKey())
        
        if cache_key != self._cache_key:
            self._scaled_cache = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.FastTransformation)
            self._cache_key = cache_key
        
        self.video_label.setPixmap(self._scaled_cache)
        
        # 상태 업데이트
        status_text = f"FPS: {self.current_fps:.1f} | 추론: {self.last_infer_time:.1f}ms (평균: {self.avg_infer_time:.1f}ms) | 탐지: {detected_count}"
        
        # 카메라 해상도 추가
        if self.frame_width > 0 and self.frame_height > 0:
            status_text += f" | 해상도: {self.frame_width}x{self.frame_height}"
        
        self.status_label.setText(status_text)
    
    def start_capture(self):
        """캡처 시작"""
        if self.hCamera is None or self.model is None:
            self.status_label.setText("카메라 또는 모델이 초기화되지 않았습니다")
            return
        
        self.is_running = True
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self._scaled_cache = None
        self.frame_width = 0
        self.frame_height = 0
        self.infer_times = []
        self.avg_infer_time = 0.0
        
        # 추론 워커 시작
        self.inference_worker = InferenceWorker(self.model)
        self.inference_worker.start()
        
        # 트리거 스레드 시작 (FPS 제어)
        self.trigger_running = True
        self.trigger_thread = threading.Thread(target=self._trigger_loop, daemon=True)
        self.trigger_thread.start()
        
        # UI 업데이트 타이머 시작 (60 FPS로 빠르게)
        self.update_timer.start(16)
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.model_combo.setEnabled(False)
        self.resolution_combo.setEnabled(False)
        self.status_label.setText("실시간 객체 탐지 중...")
        
        print(f"\n🎬 시작 (타겟 FPS: {self.target_fps})")
    
    def stop_capture(self):
        """캡처 중지"""
        self.is_running = False
        self.trigger_running = False
        
        self.update_timer.stop()
        
        if self.inference_worker:
            self.inference_worker.stop()
            self.inference_worker = None
        
        if self.trigger_thread:
            self.trigger_thread.join(timeout=1.0)
            self.trigger_thread = None
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.model_combo.setEnabled(True)
        self.resolution_combo.setEnabled(True)
        self.status_label.setText("중지됨")
    
    
    def resizeEvent(self, event):
        """윈도우 크기 변경 시 캐시 초기화"""
        super().resizeEvent(event)
        self._scaled_cache = None
        self._cache_key = None
    
    def closeEvent(self, event):
        """윈도우 종료"""
        if self.is_running:
            self.stop_capture()
        
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        if self.hCamera is not None:
            if self.pFrameBuffer is not None:
                mvsdk.CameraAlignFree(self.pFrameBuffer)
            mvsdk.CameraUnInit(self.hCamera)
        
        event.accept()


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # Wayland 플랫폼 플러그인 사용 (자동으로 선택됨)
    print(f"📱 Qt 플랫폼: {app.platformName()}")
    
    window = YOLOCameraWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


