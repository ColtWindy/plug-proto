#coding=utf-8
"""카메라 제어"""
import cv2
import numpy as np
import mvsdk
from PySide6.QtGui import QImage

class CameraController:
    def __init__(self, target_ip):
        self.hCamera = None
        self.pFrameBuffer = 0
        self.camera_info = {}
        self.target_ip = target_ip
        self.frame_callback = None  # 프레임 콜백 함수
    
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
            
            mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)
            mvsdk.CameraSetTriggerMode(self.hCamera, 1)  # 수동 트리거 모드
            mvsdk.CameraSetAeState(self.hCamera, 1)  # 자동 노출 활성화
            mvsdk.CameraSetAnalogGain(self.hCamera, 0)
            
            # 노출시간은 ps_camera.py에서 설정 (중복 제거)
            
            # 프레임 속도 설정 (0: 저속, 1: 일반, 2: 고속)
            mvsdk.CameraSetFrameSpeed(self.hCamera, 2)  # 고속 모드
            
            buffer_size = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * 3
            self.pFrameBuffer = mvsdk.CameraAlignMalloc(buffer_size, 16)
            # 콜백 함수 설정
            mvsdk.CameraSetCallbackFunction(self.hCamera, self.grab_callback, 0)
            mvsdk.CameraPlay(self.hCamera)
            
            self.camera_info = {
                'name': target_camera.GetFriendlyName(),
                'ip': self.target_ip,
                'width': cap.sResolutionRange.iWidthMax,
                'height': cap.sResolutionRange.iHeightMax,
                'exposure': int(self.get_exposure_ms()),
                'gain': self.get_gain()
            }
            
            print("카메라 연결 성공!")
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
            
            mvsdk.CameraImageProcess(hCamera, pRawData, self.pFrameBuffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
            
            # 유효한 프레임 데이터 확인
            if FrameHead.uBytes == 0:
                return
            
            # OpenCV 이미지로 변환 (안전한 크기 계산)
            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            
            # 실제 채널 수 계산
            total_pixels = FrameHead.iHeight * FrameHead.iWidth
            if len(frame) == total_pixels * 3:
                # 3채널 (BGR)
                frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 3))
            elif len(frame) == total_pixels:
                # 1채널 (Grayscale) → 3채널로 변환
                frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth))
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            else:
                print(f"지원하지 않는 프레임 형식: {len(frame)} bytes")
                return
                
            frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_NEAREST)
            
            # 안전한 QImage 변환
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            
            # 데이터 연속성 보장
            frame_contiguous = np.ascontiguousarray(frame)
            q_image = QImage(frame_contiguous.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            
            # 등록된 콜백 함수 호출
            if self.frame_callback and not q_image.isNull():
                self.frame_callback(q_image)
                
        except Exception as e:
            print(f"카메라 콜백 오류: {e}")
    
    
    def set_gain(self, value):
        """게인 설정"""
        mvsdk.CameraSetAnalogGain(self.hCamera, int(value))
        self.camera_info['gain'] = value
    
    def set_exposure_range(self, max_exposure_us):
        """노출시간 범위 설정"""
        try:
            mvsdk.CameraSetAeExposureRange(self.hCamera, 100, max_exposure_us)
            print(f"📸 노출시간 설정: {max_exposure_us}μs")
        except Exception as e:
            print(f"노출시간 설정 실패: {e}")
    
    def get_exposure_ms(self):
        """현재 노출시간 (ms 단위)"""
        return mvsdk.CameraGetExposureTime(self.hCamera) / 1000.0
    
    def get_gain(self):
        """현재 게인"""
        return mvsdk.CameraGetAnalogGain(self.hCamera)
    
    
    
    
    
    def cleanup(self):
        """종료 시 정리"""
        if self.hCamera:
            mvsdk.CameraUnInit(self.hCamera)
        if self.pFrameBuffer:
            mvsdk.CameraAlignFree(self.pFrameBuffer)
