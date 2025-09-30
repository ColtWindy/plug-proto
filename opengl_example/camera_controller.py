#coding=utf-8
"""
OpenGL Camera Controller
QOpenGLWindow에 최적화된 카메라 제어
"""
import sys
import os
import cv2
import numpy as np
from PySide6.QtGui import QImage

# 프로젝트 루트의 cam 디렉토리에서 mvsdk import
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from cam import mvsdk


class OpenGLCameraController:
    """QOpenGLWindow용 카메라 컨트롤러"""
    
    def __init__(self, target_ip):
        self.hCamera = None
        self.pFrameBuffer = 0
        self.camera_info = {}
        self.target_ip = target_ip
        self.frame_callback = None
        self.frame_number = 0  # 프레임 번호 (카메라 이미지에 표시)
    
    def setup_camera(self):
        """카메라 초기화"""
        try:
            DevList = mvsdk.CameraEnumerateDevice()
            if not DevList:
                return False, "카메라를 찾을 수 없습니다"
            
            target_camera = None
            for dev in DevList:
                if self.target_ip in dev.GetPortType():
                    target_camera = dev
                    break
            
            if not target_camera:
                return False, f"IP {self.target_ip} 카메라 없음"
            
            self.hCamera = mvsdk.CameraInit(target_camera, -1, -1)
            cap = mvsdk.CameraGetCapability(self.hCamera)
            
            # BGR8 포맷으로 출력
            mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)
            
            # 수동 트리거 모드 (필요시 활성화)
            mvsdk.CameraSetTriggerMode(self.hCamera, 0)  # 0: 연속 모드, 1: 트리거 모드
            
            # 자동 노출 활성화
            mvsdk.CameraSetAeState(self.hCamera, 1)
            
            # 아날로그 게인 초기화
            mvsdk.CameraSetAnalogGain(self.hCamera, 0)
            
            # 고속 모드
            mvsdk.CameraSetFrameSpeed(self.hCamera, 2)
            
            # 프레임 버퍼 할당
            buffer_size = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * 3
            self.pFrameBuffer = mvsdk.CameraAlignMalloc(buffer_size, 16)
            
            # 콜백 함수 설정
            mvsdk.CameraSetCallbackFunction(self.hCamera, self.grab_callback, 0)
            
            # 카메라 시작
            mvsdk.CameraPlay(self.hCamera)
            
            self.camera_info = {
                'name': target_camera.GetFriendlyName(),
                'ip': self.target_ip,
                'width': cap.sResolutionRange.iWidthMax,
                'height': cap.sResolutionRange.iHeightMax,
                'exposure': int(self.get_exposure_ms()),
                'gain': self.get_gain()
            }
            
            print(f"✅ 카메라 연결 성공: {self.camera_info['name']}")
            return True, "성공"
            
        except Exception as e:
            return False, f"카메라 초기화 오류: {e}"
    
    def set_frame_callback(self, callback_func):
        """프레임 콜백 함수 설정"""
        self.frame_callback = callback_func
    
    @mvsdk.method(mvsdk.CAMERA_SNAP_PROC)
    def grab_callback(self, hCamera, pRawData, pFrameHead, pContext):
        """카메라 콜백 함수 - 새 프레임이 준비되면 자동 호출"""
        try:
            FrameHead = pFrameHead[0]
            
            # 이미지 처리
            mvsdk.CameraImageProcess(hCamera, pRawData, self.pFrameBuffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
            
            # 유효한 프레임 데이터 확인
            if FrameHead.uBytes == 0:
                return
            
            # OpenCV 이미지로 변환
            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 3))
            
            # 프레임에 숫자 추가 (ps_camera.py 방식)
            self.frame_number += 1
            height, width = frame.shape[:2]
            if width >= 100 and height >= 50:
                text = str(self.frame_number)
                # 이미지 크기에 비례한 폰트 크기
                font_scale = width / 200.0
                thickness = max(1, int(width / 160))
                cv2.putText(frame, text, (width//2 - int(50 * font_scale), height//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale * 4, (255, 255, 255), thickness)
            
            # QImage로 변환
            bytes_per_line = 3 * width
            frame_contiguous = np.ascontiguousarray(frame)
            q_image = QImage(frame_contiguous.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            
            # 등록된 콜백 함수 호출
            if self.frame_callback and not q_image.isNull():
                self.frame_callback(q_image)
                
        except Exception as e:
            print(f"❌ 카메라 콜백 오류: {e}")
    
    def set_gain(self, value):
        """게인 설정"""
        if self.hCamera:
            mvsdk.CameraSetAnalogGain(self.hCamera, int(value))
            self.camera_info['gain'] = value
    
    def set_exposure_range(self, max_exposure_us):
        """노출시간 범위 설정"""
        if self.hCamera:
            try:
                mvsdk.CameraSetAeExposureRange(self.hCamera, 1, max_exposure_us)
                print(f"📸 노출시간 최대값: {max_exposure_us}μs")
            except Exception as e:
                print(f"❌ 노출시간 설정 실패: {e}")
    
    def get_exposure_ms(self):
        """현재 노출시간 (ms 단위)"""
        if self.hCamera:
            return mvsdk.CameraGetExposureTime(self.hCamera) / 1000.0
        return 0
    
    def get_gain(self):
        """현재 게인"""
        if self.hCamera:
            return mvsdk.CameraGetAnalogGain(self.hCamera)
        return 0
    
    def cleanup(self):
        """종료 시 정리"""
        if self.hCamera:
            mvsdk.CameraUnInit(self.hCamera)
        if self.pFrameBuffer:
            mvsdk.CameraAlignFree(self.pFrameBuffer)
