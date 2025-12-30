"""
Backend 模块
包含视频处理、姿势检测、步态分析和摔倒检测功能
"""

from .processing import process_video, analyze_keypoints
from .pose_detection import detect_pose, extract_keypoints, REQUIRED_KEYPOINTS
from .gait_analysis import (
    analyze_gait,
    detect_gait_cycles,
    calculate_step_lengths,
    calculate_gait_metrics,
    calculate_torso_stability,
    calculate_swing_amplitude,
    calculate_knee_angles
)
from .fall_detection import (
    FallDetector,
    detect_fall,
    detect_fall_in_frame,
    format_fall_warning,
    get_detector
)

__all__ = [
    # 主处理函数
    'process_video',
    'analyze_keypoints',
    
    # 姿势检测
    'detect_pose',
    'extract_keypoints',
    'REQUIRED_KEYPOINTS',
    
    # 步态分析
    'analyze_gait',
    'detect_gait_cycles',
    'calculate_step_lengths',
    'calculate_gait_metrics',
    'calculate_torso_stability',
    'calculate_swing_amplitude',
    'calculate_knee_angles',
    
    # 摔倒检测 (YOLO)
    'FallDetector',
    'detect_fall',
    'detect_fall_in_frame',
    'format_fall_warning',
    'get_detector',
]

