#coding=utf-8
"""
YOLO PyTorch 모델 테스트
.pt 파일만 로드하고 클래스 목록 표시
"""
import sys
import os
from pathlib import Path
from _lib.wayland_utils import setup_wayland_environment
from PySide6.QtWidgets import QApplication
from ui.main_window import YOLOCameraWindow
from ui.model_manager import ModelManager


def show_model_info(model, model_path):
    """PyTorch 모델 정보 표시"""
    print("\n" + "=" * 60)
    print("📊 PyTorch 모델 정보")
    print("=" * 60)
    
    # 파일 크기
    file_size_mb = Path(model_path).stat().st_size / (1024 * 1024)
    print(f"파일 크기: {file_size_mb:.1f} MB")
    
    # 모델 속성
    if hasattr(model, 'task'):
        print(f"Task: {model.task}")
    
    # 클래스 목록
    if hasattr(model, 'names'):
        class_names = model.names
        print(f"\n클래스 개수: {len(class_names)}")
        print(f"클래스 목록:")
        
        # 10개씩 출력
        for i, (idx, name) in enumerate(class_names.items()):
            if i % 10 == 0:
                print(f"  ", end="")
            print(f"{idx}:{name}", end="  ")
            if (i + 1) % 10 == 0:
                print()
        print()
    
    # 모델 아키텍처 정보
    if hasattr(model, 'model'):
        try:
            total_params = sum(p.numel() for p in model.model.parameters())
            print(f"\n파라미터 수: {total_params:,}")
        except:
            pass
    
    print("=" * 60 + "\n")


def main():
    """PyTorch 모델 테스트"""
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
    
    # 모델 디렉토리에서 .pt 파일만 검색
    models_dir = Path(__file__).parent / "models"
    pt_files = sorted(models_dir.glob("*.pt"))
    
    if not pt_files:
        print("❌ .pt 파일이 없습니다")
        sys.exit(1)
    
    print(f"📦 PyTorch 모델: {len(pt_files)}개")
    for i, f in enumerate(pt_files, 1):
        print(f"  {i}. {f.name}")
    
    # 모델 관리자 설정
    model_manager = ModelManager(models_dir)
    model_manager.model_list = [(f.name, str(f)) for f in pt_files]
    
    first_model_path = str(pt_files[0])
    model_manager.current_model = model_manager._load_single_model(first_model_path)
    
    # 모델 정보 표시
    show_model_info(model_manager.current_model, first_model_path)
    
    # 메인 윈도우 실행
    window = YOLOCameraWindow(model_manager)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

