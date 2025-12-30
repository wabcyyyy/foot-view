"""
摔倒检测模型测试脚本
测试 YOLOv8 目标检测模型的功能

用法：
    python scripts/test_model.py
"""

import sys
import os
import cv2
import random
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置 UTF-8 输出（Windows）
sys.stdout.reconfigure(encoding='utf-8')

# 降低 ultralytics 日志级别
logging.getLogger('ultralytics').setLevel(logging.WARNING)

# 导入检测器
from backend import FallDetector


def run_tests():
    print("=" * 60)
    print("摔倒检测模型测试")
    print("=" * 60)
    
    # 1. 检查模型文件
    print("\n1. 检查模型文件...")
    model_path = project_root / "backend" / "models" / "fall_detection.pt"
    print(f"   模型路径: {model_path}")
    print(f"   文件存在: {'✅' if model_path.exists() else '❌'}")
    
    if not model_path.exists():
        print("\n   ⚠️ 模型文件不存在！")
        print("   请按以下步骤训练模型：")
        print("   1. python training/prepare_detection_dataset.py")
        print("   2. python training/train_detection.py")
        return
    
    # 2. 加载模型
    print("\n2. 加载模型...")
    try:
        detector = FallDetector()
        if detector.model:
            print("   ✅ 模型加载成功！")
            print(f"   类别: {detector.model.names}")
        else:
            print("   ❌ 模型加载失败")
            return
    except Exception as e:
        print(f"   ❌ 加载失败: {e}")
        return
    
    # 3. 测试单帧检测
    print("\n3. 测试单帧检测...")
    
    # 查找测试图像
    test_dir = project_root / "training" / "dataset_detect" / "images" / "val"
    
    test_images = []
    if test_dir.exists():
        for ext in ['*.jpg', '*.png', '*.jpeg']:
            test_images.extend(list(test_dir.glob(ext)))
    
    if not test_images:
        print("   ⚠️ 找不到测试图像")
        return
    
    # 随机选择测试图像
    random.shuffle(test_images)
    sample_images = test_images[:10]
    
    print(f"   测试 {len(sample_images)} 张图像...")
    print()
    
    correct = 0
    total = 0
    
    for img_path in sample_images:
        # 从文件名判断真实标签
        filename = img_path.stem.lower()
        if filename.startswith("fall") and not filename.startswith("not"):
            true_label = "fall"
        elif "not" in filename:
            true_label = "not_fall"
        else:
            true_label = "unknown"
        
        # 读取图像并检测
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue
        
        result = detector.detect_frame(frame)
        
        # 判断预测结果
        if result['fall_detected']:
            pred_label = "fall"
        elif result['total_persons'] > 0:
            pred_label = "not_fall"
        else:
            pred_label = "no_detection"
        
        # 比较
        if true_label != "unknown":
            total += 1
            is_correct = (pred_label == true_label)
            if is_correct:
                correct += 1
            
            status = "✅" if is_correct else "❌"
            print(f"   [{status}] {img_path.name:<25} | 预测: {pred_label:<10} | 真实: {true_label}")
    
    # 计算准确率
    if total > 0:
        accuracy = (correct / total) * 100
        print(f"\n   准确率: {correct}/{total} = {accuracy:.1f}%")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()

