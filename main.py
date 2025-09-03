#!/usr/bin/env python3
"""
PySide6 프레임 카운터 애플리케이션
하드웨어 타이머를 사용하여 성능 측정
"""

import sys
import os
import cv2
import numpy as np

# 젯슨 로컬 디스플레이 환경 설정 (SSH 접속 시)
os.environ['DISPLAY'] = ':0'

# Qt 로깅 경고 억제
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.plugin=false'

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QKeyEvent

# C++ 모듈 import
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
    import timer_module
    TIMER_AVAILABLE = True
    print("하드웨어 타이머 모듈 로드 완료")
except ImportError:
    TIMER_AVAILABLE = False
    print("하드웨어 타이머 모듈을 찾을 수 없습니다. Python 타이머를 사용합니다.")
    import time


class FrameCounterWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frame Counter")
        
        # 창 크기 설정
        self.setGeometry(100, 100, 800, 600)
        self.show()
        
        # 중앙 레이블
        self.label = QLabel()
        self.setCentralWidget(self.label)
        
        # 카메라 사용하지 않음 - 더미 프레임만 사용
        self.cap = None
        
        # 카운터 초기화
        self.frame_count = 0
        
        # 타이머 초기화
        if TIMER_AVAILABLE:
            self.start_time = timer_module.get_hardware_timer()
        else:
            self.start_time = time.time() * 1000000
        
        # Qt 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30ms마다 업데이트
    
    def update_frame(self):
        # 더미 프레임 생성
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        self.frame_count += 1
        
        # 타이머 계산
        if TIMER_AVAILABLE:
            current_time = timer_module.get_hardware_timer()
            elapsed_ms = timer_module.get_timer_diff_ms(self.start_time, current_time)
        else:
            current_time = time.time() * 1000000
            elapsed_ms = (current_time - self.start_time) / 1000.0
        
        fps = self.frame_count / (elapsed_ms / 1000.0) if elapsed_ms > 0 else 0
        
        # 텍스트 추가
        info_text = [
            f"Frame: {self.frame_count}",
            f"Time: {elapsed_ms:.1f}ms",
            f"FPS: {fps:.1f}",
            f"Timer: {'HW' if TIMER_AVAILABLE else 'SW'}"
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
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)
    
    def closeEvent(self, event):
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # 애플리케이션 속성 설정
    app.setApplicationName("Frame Counter")
    app.setApplicationVersion("1.0")
    
    window = FrameCounterWidget()
    
    # 창을 최상위로 올리기
    window.raise_()
    window.activateWindow()
    window.show()
    
    
    print(f"GUI 창이 표시되었습니다. 창 크기: {window.width()}x{window.height()}")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()



