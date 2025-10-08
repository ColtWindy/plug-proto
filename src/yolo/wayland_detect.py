#coding=utf-8
import sys
import os

from pathlib import Path
import numpy as np
import cv2
from _lib import mvsdk
from _lib.wayland_utils import setup_wayland_environment
from ultralytics import YOLO
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from config import CAMERA_IP

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
        self.frame_count = 0
        self.is_running = False

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
        
        layout = QVBoxLayout()
        
        # 비디오 표시 라벨
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setMinimumSize(640, 480)
        layout.addWidget(self.video_label)
        
        # 상태 라벨
        self.status_label = QLabel("초기화 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 버튼 레이아웃
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
        
        layout.addLayout(button_layout)
        
        central_widget.setLayout(layout)
    
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
            cap = mvsdk.CameraGetCapability(self.hCamera)
            
            # 카메라를 자동 노출 모드로 설정
            print("🔧 자동 노출 모드 설정 중...")
            mvsdk.CameraSetAeState(self.hCamera, True)  # 자동 노출 활성화
            print("✅ 자동 노출 모드 활성화")
            
            # 자동 화이트밸런스 활성화
            mvsdk.CameraSetWbMode(self.hCamera, True)
            print("✅ 자동 화이트밸런스 활성화")
            
            # 카메라 재생 시작
            mvsdk.CameraPlay(self.hCamera)
            print("✅ 카메라 재생 시작")
            
            # 프레임 버퍼 할당
            FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * 3
            self.pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)
            
            self.status_label.setText("카메라 준비 완료 - 시작 버튼을 클릭하세요")
            
        except Exception as e:
            print(f"❌ 카메라 초기화 실패: {e}")
            self.status_label.setText(f"카메라 초기화 실패: {e}")
            self.start_button.setEnabled(False)
    
    def init_yolo(self):
        """YOLO 모델 초기화"""
        try:
            print("🔧 YOLO 모델 로드 중...")
            script_dir = Path(__file__).parent
            model_path = script_dir / "models/yolo8n_trash.pt"
            self.model = YOLO(model_path)
            print("✅ YOLO 모델 로드 완료")
        except Exception as e:
            print(f"❌ YOLO 모델 로드 실패: {e}")
            self.status_label.setText(f"YOLO 모델 로드 실패: {e}")
            self.start_button.setEnabled(False)
    
    def start_capture(self):
        """캡처 시작"""
        if self.hCamera is None:
            self.status_label.setText("카메가 초기화되지 않았습니다")
            return
        
        self.is_running = True
        self.timer.start(30)  # 30ms 간격 (~33 FPS)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("실시간 객체 탐지 중...")
        print("\n🎬 실시간 객체 탐지 시작")
        print("=" * 50)
    
    def stop_capture(self):
        """캡처 중지"""
        self.is_running = False
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
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
            
            # YOLO 추론 수행
            results = self.model(frame_bgr, verbose=False)
            
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
            
            # 프레임 카운터 업데이트
            self.frame_count += 1
            if self.frame_count % 30 == 0:
                detected_objects = len(results[0].boxes)
                self.status_label.setText(f"프레임: {self.frame_count} | 탐지된 객체: {detected_objects}")
                print(f"📊 프레임: {self.frame_count} | 탐지된 객체: {detected_objects}")
            
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


