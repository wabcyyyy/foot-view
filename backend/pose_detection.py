"""
姿势检测模块
负责从图像中检测人体姿势关键点
使用 YOLO Pose 进行人体姿势估计（兼容所有 Python 版本）
"""

import logging
import cv2
import numpy as np

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 尝试导入 YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    logging.info("YOLO 加载成功")
except ImportError:
    YOLO_AVAILABLE = False
    logging.warning("ultralytics 未安装，将无法进行姿势检测。请运行: pip install ultralytics")

# 定义需要的关键点
REQUIRED_KEYPOINTS = [
    'LEFT_ANKLE', 'RIGHT_ANKLE', 'LEFT_SHOULDER', 'RIGHT_SHOULDER',
    'LEFT_HIP', 'RIGHT_HIP', 'LEFT_KNEE', 'RIGHT_KNEE', 'NOSE'
]

# YOLO Pose 关键点索引映射（COCO 17 关键点格式）
# 0: nose, 1: left_eye, 2: right_eye, 3: left_ear, 4: right_ear,
# 5: left_shoulder, 6: right_shoulder, 7: left_elbow, 8: right_elbow,
# 9: left_wrist, 10: right_wrist, 11: left_hip, 12: right_hip,
# 13: left_knee, 14: right_knee, 15: left_ankle, 16: right_ankle
YOLO_KEYPOINT_NAMES = [
    'NOSE', 'LEFT_EYE', 'RIGHT_EYE', 'LEFT_EAR', 'RIGHT_EAR',
    'LEFT_SHOULDER', 'RIGHT_SHOULDER', 'LEFT_ELBOW', 'RIGHT_ELBOW',
    'LEFT_WRIST', 'RIGHT_WRIST', 'LEFT_HIP', 'RIGHT_HIP',
    'LEFT_KNEE', 'RIGHT_KNEE', 'LEFT_ANKLE', 'RIGHT_ANKLE'
]

# 骨架连接定义（用于绘制）
SKELETON_CONNECTIONS = [
    (0, 1), (0, 2), (1, 3), (2, 4),  # 头部
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # 手臂
    (5, 11), (6, 12), (11, 12),  # 躯干
    (11, 13), (13, 15), (12, 14), (14, 16)  # 腿部
]

# 全局 Pose 检测器实例
_pose_detector = None


class YoloPoseResult:
    """YOLO Pose 检测结果封装类"""
    def __init__(self, keypoints, confidence, bbox):
        self.keypoints = keypoints  # shape: (17, 3) - x, y, confidence
        self.confidence = confidence
        self.bbox = bbox
        self.pose_landmarks = self  # 兼容性属性
        self.landmark = self._create_landmarks()
    
    def _create_landmarks(self):
        """创建兼容的 landmark 列表"""
        landmarks = []
        for i, kp in enumerate(self.keypoints):
            landmarks.append(Landmark(kp[0], kp[1], 0.0, kp[2]))
        return landmarks


class Landmark:
    """关键点类"""
    def __init__(self, x, y, z, visibility):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility


def get_pose_detector():
    """
    获取或创建 YOLO Pose 检测器实例
    
    Returns:
        YOLO: Pose 检测器实例
    """
    global _pose_detector
    
    if not YOLO_AVAILABLE:
        return None
    
    if _pose_detector is None:
        try:
            # 使用 YOLO Pose 模型（会自动下载）
            _pose_detector = YOLO('yolov8n-pose.pt')
            logging.info("YOLO Pose 检测器初始化成功")
        except Exception as e:
            logging.error(f"加载 YOLO Pose 模型失败: {e}")
            return None
    
    return _pose_detector


def detect_pose(image):
    """
    检测图像中的人体姿势
    
    Args:
        image: 输入图像 (numpy array, BGR 格式)
    
    Returns:
        YoloPoseResult 或 None（如果未检测到人体）
    """
    if not YOLO_AVAILABLE:
        logging.warning("YOLO 不可用，无法进行姿势检测")
        return None
    
    pose = get_pose_detector()
    if pose is None:
        return None
    
    # 进行姿势检测
    results = pose(image, verbose=False)
    
    if len(results) == 0 or results[0].keypoints is None:
        return None
    
    # 获取第一个检测到的人
    keypoints_data = results[0].keypoints
    
    if keypoints_data.xy is None or len(keypoints_data.xy) == 0:
        return None
    
    # 获取第一个人的关键点
    kps = keypoints_data.xy[0].cpu().numpy()  # shape: (17, 2)
    
    # 获取置信度
    if keypoints_data.conf is not None and len(keypoints_data.conf) > 0:
        confs = keypoints_data.conf[0].cpu().numpy()  # shape: (17,)
    else:
        confs = np.ones(17)
    
    # 组合成 (17, 3) 格式：x, y, confidence
    # 将像素坐标归一化到 0-1 范围
    h, w = image.shape[:2]
    keypoints = np.zeros((17, 3))
    keypoints[:, 0] = kps[:, 0] / w  # 归一化 x
    keypoints[:, 1] = kps[:, 1] / h  # 归一化 y
    keypoints[:, 2] = confs  # 置信度
    
    # 获取边界框
    if results[0].boxes is not None and len(results[0].boxes) > 0:
        bbox = results[0].boxes.xyxy[0].cpu().numpy()
        box_conf = float(results[0].boxes.conf[0])
    else:
        bbox = None
        box_conf = 0.0
    
    return YoloPoseResult(keypoints, box_conf, bbox)


def get_landmark_name(idx):
    """
    获取关键点索引对应的名称（YOLO Pose 格式）
    
    Args:
        idx: 关键点索引
    
    Returns:
        str: 关键点名称
    """
    return YOLO_KEYPOINT_NAMES[idx] if idx < len(YOLO_KEYPOINT_NAMES) else 'UNKNOWN'


def extract_keypoints(results, frame_number):
    """
    从检测结果中提取关键点数据
    
    Args:
        results: 姿势检测结果（YoloPoseResult）
        frame_number: 当前帧编号
    
    Returns:
        dict: 关键点数据字典，如果提取失败则返回 None
    """
    # 检查结果是否有效
    if results is None:
        return None
    
    if not hasattr(results, 'keypoints') or results.keypoints is None:
        return None
    
    keypoints = {'frame': frame_number}
    
    # 提取关键点（YOLO 格式）
    for idx in range(len(results.keypoints)):
        keypoint_name = get_landmark_name(idx)
        if keypoint_name in REQUIRED_KEYPOINTS:
            kp = results.keypoints[idx]
            x, y, conf = kp[0], kp[1], kp[2]
            
            # 只有置信度足够高的关键点才使用
            if conf > 0.3:
                keypoints[f'{keypoint_name}_x'] = float(x)
                keypoints[f'{keypoint_name}_y'] = float(y)
                keypoints[f'{keypoint_name}_z'] = 0.0  # YOLO 没有 z 坐标
                keypoints[f'{keypoint_name}_visibility'] = float(conf)
    
    # 检查是否所有需要的关键点都存在
    if all(f'{kp}_x' in keypoints and f'{kp}_y' in keypoints for kp in REQUIRED_KEYPOINTS):
        return keypoints
    
    return None


def draw_pose_landmarks(image, results):
    """
    在图像上绘制姿势关键点和骨架
    
    Args:
        image: 输入图像 (numpy array, BGR 格式)
        results: YoloPoseResult 检测结果
    
    Returns:
        image: 绘制了关键点的图像
    """
    if results is None or not hasattr(results, 'keypoints'):
        return image
    
    h, w = image.shape[:2]
    keypoints = results.keypoints
    
    # 将归一化坐标转换为像素坐标
    points = []
    for kp in keypoints:
        x = int(kp[0] * w)
        y = int(kp[1] * h)
        conf = kp[2]
        points.append((x, y, conf))
    
    # 绘制骨架连接线
    for connection in SKELETON_CONNECTIONS:
        idx1, idx2 = connection
        if idx1 < len(points) and idx2 < len(points):
            p1 = points[idx1]
            p2 = points[idx2]
            
            # 只绘制置信度足够高的连接
            if p1[2] > 0.3 and p2[2] > 0.3:
                cv2.line(image, (p1[0], p1[1]), (p2[0], p2[1]), (0, 255, 255), 2)
    
    # 绘制关键点
    for i, (x, y, conf) in enumerate(points):
        if conf > 0.3:
            # 不同部位使用不同颜色
            if i == 0:  # 鼻子
                color = (0, 0, 255)  # 红色
            elif i <= 4:  # 眼睛和耳朵
                color = (255, 0, 255)  # 紫色
            elif i <= 10:  # 手臂
                color = (255, 0, 0)  # 蓝色
            else:  # 躯干和腿
                color = (0, 255, 0)  # 绿色
            
            cv2.circle(image, (x, y), 5, color, -1)
            cv2.circle(image, (x, y), 7, (255, 255, 255), 1)
    
    # 绘制边界框
    if results.bbox is not None:
        x1, y1, x2, y2 = [int(v) for v in results.bbox]
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # 显示置信度
        conf_text = f"Person: {results.confidence:.2f}"
        cv2.putText(image, conf_text, (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    return image


def release_pose_detector():
    """
    释放 Pose 检测器资源
    """
    global _pose_detector
    if _pose_detector is not None:
        _pose_detector = None
        logging.info("YOLO Pose 检测器已释放")

