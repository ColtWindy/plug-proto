from pathlib import Path
from ultralytics import YOLO

# Load a YOLO11n PyTorch model
script_dir = Path(__file__).parent # 현재 실행 중인 스크립트 파일의 절대 경로. parent: 부모경로를 가져옴 
model = YOLO(script_dir / "models/yolo8n_trash.pt")

# Export the model to TensorRT
# 오류 발생시: pip install onnx==1.18 이후 다시 시도
model.export(format="engine")  # creates 'yolo11n.engine'

# Load the exported TensorRT model
trt_model = YOLO(script_dir/ "models/yolo8n_trash.engine")

# Run inference
results = trt_model("https://ultralytics.com/images/bus.jpg")
