#coding=utf-8
import sys
import os

from pathlib import Path
import numpy as np
import cv2
from _lib import mvsdk
from _lib.wayland_utils import setup_wayland_environment
from ultralytics import YOLO
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, 
                                QPushButton, QHBoxLayout, QSizePolicy, QComboBox, QSlider, 
                                QCheckBox, QGroupBox, QGridLayout)
from PySide6.QtCore import QTimer, Qt
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

        # UI 초기화
        self.init_ui()
        
        # 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
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
        
        # 최대 노출 시간
        layout.addWidget(QLabel("최대 노출 (μs):"), row, 0)
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.valueChanged.connect(self.on_max_exposure_changed)
        self.exposure_slider.setEnabled(False)
        layout.addWidget(self.exposure_slider, row, 1)
        row += 1
        
        self.exposure_label = QLabel("0")
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
            # SDK 초기화
            print("🔧 카메라 SDK 초기화 중...")
            mvsdk.CameraSdkInit(1)  # 1 = English
            
            # 카메라 검색
            print(f"🔍 카메라 검색 중... (설정 IP: {TARGET_CAMERA_IP})")
            camera_list = mvsdk.CameraEnumerateDevice()
            
            if len(camera_list) == 0:
                raise Exception("카메라를 찾을 수 없습니다.")
            
            # 첫 번째 카메라 사용
            target_camera = camera_list[0]
            print(f"✅ 카메라 발견: {target_camera.GetFriendlyName()}")
            
            # 카메라 초기화
            print("🔧 카메라 초기화 중...")
            self.hCamera = mvsdk.CameraInit(target_camera, -1, -1)
            print("✅ 카메라 초기화 성공")
            
            # 카메라 정보 가져오기
            self.camera_capability = mvsdk.CameraGetCapability(self.hCamera)
            
            # 자동 화이트밸런스 활성화 (기본값)
            mvsdk.CameraSetWbMode(self.hCamera, True)
            
            # 카메라 재생 시작
            mvsdk.CameraPlay(self.hCamera)
            print("✅ 카메라 재생 시작")
            
            # 프레임 버퍼 할당
            FrameBufferSize = self.camera_capability.sResolutionRange.iWidthMax * self.camera_capability.sResolutionRange.iHeightMax * 3
            self.pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)
            
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
            # 노출 범위 설정
            exp_range = self.camera_capability.sExposeDesc
            self.exposure_min = exp_range.uiExposeTimeMin
            self.exposure_max_hw = exp_range.uiExposeTimeMax
            
            # 최대 노출 슬라이더 설정
            self.exposure_slider.setMinimum(self.exposure_min)
            self.exposure_slider.setMaximum(self.exposure_max_hw)
            
            # FPS에 따른 최대 노출 설정 (30 FPS 기본)
            target_fps = 30
            max_exposure_for_fps = int(1000000 / target_fps * 0.9)
            initial_max_exposure = min(max_exposure_for_fps, self.exposure_max_hw)
            self.exposure_slider.setValue(initial_max_exposure)
            self.exposure_label.setText(f"{initial_max_exposure}")
            
            # 자동 노출 켜기 (기본값)
            mvsdk.CameraSetAeState(self.hCamera, True)
            mvsdk.CameraSetAeExposureRange(self.hCamera, self.exposure_min, initial_max_exposure)
            
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
            
            print("✅ 카메라 컨트롤 UI 초기화 완료")
            
        except Exception as e:
            print(f"⚠️ 카메라 컨트롤 초기화 실패: {e}")
    
    def on_model_changed(self, index):
        """모델 변경 이벤트"""
        if index < 0:
            return
        
        try:
            model_path = self.model_combo.itemData(index)
            if model_path:
                print(f"🔧 모델 로드 중: {model_path}")
                self.model = YOLO(model_path)
                print(f"✅ 모델 변경 완료: {Path(model_path).name}")
        except Exception as e:
            print(f"❌ 모델 변경 실패: {e}")
    
    def on_fps_changed(self, fps):
        """FPS 변경 이벤트 (실시간 적용)"""
        if self.hCamera is None:
            return
        
        try:
            self.fps_label.setText(f"{fps} FPS")
            
            # FPS에 따른 최대 노출 계산 및 제안
            max_exposure_for_fps = int(1000000 / fps * 0.9)
            suggested_max = min(max_exposure_for_fps, self.exposure_max_hw)
            
            # 현재 최대 노출이 FPS에 맞지 않으면 자동 조정
            current_max = self.exposure_slider.value()
            if current_max > max_exposure_for_fps:
                self.exposure_slider.setValue(suggested_max)
                mvsdk.CameraSetAeExposureRange(self.hCamera, self.exposure_min, suggested_max)
                print(f"✅ 타겟 FPS: {fps}, 최대 노출 자동 조정: {suggested_max} μs")
            else:
                print(f"✅ 타겟 FPS: {fps}")
        except Exception as e:
            print(f"❌ FPS 변경 실패: {e}")
    
    def on_max_exposure_changed(self, value):
        """최대 노출 시간 변경 이벤트"""
        if self.hCamera is None:
            return
        
        try:
            self.exposure_label.setText(f"{value}")
            mvsdk.CameraSetAeExposureRange(self.hCamera, self.exposure_min, value)
        except Exception as e:
            print(f"❌ 최대 노출 변경 실패: {e}")
    
    def on_gain_changed(self, value):
        """게인 변경 이벤트"""
        if self.hCamera is None:
            return
        
        try:
            mvsdk.CameraSetGain(self.hCamera, value, value, value)
            self.gain_label.setText(f"{value}")
        except Exception as e:
            print(f"❌ 게인 변경 실패: {e}")
    
    def init_yolo(self):
        """YOLO 모델 초기화"""
        try:
            print("🔧 YOLO 모델 검색 중...")
            script_dir = Path(__file__).parent
            models_dir = script_dir / "models"
            
            # .engine 파일 목록 가져오기
            engine_files = sorted(models_dir.glob("*.engine"))
            
            if not engine_files:
                print("⚠️ .engine 파일을 찾을 수 없습니다")
                self.status_label.setText("모델 파일(.engine)을 찾을 수 없습니다")
                self.start_button.setEnabled(False)
                return
            
            # 모델 목록을 콤보박스에 추가
            for model_file in engine_files:
                model_name = model_file.name
                self.model_combo.addItem(model_name, str(model_file))
            
            # 첫 번째 모델 로드
            first_model = str(engine_files[0])
            self.model = YOLO(first_model)
            print(f"✅ YOLO 모델 로드 완료: {engine_files[0].name}")
            
        except Exception as e:
            print(f"❌ YOLO 모델 로드 실패: {e}")
            self.status_label.setText(f"YOLO 모델 로드 실패: {e}")
            self.start_button.setEnabled(False)
    
    def start_capture(self):
        """캡처 시작"""
        if self.hCamera is None:
            self.status_label.setText("카메라가 초기화되지 않았습니다")
            return
        
        self.is_running = True
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.timer.start(30)  # 30ms 간격 (~33 FPS)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.model_combo.setEnabled(False)
        self.status_label.setText("실시간 객체 탐지 중...")
        print("\n🎬 실시간 객체 탐지 시작")
        print("=" * 50)
    
    def stop_capture(self):
        """캡처 중지"""
        self.is_running = False
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.model_combo.setEnabled(True)
        self.status_label.setText("중지됨 - 시작 버튼을 클릭하여 재시작")
        print("\n⏸️ 캡처 중지")
    
    def update_frame(self):
        """프레임 업데이트"""
        if not self.is_running or self.hCamera is None:
            return
        
        try:
            # 카메라에서 이미지 가져오기 (100ms 타임아웃)
            pRawData, FrameHead = mvsdk.CameraGetImageBuffer(self.hCamera, 100)
            
            # 이미지를 RGB 포맷으로 변환
            mvsdk.CameraImageProcess(self.hCamera, pRawData, self.pFrameBuffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(self.hCamera, pRawData)
            
            # numpy 배열로 변환
            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 3))
            
            # BGR로 변환 (YOLO 추론용)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # YOLO 추론 수행 (시간 측정)
            infer_start = time.time()
            results = self.model(frame_bgr, verbose=False)
            infer_time = (time.time() - infer_start) * 1000  # ms 단위
            
            # 결과를 프레임에 그리기
            annotated_frame = results[0].plot()
            
            # BGR을 RGB로 변환 (Qt 표시용)
            annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            
            # QImage로 변환
            height, width, channel = annotated_frame_rgb.shape
            bytes_per_line = 3 * width
            q_image = QImage(annotated_frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # QLabel에 표시
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.video_label.setPixmap(scaled_pixmap)
            
            # FPS 계산
            self.fps_frame_count += 1
            elapsed_time = time.time() - self.fps_start_time
            if elapsed_time >= 1.0:
                self.current_fps = self.fps_frame_count / elapsed_time
                self.fps_start_time = time.time()
                self.fps_frame_count = 0
            
            # 상태 업데이트
            detected_objects = len(results[0].boxes)
            self.status_label.setText(f"FPS: {self.current_fps:.1f} | 추론: {infer_time:.1f}ms | 탐지: {detected_objects}")
            
        except mvsdk.CameraException as e:
            if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
                print(f"⚠️ 카메라 오류: {e}")
                self.status_label.setText(f"카메라 오류: {e}")
        except Exception as e:
            print(f"⚠️ 프레임 처리 오류: {e}")
    
    def closeEvent(self, event):
        """윈도우 종료 이벤트"""
        print("\n🧹 리소스 정리 중...")
        
        # 타이머 중지
        if self.timer.isActive():
            self.timer.stop()
        
        # 카메라 정리
        if self.hCamera is not None:
            try:
                if self.pFrameBuffer is not None:
                    mvsdk.CameraAlignFree(self.pFrameBuffer)
                mvsdk.CameraUnInit(self.hCamera)
                print("✅ 카메라 정리 완료")
            except Exception as e:
                print(f"⚠️ 카메라 정리 중 오류: {e}")
        
        print("✅ 종료 완료")
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


