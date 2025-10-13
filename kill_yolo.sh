#!/bin/bash
# YOLO 프로세스 종료

echo "🛑 YOLO 프로세스 종료 중..."
pkill -9 -f yolo_test.py
echo "✅ 완료"

