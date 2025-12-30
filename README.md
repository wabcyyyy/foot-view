# Foot View - 步态分析与摔倒检测系统

基于 Flask + Vue 3 的步态分析和摔倒检测系统，使用 YOLOv8 进行实时摔倒检测。

## 项目结构

```
foot-view/
├── app.py                  # Flask 后端入口
├── backend/                # 后端模块
│   ├── __init__.py
│   ├── processing.py       # 视频处理主模块
│   ├── pose_detection.py   # 姿态检测
│   ├── gait_analysis.py    # 步态分析
│   ├── fall_detection.py   # 摔倒检测（YOLOv8）
│   └── models/             # 模型文件目录
│       └── fall_detection.pt
├── frontend/               # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   └── router/
│   └── package.json
├── scripts/                # 测试脚本
│   ├── test_model.py       # 模型测试
│   └── test_video.py       # 视频测试
├── training/               # 模型训练
│   ├── prepare_detection_dataset.py
│   ├── train_detection.py
│   └── README.md
├── pyproject.toml          # Python 依赖
└── README.md
```

## 快速开始

### 1. 环境配置

使用 uv 管理 Python 依赖：

```bash
# 安装 uv（如未安装）
pip install uv

# 创建虚拟环境并安装依赖
uv venv
uv pip sync pyproject.toml
```

### 2. 启动后端

```bash
# 激活虚拟环境
# Windows PowerShell
.venv\Scripts\activate
# Windows CMD
.venv\Scripts\activate.bat

# 运行 Flask
python app.py
```

后端运行在 `http://127.0.0.1:5000`

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:5173`

## 摔倒检测

### 使用预训练模型

确保模型文件 `backend/models/fall_detection.pt` 存在。

### 训练自定义模型

1. 下载数据集到 `training/raw_data/`
2. 准备数据集：
   ```bash
   python training/prepare_detection_dataset.py
   ```
3. 训练模型：
   ```bash
   python training/train_detection.py
   ```

详见 `training/README.md`

## 测试脚本

```bash
# 测试模型
python scripts/test_model.py

# 测试视频（摄像头）
python scripts/test_video.py

# 测试视频文件
python scripts/test_video.py video.mp4

# 测试并保存结果
python scripts/test_video.py video.mp4 --save
```

## 常见问题

- **模型不存在**：需要先训练模型或下载预训练权重
- **OpenCV 错误**：确保使用 `opencv-python-headless`
- **CUDA 不可用**：确保安装了 CUDA 版本的 PyTorch
