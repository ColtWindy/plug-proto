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
            mvsdk.CameraSetTriggerMode(self.hCamera, 0)
            mvsdk.CameraSetAeState(self.hCamera, 0)
            mvsdk.CameraSetExposureTime(self.hCamera, 30 * 1000)
            mvsdk.CameraSetAnalogGain(self.hCamera, 0)
            
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
        FrameHead = pFrameHead[0]
        
        mvsdk.CameraImageProcess(hCamera, pRawData, self.pFrameBuffer, FrameHead)
        mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
        
        # OpenCV 이미지로 변환
        frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.pFrameBuffer)
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 3))
        frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_NEAREST)
        
        # QImage로 변환
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        # 등록된 콜백 함수 호출
        if self.frame_callback:
            self.frame_callback(q_image)
    
    def set_exposure(self, value_ms):
        """노출시간 설정"""
        mvsdk.CameraSetExposureTime(self.hCamera, int(value_ms * 1000))
        self.camera_info['exposure'] = value_ms
    
    def set_gain(self, value):
        """게인 설정"""
        mvsdk.CameraSetAnalogGain(self.hCamera, int(value))
        self.camera_info['gain'] = value
    
    def get_exposure_ms(self):
        """현재 노출시간 (ms 단위)"""
        return mvsdk.CameraGetExposureTime(self.hCamera) / 1000.0
    
    def get_gain(self):
        """현재 게인"""
        return mvsdk.CameraGetAnalogGain(self.hCamera)
    
    def set_exposure_mode(self, manual_mode):
        """노출 모드 설정 (True: 수동, False: 자동)"""
        if manual_mode:
            mvsdk.CameraSetAeState(self.hCamera, 0)
            print("수동 노출 모드로 설정")
        else:
            mvsdk.CameraSetAeState(self.hCamera, 1)
            print("자동 노출 모드로 설정")
    
    def set_fps_mode(self, fps):
        """FPS 모드 설정"""
        if fps == "Auto":
            mvsdk.CameraSetTriggerMode(self.hCamera, 0)  # 자동 연속
            print("자동 FPS 모드")
        else:
            mvsdk.CameraSetTriggerMode(self.hCamera, 1)  # 수동 트리거
            print(f"{fps} FPS 모드로 설정")
        return fps
    
    def set_frame_speed(self, speed_mode):
        """프레임 속도 설정 (0: 저속, 1: 일반, 2: 고속)"""
        mvsdk.CameraSetFrameSpeed(self.hCamera, speed_mode)
        print(f"프레임 속도 모드: {speed_mode} (0:저속, 1:일반, 2:고속)")
    
    def get_frame_speed(self):
        """현재 프레임 속도 모드 가져오기"""
        return mvsdk.CameraGetFrameSpeed(self.hCamera)
    
    
    def cleanup(self):
        """종료 시 정리"""
        if self.hCamera:
            mvsdk.CameraUnInit(self.hCamera)
        if self.pFrameBuffer:
            mvsdk.CameraAlignFree(self.pFrameBuffer)
