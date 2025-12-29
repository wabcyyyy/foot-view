# Foot View - 步态分析系统

本项目使用 Flask 作为后端，Vue 3 + Vite 作为前端。

## 环境清理与配置 (使用 uv)

由于之前可能存在 Anaconda 环境冲突，建议按照以下步骤重新配置环境。

1.  **删除旧的虚拟环境** (如果存在):
    删除 `D:/wcy/note/互联网+/foot-view/venv` 文件夹。

2.  **安装 uv** (如果尚未安装):
    ```bash
    pip install uv
    ```

3.  **创建并同步新环境**:
    在项目根目录 (`D:/wcy/note/互联网+/foot-view`) 运行：
    ```bash
    uv venv
    uv pip sync pyproject.toml
    ```
    *注意：我们在 `pyproject.toml` 中使用了 `opencv-python-headless` 来解决 OpenCV 下载和依赖问题。*

## 启动项目

### 后端 (Flask)

1.  激活虚拟环境:
    *   Windows (PowerShell): `.venv\Scripts\activate`
    *   Windows (CMD): `.venv\Scripts\activate.bat`

2.  运行 Flask 应用:
    ```bash
    python app.py
    ```
    后端将在 `http://127.0.0.1:5000` 运行。

### 前端 (Vue + Vite)

1.  进入前端目录:
    ```bash
    cd frontend
    ```

2.  安装依赖:
    ```bash
    npm install
    ```

3.  启动开发服务器:
    ```bash
    npm run dev
    ```
    前端将在 `http://localhost:5173` (默认 Vite 端口) 运行。

## 项目结构说明

*   `app.py`: Flask 后端入口。
*   `backend/`: 包含视频处理和分析逻辑。
*   `frontend/`: Vue + Vite 前端项目。
*   `pyproject.toml`: Python 依赖管理配置。
*   `uploads/`: 存放上传的视频文件。
*   `outputs/`: 存放处理后的结果文件。

## 常见问题

*   **OpenCV 错误**: 如果仍然遇到 OpenCV 相关错误，请确保已安装 `opencv-python-headless` 且没有安装 `opencv-python`。
*   **端口冲突**: 如果 5000 端口被占用，请修改 `app.py` 中的端口号。
