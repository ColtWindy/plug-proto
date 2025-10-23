#coding=utf-8
"""
YOLO 모델 관리자
모델 로딩, YOLOE 설정, 모델 전환을 담당
"""
from pathlib import Path
from ultralytics import YOLO


class BaseModelManager:
    """YOLO 모델 관리 베이스 클래스"""
    
    def __init__(self, models_dir):
        """
        Args:
            models_dir: 모델 디렉토리 경로
        """
        self.models_dir = Path(models_dir)
        self.current_model = None
        self.model_list = []
    
    @property
    def file_extension(self):
        """서브클래스에서 구현: 파일 확장자"""
        raise NotImplementedError
    
    @property
    def model_type_name(self):
        """서브클래스에서 구현: 모델 타입 이름"""
        raise NotImplementedError
    
    def load_models(self):
        """
        모델 디렉토리에서 사용 가능한 모델 검색 및 첫 번째 모델 로드
        
        Returns:
            (model, model_list): 로드된 모델과 전체 모델 리스트
        """
        model_files = sorted(self.models_dir.glob(f"*{self.file_extension}"))
        
        if not model_files:
            print(f"❌ {self.file_extension} 파일을 찾을 수 없습니다")
            return None, []
        
        # 모델 목록 생성
        self.model_list = [(f.name, str(f)) for f in model_files]
        
        print(f"📦 {self.model_type_name} 모델: {len(model_files)}개")
        
        # 첫 번째 모델 로드
        self.current_model = self._load_single_model(str(model_files[0]))
        print(f"✅ 모델: {model_files[0].name}")
        
        return self.current_model, self.model_list
    
    def switch_model(self, model_path, task=None):
        """
        모델 전환
        
        Args:
            model_path: 모델 파일 경로
            task: YOLO task (detect, segment 등). None이면 자동 감지
        
        Returns:
            새로운 모델 객체
        """
        self.current_model = self._load_single_model(model_path, task)
        return self.current_model
    
    def _load_single_model(self, model_path, task=None):
        """
        단일 모델 로드 (YOLOE 자동 처리)
        서브클래스에서 필요시 오버라이드
        
        Args:
            model_path: 모델 파일 경로
            task: YOLO task (None이면 자동 감지)
        
        Returns:
            로드된 YOLO 모델
        """
        model_path = str(model_path)
        
        # YOLOE 모델 처리
        if self._is_yoloe_model(model_path):
            return self._load_yoloe_model(model_path)
        
        # 일반 YOLO 모델
        if task is None:
            task = self._detect_task(model_path)
        
        model = YOLO(model_path, task=task)
        print(f"✅ {self.model_type_name} 모델 (task={task})")
        return model
    
    def _load_yoloe_model(self, model_path):
        """
        YOLOE 모델 로드
        서브클래스에서 필요시 오버라이드
        
        Args:
            model_path: 모델 파일 경로
        
        Returns:
            로드된 YOLO 모델
        """
        model = YOLO(model_path)
        
        # .pt 파일 중 prompt-free가 아닌 모델만 프롬프트 지원
        if self._is_pt_file(model_path) and not self._is_prompt_free(model_path):
            self._setup_yoloe_prompt(model, ["car"])
            print(f"ℹ️ YOLOE (프롬프트 지원)")
        else:
            mode = "prompt-free" if self._is_prompt_free(model_path) else "고정 vocabulary"
            print(f"ℹ️ YOLOE ({mode})")
        
        return model
    
    def _setup_yoloe_prompt(self, model, classes):
        """
        YOLOE 프롬프트 설정
        
        Args:
            model: YOLO 모델 객체
            classes: 탐지할 클래스 리스트
        """
        try:
            if not hasattr(model, 'set_classes') or not hasattr(model, 'get_text_pe'):
                print(f"⚠️ YOLOE 메서드를 찾을 수 없습니다")
                return
            
            text_embeddings = model.get_text_pe(classes)
            model.set_classes(classes, text_embeddings)
            print(f"✅ YOLOE 프롬프트: {', '.join(classes)}")
        except Exception as e:
            print(f"⚠️ YOLOE 프롬프트 설정 실패: {e}")
    
    @staticmethod
    def _is_yoloe_model(model_path):
        """YOLOE 모델인지 확인"""
        return "yoloe" in Path(model_path).stem.lower()
    
    @staticmethod
    def _is_pt_file(model_path):
        """PyTorch 모델 파일인지 확인"""
        return Path(model_path).suffix.lower() == '.pt'
    
    @staticmethod
    def _is_prompt_free(model_path):
        """Prompt-free 모델인지 확인 ('-pf' 포함)"""
        return '-pf' in Path(model_path).stem.lower()
    
    @staticmethod
    def _detect_task(model_path):
        """파일명에서 task 추론"""
        name = Path(model_path).stem.lower()
        
        if 'seg' in name or 'segment' in name:
            return 'segment'
        elif 'cls' in name or 'classify' in name:
            return 'classify'
        elif 'pose' in name:
            return 'pose'
        elif 'obb' in name:
            return 'obb'
        
        return 'detect'


class PyTorchModelManager(BaseModelManager):
    """PyTorch 모델 전용 관리자"""
    
    @property
    def file_extension(self):
        return ".pt"
    
    @property
    def model_type_name(self):
        return "PyTorch"


class TensorRTModelManager(BaseModelManager):
    """TensorRT 엔진 전용 관리자"""
    
    @property
    def file_extension(self):
        return ".engine"
    
    @property
    def model_type_name(self):
        return "TensorRT"
    
    def _load_yoloe_model(self, model_path):
        """
        TensorRT YOLOE는 프롬프트 변경 불가 (고정 vocabulary)
        
        Args:
            model_path: 모델 파일 경로
        
        Returns:
            로드된 YOLO 모델
        """
        model = YOLO(model_path)
        mode = "prompt-free" if self._is_prompt_free(model_path) else "고정 vocabulary"
        print(f"ℹ️ YOLOE ({mode})")
        return model


class YOLOEModelManager(BaseModelManager):
    """YOLOE 모델 전용 관리자 (프롬프트 제어 가능)"""
    
    def __init__(self, models_dir):
        super().__init__(models_dir)
        self.current_classes = ["car"]  # 기본 프롬프트
        self.visual_prompt = None  # visual prompt 이미지 경로
    
    @property
    def file_extension(self):
        return ".pt"
    
    @property
    def model_type_name(self):
        return "YOLOE"
    
    def load_models(self):
        """YOLOE 모델만 검색"""
        model_files = sorted(self.models_dir.glob(f"*{self.file_extension}"))
        yoloe_files = [f for f in model_files if self._is_yoloe_model(str(f))]
        
        if not yoloe_files:
            print(f"❌ YOLOE {self.file_extension} 파일을 찾을 수 없습니다")
            return None, []
        
        # 모델 목록 생성
        self.model_list = [(f.name, str(f)) for f in yoloe_files]
        
        print(f"📦 {self.model_type_name} 모델: {len(yoloe_files)}개")
        
        # 첫 번째 모델 로드
        self.current_model = self._load_single_model(str(yoloe_files[0]))
        print(f"✅ 모델: {yoloe_files[0].name}")
        
        return self.current_model, self.model_list
    
    def update_prompt(self, classes):
        """
        프롬프트 업데이트 (런타임에 변경 가능)
        
        Args:
            classes: 클래스 리스트 (예: ["car", "person"])
        
        Returns:
            성공 여부
        """
        if not self.current_model:
            print("❌ 모델이 로드되지 않았습니다")
            return False
        
        # prompt-free 모델은 프롬프트 변경 불가
        if hasattr(self.current_model, 'model') and hasattr(self.current_model.model, 'model'):
            model_path = getattr(self.current_model, 'ckpt_path', '')
            if self._is_prompt_free(model_path):
                print("⚠️ Prompt-free 모델은 프롬프트 변경이 불가능합니다")
                return False
        
        try:
            self._setup_yoloe_prompt(self.current_model, classes)
            self.current_classes = classes
            return True
        except Exception as e:
            print(f"❌ 프롬프트 업데이트 실패: {e}")
            return False
    
    def set_visual_prompt(self, prompt_data):
        """
        Visual prompt 설정
        
        Args:
            prompt_data: list of dicts or single dict or None
        
        Returns:
            성공 여부
        """
        if not self.current_model:
            print("❌ 모델이 로드되지 않았습니다")
            return False
        
        if not prompt_data:
            self.visual_prompt = None
            print("✅ Visual prompt 해제")
            return True
        
        try:
            self.visual_prompt = prompt_data
            
            if isinstance(prompt_data, list):
                total = sum(len(p['bboxes']) for p in prompt_data)
                print(f"✅ Visual prompt: {len(prompt_data)}개 이미지, {total}개 객체")
            else:
                image_name = Path(prompt_data['image_path']).name
                bbox_count = len(prompt_data['bboxes'])
                print(f"✅ Visual prompt: {image_name} ({bbox_count}개)")
            
            return True
        except Exception as e:
            print(f"❌ Visual prompt 설정 실패: {e}")
            return False


# 하위 호환성을 위한 별칭
ModelManager = BaseModelManager

