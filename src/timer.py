#!/usr/bin/env python3
#coding=utf-8
"""
PySide6 프레임 카운터 애플리케이션
하드웨어 타이머를 사용하여 성능 측정
Wayland 환경 지원
"""

import sys
import os
import cv2
import numpy as np
from _lib.wayland_utils import setup_wayland_environment

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
    print(f"✅ Wayland 소켓: {socket_path}")

# Qt 로깅 경고 억제
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.plugin=false'

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QKeyEvent

# C++ 하드웨어 타이머 모듈 import (필수)
from _native.timer_module import get_hardware_timer, get_timer_diff_ms
print("✅ 하드웨어 타이머 모듈 로드 완료")


class FrameCounterWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frame Counter - Hardware Timer")
        
        # 창 크기 설정
        self.setGeometry(100, 100, 800, 600)
        self.show()
        
        # 중앙 레이블
        self.label = QLabel()
        self.setCentralWidget(self.label)
        
        # 카운터 초기화
        self.frame_count = 0
        
        # 하드웨어 타이머 초기화
        self.start_time = get_hardware_timer()
        
        # Qt 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30ms마다 업데이트
    
    def update_frame(self):
        """프레임 업데이트 및 타이머 표시"""
        # 더미 프레임 생성
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        self.frame_count += 1
        
        # 하드웨어 타이머 계산
        current_time = get_hardware_timer()
        elapsed_ms = get_timer_diff_ms(self.start_time, current_time)
        fps = self.frame_count / (elapsed_ms / 1000.0) if elapsed_ms > 0 else 0
        
        # 텍스트 추가
        info_text = [
            f"Frame: {self.frame_count}",
            f"Time: {elapsed_ms:.1f}ms",
            f"FPS: {fps:.1f}",
            f"Timer: Hardware"
        ]
        
        y_offset = 30
        for i, text in enumerate(info_text):
            cv2.putText(frame, text, (10, y_offset + i * 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 중앙에 프레임 번호 표시
        text = str(self.frame_count)
        font_scale = 3
        thickness = 3
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = (frame.shape[0] + text_size[1]) // 2
        cv2.putText(frame, text, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
        
        # OpenCV BGR을 Qt RGB로 변환
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # QLabel에 표시
        self.label.setPixmap(QPixmap.fromImage(qt_image))
    
    def keyPressEvent(self, event):
        """ESC 키로 종료"""
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """종료 처리"""
        event.accept()


def main():
    """애플리케이션 진입점"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 속성 설정
    app.setApplicationName("Frame Counter")
    app.setApplicationVersion("1.0")
    
    window = FrameCounterWidget()
    
    # 창을 최상위로 올리기
    window.raise_()
    window.activateWindow()
    window.show()
    
    print(f"🎬 GUI 창이 표시되었습니다. 창 크기: {window.width()}x{window.height()}")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

