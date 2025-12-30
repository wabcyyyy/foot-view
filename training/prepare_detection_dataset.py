"""
准备 YOLO 目标检测数据集

该脚本将 Kaggle Fall Detection Dataset 转换为标准 YOLO 目标检测格式。

数据集格式说明：
- 原始标签格式：class_id x_center y_center width height
- class 0 = fall (摔倒)
- class 1 = not_fall (正常)

目标目录结构：
dataset_detect/
├── images/
│   ├── train/
│   └── val/
├── labels/
│   ├── train/
│   └── val/
└── data.yaml
"""

import os
import shutil
from pathlib import Path


# 路径配置
SCRIPT_DIR = Path(__file__).parent
RAW_DATA_DIR = SCRIPT_DIR / "raw_data" / "fall_dataset"
OUTPUT_DIR = SCRIPT_DIR / "dataset_detect"

# 类别定义
CLASSES = ["fall", "not_fall"]


def copy_with_rename(src_dir, dst_images_dir, dst_labels_dir, images_src_dir, labels_src_dir):
    """复制并统一命名图像和标签文件"""
    
    # 获取所有图像文件
    image_files = []
    for ext in ['*.jpg', '*.png', '*.jpeg']:
        image_files.extend(images_src_dir.glob(ext))
    
    copied_count = 0
    for img_file in image_files:
        # 查找对应的标签文件
        label_file = labels_src_dir / (img_file.stem + ".txt")
        
        if not label_file.exists():
            print(f"  警告: 找不到标签文件 {label_file.name}，跳过")
            continue
        
        # 生成新文件名（统一格式，移除空格）
        new_name = img_file.stem.replace(" ", "_").lower()
        new_img_name = f"{new_name}{img_file.suffix}"
        new_label_name = f"{new_name}.txt"
        
        # 复制图像
        shutil.copy2(img_file, dst_images_dir / new_img_name)
        # 复制标签
        shutil.copy2(label_file, dst_labels_dir / new_label_name)
        
        copied_count += 1
    
    return copied_count


def create_data_yaml():
    """创建 YOLO data.yaml 配置文件"""
    yaml_content = f"""# Fall Detection Dataset
# YOLO 目标检测格式

path: {OUTPUT_DIR.absolute()}
train: images/train
val: images/val

# 类别
nc: 2
names:
  0: fall
  1: not_fall
"""
    
    yaml_path = OUTPUT_DIR / "data.yaml"
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    
    return yaml_path


def main():
    print("=" * 60)
    print("准备 YOLO 目标检测数据集")
    print("=" * 60)
    
    # 检查原始数据目录
    if not RAW_DATA_DIR.exists():
        print(f"\n错误: 原始数据目录不存在: {RAW_DATA_DIR}")
        print("\n请按以下步骤操作：")
        print("1. 从 Kaggle 下载数据集:")
        print("   https://www.kaggle.com/datasets/uttejkumarkandagatla/fall-detection-dataset")
        print(f"2. 解压到: {RAW_DATA_DIR}")
        return False
    
    # 创建输出目录结构
    print("\n1. 创建目录结构...")
    dirs_to_create = [
        OUTPUT_DIR / "images" / "train",
        OUTPUT_DIR / "images" / "val",
        OUTPUT_DIR / "labels" / "train",
        OUTPUT_DIR / "labels" / "val",
    ]
    
    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)
        print(f"   [OK] {d}")
    
    # 复制训练集
    print("\n2. 复制训练集...")
    train_count = copy_with_rename(
        RAW_DATA_DIR,
        OUTPUT_DIR / "images" / "train",
        OUTPUT_DIR / "labels" / "train",
        RAW_DATA_DIR / "images" / "train",
        RAW_DATA_DIR / "labels" / "train"
    )
    print(f"   [OK] 复制了 {train_count} 个训练样本")
    
    # 复制验证集
    print("\n3. 复制验证集...")
    val_count = copy_with_rename(
        RAW_DATA_DIR,
        OUTPUT_DIR / "images" / "val",
        OUTPUT_DIR / "labels" / "val",
        RAW_DATA_DIR / "images" / "val",
        RAW_DATA_DIR / "labels" / "val"
    )
    print(f"   [OK] 复制了 {val_count} 个验证样本")
    
    # 创建 data.yaml
    print("\n4. 创建 data.yaml 配置文件...")
    yaml_path = create_data_yaml()
    print(f"   [OK] {yaml_path}")
    
    # 统计信息
    print("\n" + "=" * 60)
    print("数据集准备完成！")
    print("=" * 60)
    print(f"\n数据集路径: {OUTPUT_DIR}")
    print(f"训练集: {train_count} 张图像")
    print(f"验证集: {val_count} 张图像")
    print(f"类别: {CLASSES}")
    print(f"\n配置文件: {yaml_path}")
    
    print("\n下一步：运行 train_detection.py 开始训练")
    
    return True


if __name__ == "__main__":
    main()

