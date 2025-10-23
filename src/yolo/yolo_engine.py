#coding=utf-8
"""
YOLO TensorRT 엔진 테스트
.engine 파일만 로드
"""
import sys
import os
from pathlib import Path
from _lib.wayland_utils import setup_wayland_environment
from PySide6.QtWidgets import QApplication
from ui.tensorrt_window import TensorRTWindow
from inference.model_manager import TensorRTModelManager


def main():
    """TensorRT 엔진 테스트"""
    # Wayland 환경 설정
    wayland_display, xdg_runtime_dir = setup_wayland_environment()
    if not wayland_display:
        print("❌ Wayland 디스플레이를 찾을 수 없습니다")
        sys.exit(1)
    
    socket_path = os.path.join(xdg_runtime_dir, wayland_display)
    if not os.path.exists(socket_path):
        print(f"❌ Wayland 소켓이 없습니다: {socket_path}")
        sys.exit(1)
    
    print(f"✅ Wayland: {wayland_display}")
    
    # Qt 애플리케이션
    app = QApplication(sys.argv)
    print(f"📱 Qt 플랫폼: {app.platformName()}")
    
    # TensorRT 모델 관리자
    models_dir = Path(__file__).parent / "models"
    model_manager = TensorRTModelManager(models_dir)
    
    # 모델 자동 로드
    model, model_list = model_manager.load_models()
    if model is None:
        sys.exit(1)
    
    # TensorRT 전용 윈도우 실행
    window = TensorRTWindow(model_manager)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


