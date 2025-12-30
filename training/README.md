# 摔倒检测模型训练指南

本目录包含训练 YOLOv8 摔倒检测模型所需的脚本和配置。

## 快速开始

### 1. 下载数据集

从 Kaggle 下载摔倒检测数据集：
- 地址：https://www.kaggle.com/datasets/uttejkumarkandagatla/fall-detection-dataset
- 下载后解压到 `training/raw_data/` 目录

目录结构应类似于：
```
training/
├── raw_data/
│   ├── Fall/
│   │   ├── image1.jpg
│   │   └── ...
│   └── Not Fall/
│       ├── image1.jpg
│       └── ...
├── prepare_dataset.py
├── train.py
└── README.md
```

### 2. 安装依赖

```bash
# 进入项目根目录
cd foot-view

# 使用 uv 安装
uv pip sync pyproject.toml

# 或使用 pip
pip install ultralytics torch torchvision
```

### 3. 准备数据集

```bash
cd training
python prepare_dataset.py
```

这将：
- 读取原始数据
- 转换为 YOLO 格式
- 划分训练集和验证集
- 生成 `fall_detection.yaml` 配置文件

### 4. 开始训练

```bash
python train.py
```

训练参数可在 `train.py` 中的 `CONFIG` 字典修改：
- `epochs`: 训练轮数（默认 100）
- `batch_size`: 批次大小（默认 16，内存不足可减小）
- `model`: 预训练模型（yolov8n/s/m/l/x）

### 5. 使用训练好的模型

训练完成后，模型会自动复制到 `backend/models/fall_detection.pt`。

## 目录结构

```
training/
├── raw_data/           # 原始数据集（需手动下载）
├── dataset/            # 处理后的 YOLO 格式数据集
│   ├── images/
│   │   ├── train/
│   │   └── val/
│   └── labels/
│       ├── train/
│       └── val/
├── runs/               # 训练结果
│   └── detect/
│       └── fall_detection/
│           ├── weights/
│           │   ├── best.pt    # 最佳模型
│           │   └── last.pt    # 最后一轮模型
│           └── ...            # 训练曲线等
├── prepare_dataset.py  # 数据准备脚本
├── train.py            # 训练脚本
├── fall_detection.yaml # 数据配置文件（自动生成）
└── README.md
```

## 常见问题

### Q: 训练很慢怎么办？
A: 
1. 使用 GPU 训练（安装 CUDA 版 PyTorch）
2. 减小 `batch_size`
3. 使用更小的模型（yolov8n.pt）

### Q: 内存不足 (OOM) 怎么办？
A:
1. 减小 `batch_size`（如改为 8 或 4）
2. 减小 `img_size`（如改为 416）

### Q: 如何提高模型精度？
A:
1. 增加 `epochs`
2. 使用更大的模型（yolov8m.pt 或 yolov8l.pt）
3. 增加训练数据
4. 调整数据增强参数

## 模型选择指南

| 模型 | 大小 | 速度 | 精度 | 适用场景 |
|------|------|------|------|---------|
| yolov8n.pt | 6 MB | 最快 | 较低 | 边缘设备、快速原型 |
| yolov8s.pt | 22 MB | 快 | 中等 | 一般应用 |
| yolov8m.pt | 52 MB | 中等 | 较高 | 平衡场景 |
| yolov8l.pt | 87 MB | 较慢 | 高 | 精度优先 |
| yolov8x.pt | 131 MB | 慢 | 最高 | 最高精度需求 |

