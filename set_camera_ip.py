#coding=utf-8
import sys
import os

# src/_lib 경로를 추가하여 mvsdk 모듈 import 가능하게 함
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', '_lib'))

import mvsdk
from config import CAMERA_IP, SUBNET_MASK, GATEWAY, PERSISTENT

def set_camera_ip():
    """
    GigE 카메라의 IP 주소를 설정하는 함수
    """
    # 설정할 IP 정보 (config.py에서 로드)
    target_ip = CAMERA_IP
    subnet_mask = SUBNET_MASK
    gateway = GATEWAY
    persistent = PERSISTENT
    
    print("=" * 60)
    print("카메라 IP 설정 스크립트")
    print("=" * 60)
    
    try:
        # SDK 초기화 (0: 영어, 1: 중국어)
        print("\n[1] SDK 초기화 중...")
        err = mvsdk.CameraSdkInit(1)
        if err != mvsdk.CAMERA_STATUS_SUCCESS:
            print(f"❌ SDK 초기화 실패: {mvsdk.CameraGetErrorString(err)}")
            return False
        print("✓ SDK 초기화 완료")
        
        # 카메라 열거
        print("\n[2] 카메라 검색 중...")
        camera_list = mvsdk.CameraEnumerateDevice()
        
        if len(camera_list) == 0:
            print("❌ 연결된 카메라를 찾을 수 없습니다.")
            return False
        
        print(f"✓ {len(camera_list)}개의 카메라 발견")
        
        # 카메라 정보 출력
        print("\n" + "-" * 60)
        for idx, cam_info in enumerate(camera_list):
            print(f"\n카메라 #{idx + 1}")
            print(f"  - 제품명: {cam_info.GetProductName()}")
            print(f"  - 별명: {cam_info.GetFriendlyName()}")
            print(f"  - 인터페이스: {cam_info.GetPortType()}")
            print(f"  - S/N: {cam_info.GetSn()}")
            
            # GigE 카메라인 경우 현재 IP 정보 표시
            port_type = cam_info.GetPortType()
            if "GIGE" in port_type.upper() or "ETH" in port_type.upper():
                try:
                    cam_ip, cam_mask, cam_gw, eth_ip, eth_mask, eth_gw = mvsdk.CameraGigeGetIp(cam_info)
                    print(f"  - 현재 카메라 IP: {cam_ip}")
                    print(f"  - 현재 서브넷: {cam_mask}")
                    print(f"  - 현재 게이트웨이: {cam_gw}")
                except Exception as e:
                    print(f"  - IP 정보 조회 실패: {e}")
        
        print("-" * 60)
        
        # 설정할 카메라 선택
        if len(camera_list) == 1:
            selected_idx = 0
            print(f"\n자동으로 카메라 #{selected_idx + 1} 선택")
        else:
            while True:
                try:
                    selected_idx = int(input(f"\nIP를 설정할 카메라 번호를 입력하세요 (1-{len(camera_list)}): ")) - 1
                    if 0 <= selected_idx < len(camera_list):
                        break
                    else:
                        print(f"❌ 1에서 {len(camera_list)} 사이의 숫자를 입력하세요.")
                except ValueError:
                    print("❌ 올바른 숫자를 입력하세요.")
        
        selected_camera = camera_list[selected_idx]
        
        # IP 설정
        print(f"\n[3] IP 설정 중...")
        print(f"  - 대상 카메라: {selected_camera.GetProductName()}")
        print(f"  - 새 IP: {target_ip}")
        print(f"  - 서브넷 마스크: {subnet_mask}")
        print(f"  - 게이트웨이: {gateway}")
        print(f"  - 영구 저장: {'예' if persistent else '아니오'}")
        
        err = mvsdk.CameraGigeSetIp(selected_camera, target_ip, subnet_mask, gateway, persistent)
        
        if err != mvsdk.CAMERA_STATUS_SUCCESS:
            print(f"❌ IP 설정 실패: {mvsdk.CameraGetErrorString(err)}")
            return False
        
        print("✓ IP 설정 완료!")
        
        # 설정 확인
        print("\n[4] 설정 확인 중...")
        import time
        time.sleep(1)  # 설정 적용 대기
        
        try:
            cam_ip, cam_mask, cam_gw, eth_ip, eth_mask, eth_gw = mvsdk.CameraGigeGetIp(selected_camera)
            print(f"✓ 설정된 카메라 IP: {cam_ip}")
            print(f"✓ 설정된 서브넷: {cam_mask}")
            print(f"✓ 설정된 게이트웨이: {cam_gw}")
            
            if cam_ip == target_ip:
                print("\n" + "=" * 60)
                print("✅ IP 설정이 성공적으로 완료되었습니다!")
                print("=" * 60)
                return True
            else:
                print(f"\n⚠️ 경고: 설정한 IP({target_ip})와 확인된 IP({cam_ip})가 다릅니다.")
                return False
                
        except Exception as e:
            print(f"⚠️ 설정 확인 실패: {e}")
            print("설정은 완료되었으나 확인할 수 없습니다. 카메라를 재시작해주세요.")
            return True
            
    except mvsdk.CameraException as e:
        print(f"❌ 카메라 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n카메라 IP 설정 도구")
    print("주의: 이 스크립트는 GigE 카메라에만 적용됩니다.\n")
    
    success = set_camera_ip()
    
    if success:
        print("\n프로그램을 종료합니다.")
        sys.exit(0)
    else:
        print("\n프로그램을 종료합니다.")
        sys.exit(1)

