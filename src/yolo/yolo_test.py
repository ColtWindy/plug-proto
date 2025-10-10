#coding=utf-8
"""
YOLO 카메라 애플리케이션 메인 진입점
"""
import sys
import os
from pathlib import Path
from _lib.wayland_utils import setup_wayland_environment
from PySide6.QtWidgets import QApplication
from ultralytics import YOLO
from ui.main_window import YOLOCameraWindow


def load_models():
    """YOLO 모델 로드"""
    models_dir = Path(__file__).parent / "models"
    engine_files = sorted(models_dir.glob("*.engine"))
    
    if not engine_files:
        print("❌ 모델 파일(.engine)을 찾을 수 없습니다")
        return None, []
    
    # 모델 목록 생성
    model_list = [(f.name, str(f)) for f in engine_files]
    
    # 첫 번째 모델 로드
    first_model_path = str(engine_files[0])
    model = YOLO(first_model_path)
    print(f"✅ 모델: {engine_files[0].name}")
    
    return model, model_list


def main():
    """메인 함수"""
    # Wayland 환경 설정
    wayland_display, xdg_runtime_dir = setup_wayland_environment()
    
    if not wayland_display:
        print("❌ 사용 가능한 Wayland 디스플레이를 찾을 수 없습니다")
        sys.exit(1)
    
    print(f"✅ Wayland 디스플레이: {wayland_display}")
    
    socket_path = os.path.join(xdg_runtime_dir, wayland_display)
    if not os.path.exists(socket_path):
        print(f"❌ Wayland 소켓이 존재하지 않습니다: {socket_path}")
        sys.exit(1)
    
    print(f"✅ Wayland 소켓 확인: {socket_path}")
    
    # Qt 애플리케이션
    app = QApplication(sys.argv)
    print(f"📱 Qt 플랫폼: {app.platformName()}")
    
    # YOLO 모델 로드
    model, model_list = load_models()
    if not model:
        print("❌ YOLO 모델을 로드할 수 없습니다")
        sys.exit(1)
    
    # 메인 윈도우
    window = YOLOCameraWindow(model, model_list)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
