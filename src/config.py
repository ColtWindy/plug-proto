#coding=utf-8
"""
카메라 네트워크 설정
"""

# 카메라 IP 설정
CAMERA_IP = "192.168.0.100"
SUBNET_MASK = "255.255.255.0"
GATEWAY = "192.168.0.1"
PERSISTENT = 1  # 1: 영구 저장, 0: 임시 설정

# 필수 값 검증
if not CAMERA_IP:
    raise ValueError("❌ CAMERA_IP가 설정되지 않았습니다.")
