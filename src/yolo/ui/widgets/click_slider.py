#coding=utf-8
"""
클릭 시 즉시 이동하는 슬라이더
"""
from PySide6.QtWidgets import QSlider, QStyle
from PySide6.QtCore import Qt


class ClickSlider(QSlider):
    """클릭한 위치로 즉시 이동하는 슬라이더"""
    
    def mousePressEvent(self, event):
        """마우스 클릭 시 해당 위치로 즉시 이동"""
        if event.button() == Qt.LeftButton:
            # 클릭 위치 계산
            if self.orientation() == Qt.Horizontal:
                value = QStyle.sliderValueFromPosition(
                    self.minimum(), self.maximum(),
                    event.pos().x(), self.width()
                )
            else:
                value = QStyle.sliderValueFromPosition(
                    self.minimum(), self.maximum(),
                    event.pos().y(), self.height()
                )
            
            self.setValue(value)
            event.accept()
        
        super().mousePressEvent(event)

