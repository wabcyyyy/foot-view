"""
训练 YOLOv8 目标检测模型用于摔倒检测

该脚本训练一个可以同时检测人体位置和判断是否摔倒的模型。
输出：带边界框的检测结果，类别为 fall 或 not_fall
"""

import os
import shutil
from pathlib import Path
from ultralytics import YOLO


# 训练配置
CONFIG = {
    "model": "yolov8s.pt",      # 使用 YOLOv8s（比 nano 更准确，适合 4060Ti 8GB）
    "epochs": 100,               # 训练轮数
    "batch_size": 16,            # 批大小（8GB显存适用）
    "img_size": 640,             # 图像尺寸
    "patience": 20,              # 早停耐心值
}

# 路径
SCRIPT_DIR = Path(__file__).parent
DATASET_PATH = SCRIPT_DIR / "dataset_detect"
DATA_YAML = DATASET_PATH / "data.yaml"
RUNS_DIR = SCRIPT_DIR.parent / "runs" / "detect" / "fall_detection"


def train():
    print("=" * 60)
    print("训练 YOLOv8 摔倒检测模型（目标检测）")
    print("=" * 60)
    
    # 检查数据集
    if not DATA_YAML.exists():
        print(f"\n错误: 数据集配置文件不存在: {DATA_YAML}")
        print("请先运行 prepare_detection_dataset.py 准备数据集")
        return None
    
    print(f"\n配置:")
    print(f"  - 模型: {CONFIG['model']}")
    print(f"  - 训练轮数: {CONFIG['epochs']}")
    print(f"  - 批大小: {CONFIG['batch_size']}")
    print(f"  - 图像尺寸: {CONFIG['img_size']}")
    print(f"  - 数据集: {DATA_YAML}")
    
    # 加载模型
    print("\n加载预训练模型...")
    model = YOLO(CONFIG["model"])
    
    # 开始训练
    print("\n开始训练...")
    results = model.train(
        data=str(DATA_YAML),
        epochs=CONFIG["epochs"],
        imgsz=CONFIG["img_size"],
        batch=CONFIG["batch_size"],
        patience=CONFIG["patience"],
        device=0,                    # 使用 GPU 0
        project=str(RUNS_DIR.parent),
        name=RUNS_DIR.name,
        exist_ok=True,
        # 数据增强
        hsv_h=0.015,                 # 色调变化
        hsv_s=0.7,                   # 饱和度变化
        hsv_v=0.4,                   # 亮度变化
        degrees=10.0,                # 旋转角度
        translate=0.1,               # 平移
        scale=0.5,                   # 缩放
        flipud=0.5,                  # 上下翻转
        fliplr=0.5,                  # 左右翻转
        mosaic=1.0,                  # Mosaic 增强
        mixup=0.1,                   # Mixup 增强
    )
    
    print("\n" + "=" * 60)
    print("训练完成!")
    print("=" * 60)
    
    # 复制最佳模型到 backend/models
    best_model = Path(results.save_dir) / "weights" / "best.pt"
    if best_model.exists():
        dst_dir = SCRIPT_DIR.parent / "backend" / "models"
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_path = dst_dir / "fall_detection.pt"
        
        shutil.copy2(best_model, dst_path)
        print(f"\n最佳模型已复制到: {dst_path}")
    else:
        print(f"\n警告: 找不到最佳模型文件: {best_model}")
    
    print(f"\n训练结果保存在: {results.save_dir}")
    
    return results


if __name__ == "__main__":
    train()

