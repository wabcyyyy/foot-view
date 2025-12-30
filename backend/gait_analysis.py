"""
步态分析模块
负责步态周期检测、步长计算和步态评分

基于 2D 姿态估计（YOLO Pose）的步态分析指标：
1. 时序指标：步频、步态周期、对称性、连贯性
2. 空间指标：相对步长、摆动幅度
3. 角度指标：膝关节角度、躯干倾斜
"""

import numpy as np
import pandas as pd
from scipy import signal


def calculate_angle(p1, p2, p3):
    """
    计算三个点形成的角度（p2 为顶点）
    
    Args:
        p1, p2, p3: 三个点的坐标 (x, y)
    
    Returns:
        float: 角度（度数）
    """
    v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
    v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    cos_angle = np.clip(cos_angle, -1, 1)
    angle = np.arccos(cos_angle)
    return np.degrees(angle)


def detect_gait_cycles(keypoints_df, fps):
    """
    检测步态周期（基于脚踝 y 坐标的周期性变化）
    
    Args:
        keypoints_df: 包含关键点数据的 DataFrame
        fps: 视频帧率
    
    Returns:
        dict: 包含步态周期信息的字典
    """
    # 使用 y 坐标（垂直方向）来检测步态周期
    # 当人行走时，脚踝的 y 坐标会有周期性变化：脚抬起时 y 变小，落地时 y 变大
    right_ankle_y = keypoints_df['RIGHT_ANKLE_y'].ffill().bfill()
    left_ankle_y = keypoints_df['LEFT_ANKLE_y'].ffill().bfill()

    # 对信号进行平滑处理，去除噪声
    window_length = 11  # 必须为奇数
    polyorder = 2
    
    # 确保数据长度足够进行平滑处理
    if len(right_ankle_y) < window_length:
        window_length = max(3, len(right_ankle_y) if len(right_ankle_y) % 2 == 1 else len(right_ankle_y) - 1)
    
    if window_length < 3:
        # 数据太少，无法进行步态分析
        return {
            'gait_cycles_right': np.array([]),
            'gait_cycles_left': np.array([]),
            'mean_gait_cycle_right': None,
            'mean_gait_cycle_left': None,
            'first_gait_cycle_frame': None,
            'valleys_left': np.array([]),
            'valleys_right': np.array([]),
            'cadence': None
        }
    
    right_ankle_y_smooth = signal.savgol_filter(right_ankle_y, window_length=window_length, polyorder=polyorder)
    left_ankle_y_smooth = signal.savgol_filter(left_ankle_y, window_length=window_length, polyorder=polyorder)

    # 去趋势处理，突出信号的局部波动
    right_ankle_y_detrended = right_ankle_y_smooth - pd.Series(right_ankle_y_smooth).rolling(window=30, min_periods=1).mean()
    left_ankle_y_detrended = left_ankle_y_smooth - pd.Series(left_ankle_y_smooth).rolling(window=30, min_periods=1).mean()

    # 检测波峰（y 坐标最大值 = 脚落地时刻）
    distance = 10  # 最小间隔帧数
    prominence = 0.005  # 适应归一化坐标

    peaks_right, _ = signal.find_peaks(right_ankle_y_detrended, prominence=prominence, distance=distance)
    valleys_right = peaks_right
    peaks_left, _ = signal.find_peaks(left_ankle_y_detrended, prominence=prominence, distance=distance)
    valleys_left = peaks_left

    # 计算步态周期（相邻波峰之间的帧数差）
    gait_cycles_right = np.diff(valleys_right)
    gait_cycles_left = np.diff(valleys_left)

    # 转换步态周期为时间（秒）
    gait_cycles_right_time = gait_cycles_right / fps
    gait_cycles_left_time = gait_cycles_left / fps

    # 检测第一个完整的步态周期的起始帧
    if len(valleys_right) > 1:
        first_gait_cycle_frame = valleys_right[1]
    elif len(valleys_left) > 1:
        first_gait_cycle_frame = valleys_left[1]
    else:
        first_gait_cycle_frame = None

    # 计算步频（步/分钟）
    total_steps = len(valleys_left) + len(valleys_right)
    total_time = len(keypoints_df) / fps
    cadence = (total_steps / total_time) * 60 if total_time > 0 else None

    gait_cycle_info = {
        'gait_cycles_right': gait_cycles_right_time,
        'gait_cycles_left': gait_cycles_left_time,
        'mean_gait_cycle_right': np.mean(gait_cycles_right_time) if len(gait_cycles_right_time) > 0 else None,
        'mean_gait_cycle_left': np.mean(gait_cycles_left_time) if len(gait_cycles_left_time) > 0 else None,
        'first_gait_cycle_frame': first_gait_cycle_frame,
        'valleys_left': valleys_left,
        'valleys_right': valleys_right,
        'cadence': cadence
    }

    return gait_cycle_info


def calculate_step_lengths(keypoints_df, gait_cycle_info):
    """
    计算步长（使用水平方向 x 坐标，更能反映实际步长）
    
    Args:
        keypoints_df: 包含关键点数据的 DataFrame
        gait_cycle_info: 步态周期信息
    
    Returns:
        list: 步长列表（归一化坐标单位）
    """
    # 提取左右脚踝的x坐标
    left_ankle_x = keypoints_df['LEFT_ANKLE_x'].ffill().bfill()
    right_ankle_x = keypoints_df['RIGHT_ANKLE_x'].ffill().bfill()

    # 初始化步长列表
    step_lengths = []

    # 获取左、右脚波峰（表示脚落地时刻）
    valleys_left = list(gait_cycle_info.get('valleys_left', []))
    valleys_right = list(gait_cycle_info.get('valleys_right', []))

    # 合并并排序所有落地时刻
    all_valleys = sorted(valleys_left + valleys_right)

    # 计算相邻落地点之间的步长（主要看 x 方向位移）
    for i in range(1, len(all_valleys)):
        current_frame = all_valleys[i]
        previous_frame = all_valleys[i - 1]
        
        # 确保索引在范围内
        if current_frame >= len(left_ankle_x) or previous_frame >= len(left_ankle_x):
            continue

        # 判断是哪只脚
        if current_frame in valleys_left:
            current_x = left_ankle_x.iloc[current_frame]
        else:
            current_x = right_ankle_x.iloc[current_frame]

        if previous_frame in valleys_left:
            prev_x = left_ankle_x.iloc[previous_frame]
        else:
            prev_x = right_ankle_x.iloc[previous_frame]

        # 步长 = 水平方向的位移（取绝对值）
        step_length = abs(current_x - prev_x)
        if step_length > 0.001:  # 过滤掉太小的噪声
            step_lengths.append(step_length)

    return step_lengths


def calculate_swing_amplitude(keypoints_df, gait_cycle_info):
    """
    计算腿部摆动幅度（脚踝 y 坐标的变化范围）
    
    Args:
        keypoints_df: 包含关键点数据的 DataFrame
        gait_cycle_info: 步态周期信息
    
    Returns:
        dict: 左右腿摆动幅度
    """
    right_ankle_y = keypoints_df['RIGHT_ANKLE_y'].ffill().bfill()
    left_ankle_y = keypoints_df['LEFT_ANKLE_y'].ffill().bfill()
    
    # 计算 y 坐标的变化范围作为摆动幅度
    right_swing = right_ankle_y.max() - right_ankle_y.min()
    left_swing = left_ankle_y.max() - left_ankle_y.min()
    
    return {
        'right_swing': right_swing,
        'left_swing': left_swing,
        'mean_swing': (right_swing + left_swing) / 2
    }


def calculate_knee_angles(keypoints_df):
    """
    计算膝关节角度变化
    
    Args:
        keypoints_df: 包含关键点数据的 DataFrame
    
    Returns:
        dict: 膝关节角度统计
    """
    left_knee_angles = []
    right_knee_angles = []
    
    for _, row in keypoints_df.iterrows():
        # 左膝角度：髋-膝-踝
        left_hip = (row['LEFT_HIP_x'], row['LEFT_HIP_y'])
        left_knee = (row['LEFT_KNEE_x'], row['LEFT_KNEE_y'])
        left_ankle = (row['LEFT_ANKLE_x'], row['LEFT_ANKLE_y'])
        
        # 右膝角度：髋-膝-踝
        right_hip = (row['RIGHT_HIP_x'], row['RIGHT_HIP_y'])
        right_knee = (row['RIGHT_KNEE_x'], row['RIGHT_KNEE_y'])
        right_ankle = (row['RIGHT_ANKLE_x'], row['RIGHT_ANKLE_y'])
        
        left_angle = calculate_angle(left_hip, left_knee, left_ankle)
        right_angle = calculate_angle(right_hip, right_knee, right_ankle)
        
        if not np.isnan(left_angle):
            left_knee_angles.append(left_angle)
        if not np.isnan(right_angle):
            right_knee_angles.append(right_angle)
    
    return {
        'left_knee_mean': np.mean(left_knee_angles) if left_knee_angles else None,
        'right_knee_mean': np.mean(right_knee_angles) if right_knee_angles else None,
        'left_knee_range': np.ptp(left_knee_angles) if left_knee_angles else None,
        'right_knee_range': np.ptp(right_knee_angles) if right_knee_angles else None
    }


def calculate_torso_stability(keypoints_df):
    """
    计算躯干稳定性（躯干倾斜角度的变化程度）
    
    Args:
        keypoints_df: 包含关键点数据的 DataFrame
    
    Returns:
        dict: 躯干稳定性相关指标
    """
    keypoints_df = keypoints_df.copy()
    
    # 计算躯干的倾斜角度（相对于垂直线）
    def calc_torso_angle(row):
        shoulder_mid_x = (row['LEFT_SHOULDER_x'] + row['RIGHT_SHOULDER_x']) / 2
        shoulder_mid_y = (row['LEFT_SHOULDER_y'] + row['RIGHT_SHOULDER_y']) / 2
        hip_mid_x = (row['LEFT_HIP_x'] + row['RIGHT_HIP_x']) / 2
        hip_mid_y = (row['LEFT_HIP_y'] + row['RIGHT_HIP_y']) / 2
        
        # 计算与垂直线的夹角
        dx = shoulder_mid_x - hip_mid_x
        dy = shoulder_mid_y - hip_mid_y
        
        # 角度：与垂直线（dy 方向）的夹角
        angle = np.degrees(np.arctan2(abs(dx), abs(dy)))
        return angle
    
    keypoints_df['Torso_Angle'] = keypoints_df.apply(calc_torso_angle, axis=1)
    
    # 计算躯干稳定性指标
    torso_mean_angle = keypoints_df['Torso_Angle'].mean()  # 平均倾斜角
    torso_angle_std = keypoints_df['Torso_Angle'].std()    # 角度变化标准差
    torso_angle_change = keypoints_df['Torso_Angle'].diff().abs().mean()  # 帧间变化
    
    return {
        'mean_angle': torso_mean_angle,      # 平均躯干倾斜角度（度）
        'angle_std': torso_angle_std,        # 角度标准差
        'stability': torso_angle_change      # 稳定性（越小越稳定）
    }


def calculate_gait_metrics(keypoints_df, torso_info, gait_cycle_info, fps):
    """
    计算步态客观指标（纯数据，无评分）
    
    指标体系：
    1. 时序指标：步频、步态周期、对称性指数、变异系数
    2. 空间指标：步长、摆动幅度
    3. 角度指标：膝关节活动度、躯干倾斜
    
    Args:
        keypoints_df: 包含关键点数据的 DataFrame
        torso_info: 躯干稳定性信息字典
        gait_cycle_info: 步态周期信息
        fps: 视频帧率
    
    Returns:
        tuple: (测量值字典, 是否检测到有效步态)
    """
    measurements = {}
    
    # 检查是否有足够的步态周期数据
    has_valid_gait = False
    valleys_left = gait_cycle_info.get('valleys_left', [])
    valleys_right = gait_cycle_info.get('valleys_right', [])
    
    # 如果左右脚都有至少2个波峰点（表示检测到步态周期）
    if len(valleys_left) >= 2 or len(valleys_right) >= 2:
        has_valid_gait = True

    # ========== 1. 步频（步/分钟） ==========
    cadence = gait_cycle_info.get('cadence')
    if cadence is not None and has_valid_gait:
        measurements["步频"] = round(cadence, 1)
    else:
        measurements["步频"] = None

    # ========== 2. 步态周期（秒） ==========
    mean_cycle_right = gait_cycle_info.get('mean_gait_cycle_right')
    mean_cycle_left = gait_cycle_info.get('mean_gait_cycle_left')
    
    if mean_cycle_right is not None and mean_cycle_left is not None and has_valid_gait:
        avg_cycle = (mean_cycle_right + mean_cycle_left) / 2
        measurements["步态周期"] = round(avg_cycle, 3)
    else:
        measurements["步态周期"] = None

    # ========== 3. 对称性指数（%，越小越对称） ==========
    if mean_cycle_right is not None and mean_cycle_left is not None and has_valid_gait:
        avg_cycle = (mean_cycle_right + mean_cycle_left) / 2
        symmetry_index = abs(mean_cycle_right - mean_cycle_left) / avg_cycle * 100 if avg_cycle > 0 else 0
        measurements["对称性指数"] = round(symmetry_index, 1)
    else:
        measurements["对称性指数"] = None

    # ========== 4. 变异系数（%，越小越稳定） ==========
    gait_cycles_right = gait_cycle_info.get('gait_cycles_right', np.array([]))
    gait_cycles_left = gait_cycle_info.get('gait_cycles_left', np.array([]))
    
    if len(gait_cycles_right) > 0 or len(gait_cycles_left) > 0:
        gait_cycles_combined = np.concatenate([gait_cycles_right, gait_cycles_left])
    else:
        gait_cycles_combined = np.array([])

    if len(gait_cycles_combined) > 1 and has_valid_gait:
        cycle_mean = np.mean(gait_cycles_combined)
        cycle_std = np.std(gait_cycles_combined)
        cv = (cycle_std / cycle_mean * 100) if cycle_mean > 0 else 0
        measurements["变异系数"] = round(cv, 1)
    else:
        measurements["变异系数"] = None

    # ========== 5. 躯干稳定性（度/帧，越小越稳定） ==========
    if torso_info is not None:
        stability = torso_info.get('stability')
        mean_angle = torso_info.get('mean_angle')
        
        if stability is not None and not np.isnan(stability):
            measurements["躯干稳定性"] = round(stability, 3)
            measurements["躯干倾斜角"] = round(mean_angle, 1) if mean_angle and not np.isnan(mean_angle) else None
        else:
            measurements["躯干稳定性"] = None
            measurements["躯干倾斜角"] = None
    else:
        measurements["躯干稳定性"] = None
        measurements["躯干倾斜角"] = None

    # ========== 6. 步长（相对值） ==========
    step_lengths = calculate_step_lengths(keypoints_df, gait_cycle_info)
    if step_lengths:
        measurements["平均步长"] = round(np.mean(step_lengths), 4)
    else:
        measurements["平均步长"] = None
    
    # ========== 7. 摆动幅度（相对值） ==========
    swing_info = calculate_swing_amplitude(keypoints_df, gait_cycle_info)
    if swing_info['mean_swing'] > 0:
        measurements["摆动幅度"] = round(swing_info['mean_swing'], 4)
    else:
        measurements["摆动幅度"] = None
    
    # ========== 8. 膝关节活动度（度） ==========
    knee_info = calculate_knee_angles(keypoints_df)
    if knee_info['left_knee_range'] is not None and knee_info['right_knee_range'] is not None:
        measurements["膝关节活动度"] = round(
            (knee_info['left_knee_range'] + knee_info['right_knee_range']) / 2, 1
        )
    else:
        measurements["膝关节活动度"] = None

    return measurements, has_valid_gait


def analyze_gait(keypoints_df, fps):
    """
    执行完整的步态分析（纯客观数据，无评分）
    
    基于 2D 姿态估计的步态测量，包含：
    - 步频（步/分钟）
    - 步态周期（秒）
    - 对称性指数（%）
    - 变异系数（%）
    - 躯干稳定性（度/帧）
    - 平均步长（相对值）
    - 摆动幅度（相对值）
    - 膝关节活动度（度）
    
    Args:
        keypoints_df: 包含关键点数据的 DataFrame
        fps: 视频帧率
    
    Returns:
        dict: 包含分析结果的字典
    """
    # 计算躯干稳定性
    torso_info = calculate_torso_stability(keypoints_df)
    
    # 步态周期检测
    gait_cycle_info = detect_gait_cycles(keypoints_df, fps)
    
    # 计算步态指标（纯数据）
    measurements, has_valid_gait = calculate_gait_metrics(
        keypoints_df, torso_info, gait_cycle_info, fps
    )
    
    return {
        'measurements': measurements,
        'has_valid_gait': has_valid_gait,
        'torso_info': torso_info,
        'gait_cycle_info': gait_cycle_info
    }

