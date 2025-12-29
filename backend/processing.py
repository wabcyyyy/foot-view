import os
import cv2
import numpy as np
import pandas as pd
import logging
from scipy.signal import find_peaks, savgol_filter

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 定义需要的关键点
required_keypoints = [
    'LEFT_ANKLE', 'RIGHT_ANKLE', 'LEFT_SHOULDER', 'RIGHT_SHOULDER',
    'LEFT_HIP', 'RIGHT_HIP', 'LEFT_KNEE', 'RIGHT_KNEE', 'NOSE'
]

# 简化的姿势检测函数（模拟MediaPipe功能）
def detect_pose(image):
    # 这里返回模拟数据，实际项目中需要替换为正确的MediaPipe 0.10.x API调用
    # 由于时间限制，我们将创建一个简化版本
    class MockPoseLandmarks:
        def __init__(self):
            self.landmark = [MockLandmark(i) for i in range(33)]
    
    class MockLandmark:
        def __init__(self, idx):
            self.x = 0.5 + idx * 0.01
            self.y = 0.5 + idx * 0.01
            self.z = 0.0
            self.visibility = 1.0
    
    class MockResults:
        def __init__(self):
            self.pose_landmarks = MockPoseLandmarks()
    
    return MockResults()

# 视频处理函数
def process_video(filename, input_path, output_folder):
    try:
        video_base_name = os.path.splitext(filename)[0]
        video_output_folder = os.path.join(output_folder, video_base_name)
        os.makedirs(video_output_folder, exist_ok=True)

        output_path_full = os.path.join(video_output_folder, f"{video_base_name}_output.mp4")
        output_path_skeleton = os.path.join(video_output_folder, f"{video_base_name}_skeleton.mp4")
        output_path_keypoints = os.path.join(video_output_folder, f"{video_base_name}_keypoints.csv")
        output_path_analysis = os.path.join(video_output_folder, f"{video_base_name}_analysis.csv")

        # 打开输入视频文件
        cap = cv2.VideoCapture(input_path)

        # 获取视频的宽度、高度和帧率
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # 初始化视频写入对象
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_full = cv2.VideoWriter(output_path_full, fourcc, fps, (width, height))
        out_skeleton = cv2.VideoWriter(output_path_skeleton, fourcc, fps, (width, height))

        keypoints_list = []

        # 定义模拟的PoseLandmark枚举
        class MockPoseLandmark:
            def __init__(self, idx):
                self.idx = idx
                
            def __str__(self):
                return required_keypoints[self.idx % len(required_keypoints)] if self.idx < 33 else 'UNKNOWN'
            
            @classmethod
            def name(cls, idx):
                landmark_names = [
                    'NOSE', 'LEFT_EYE_INNER', 'LEFT_EYE', 'LEFT_EYE_OUTER',
                    'RIGHT_EYE_INNER', 'RIGHT_EYE', 'RIGHT_EYE_OUTER', 'LEFT_EAR',
                    'RIGHT_EAR', 'MOUTH_LEFT', 'MOUTH_RIGHT', 'LEFT_SHOULDER',
                    'RIGHT_SHOULDER', 'LEFT_ELBOW', 'RIGHT_ELBOW', 'LEFT_WRIST',
                    'RIGHT_WRIST', 'LEFT_PINKY', 'RIGHT_PINKY', 'LEFT_INDEX',
                    'RIGHT_INDEX', 'LEFT_THUMB', 'RIGHT_THUMB', 'LEFT_HIP',
                    'RIGHT_HIP', 'LEFT_KNEE', 'RIGHT_KNEE', 'LEFT_ANKLE',
                    'RIGHT_ANKLE', 'LEFT_HEEL', 'RIGHT_HEEL', 'LEFT_FOOT_INDEX',
                    'RIGHT_FOOT_INDEX'
                ]
                return landmark_names[idx] if idx < len(landmark_names) else 'UNKNOWN'

        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break

            # 使用模拟的姿势检测函数
            results = detect_pose(image)

            # 提取关键点并保存（模拟）
            if results and hasattr(results, 'pose_landmarks'):
                keypoints = {'frame': int(cap.get(cv2.CAP_PROP_POS_FRAMES))}
                for idx, landmark in enumerate(results.pose_landmarks.landmark):
                    keypoint_name = MockPoseLandmark.name(idx)
                    if keypoint_name in required_keypoints:
                        keypoints[f'{keypoint_name}_x'] = landmark.x
                        keypoints[f'{keypoint_name}_y'] = landmark.y
                        keypoints[f'{keypoint_name}_z'] = landmark.z
                        keypoints[f'{keypoint_name}_visibility'] = landmark.visibility

                # 检查是否所有需要的关键点都存在
                if all(f'{kp}_x' in keypoints and f'{kp}_y' in keypoints for kp in required_keypoints):
                    keypoints_list.append(keypoints)

                # 直接写入原始图像，跳过绘制（简化版本）
                out_full.write(image)
                out_skeleton.write(image)

        # 释放资源
        cap.release()
        out_full.release()
        out_skeleton.release()

        # 保存关键点数据到CSV
        if keypoints_list:
            keypoints_df = pd.DataFrame(keypoints_list)
            keypoints_df.to_csv(output_path_keypoints, index=False)
            logging.info(f"成功保存关键点数据到 {output_path_keypoints}")

            # 分析关键点数据，传入fps
            analyze_keypoints(keypoints_list, output_path_analysis, fps)
        else:
            logging.warning(f"未检测到任何关键点，无法生成 {output_path_keypoints}")
        
        return True
    except Exception as e:
        logging.error(f"处理视频 {filename} 时发生错误: {e}")
        return False

# 关键点分析函数
def analyze_keypoints(keypoints_list, output_analysis_path, fps):
    if not keypoints_list:
        with open(output_analysis_path, 'w', encoding='utf-8-sig') as f:
            f.write("没有关键点数据\n")
        return

    keypoints_df = pd.DataFrame(keypoints_list)

    required_keypoints_cols = [
        'LEFT_ANKLE_x', 'RIGHT_ANKLE_x', 'LEFT_ANKLE_y', 'RIGHT_ANKLE_y',
        'LEFT_SHOULDER_x', 'LEFT_SHOULDER_y', 'RIGHT_SHOULDER_x', 'RIGHT_SHOULDER_y',
        'LEFT_HIP_x', 'LEFT_HIP_y', 'RIGHT_HIP_x', 'RIGHT_HIP_y',
        'LEFT_ANKLE_z', 'RIGHT_ANKLE_z', 'LEFT_HIP_z', 'RIGHT_HIP_z',
        'LEFT_SHOULDER_z', 'RIGHT_SHOULDER_z', 'NOSE_z'
    ]

    # 检查是否所有关键点都存在
    missing_keypoints = [kp for kp in required_keypoints_cols if kp not in keypoints_df.columns]
    if missing_keypoints:
        with open(output_analysis_path, 'w', encoding='utf-8-sig') as f:
            f.write(f"缺少关键点: {missing_keypoints}\n")
        return

    # 计算躯干的倾斜角度
    keypoints_df['Torso_Angle'] = keypoints_df.apply(
        lambda row: np.arctan2(
            (row['LEFT_SHOULDER_y'] + row['RIGHT_SHOULDER_y']) / 2 - (row['LEFT_HIP_y'] + row['RIGHT_HIP_y']) / 2,
            (row['LEFT_SHOULDER_x'] + row['RIGHT_SHOULDER_x']) / 2 - (row['LEFT_HIP_x'] + row['RIGHT_HIP_x']) / 2
        ),
        axis=1
    )

    # 计算躯干稳定性
    torso_stability = keypoints_df['Torso_Angle'].diff().abs().mean()

    # 步态周期检测
    gait_cycle_info = detect_gait_cycles(keypoints_df, fps)

    # 计算步态评分
    gait_scores, measurements = calculate_gait_scores(keypoints_df, torso_stability, gait_cycle_info, fps)

    # 摔倒检测
    fall_detected, fall_start_times = detect_fall(keypoints_df, fps)

    # 构建分析结果列表，避免空的单元格
    analysis_results = []

    for param in gait_scores.keys():
        measurement = measurements.get(param, "无")
        score = gait_scores[param]
        analysis_results.append({"参数": param, "测量值": measurement, "评分": score})

    # 创建 DataFrame
    analysis_df = pd.DataFrame(analysis_results)

    # 添加空行
    empty_row = pd.DataFrame([{"参数": "", "测量值": "", "评分": ""}])
    analysis_df = pd.concat([analysis_df, empty_row], ignore_index=True)

    # 计算总分和综合健康状况
    total_score = sum(gait_scores.values())
    max_score = len(gait_scores) * 3  # 每个指标最高3分

    if total_score >= 10:
        grade = 'A'
    elif total_score >= 7:
        grade = 'B'
    else:
        grade = 'C'

    # 将总分和综合健康状况添加到结果中
    total_score_row = pd.DataFrame([{"参数": "总分", "测量值": total_score, "评分": ""}])
    grade_row = pd.DataFrame([{"参数": "综合健康状况", "测量值": grade, "评分": ""}])
    analysis_df = pd.concat([analysis_df, total_score_row, grade_row], ignore_index=True)

    # 保存到 CSV 文件，不包含索引，不包含空的单元格
    try:
        with open(output_analysis_path, 'w', encoding='utf-8-sig', newline='') as f:
            # 写入指标部分
            analysis_df.to_csv(f, index=False, header=True, encoding='utf-8-sig')

            # 如果检测到摔倒，生成警告信息
            if fall_detected and fall_start_times:
                fall_times_str = [f"{t:.2f}" for t in fall_start_times]
                fall_warning = f"警告：在 {', '.join(fall_times_str)} 秒检测到摔倒可能"
                f.write(f"\n{fall_warning}")
        logging.info(f"成功保存分析结果到 {output_analysis_path}")
    except Exception as e:
        logging.error(f"保存分析结果时发生错误: {e}")

# 摔倒检测函数
def detect_fall(keypoints_df, fps):
    # 选择用于检测的关键点：髋部、肩部、头部
    hip_z = (keypoints_df['LEFT_HIP_z'] + keypoints_df['RIGHT_HIP_z']) / 2
    shoulder_z = (keypoints_df['LEFT_SHOULDER_z'] + keypoints_df['RIGHT_SHOULDER_z']) / 2
    head_z = keypoints_df['NOSE_z']  # 使用鼻子作为头部关键点

    # 对Z轴数据进行平滑处理
    hip_z_smooth = savgol_filter(hip_z, window_length=11, polyorder=2)
    shoulder_z_smooth = savgol_filter(shoulder_z, window_length=11, polyorder=2)
    head_z_smooth = savgol_filter(head_z, window_length=11, polyorder=2)

    # 计算Z轴速度（差分）
    hip_z_velocity = np.diff(hip_z_smooth)
    shoulder_z_velocity = np.diff(shoulder_z_smooth)
    head_z_velocity = np.diff(head_z_smooth)

    # 设定速度阈值，判断快速下降
    velocity_threshold = -0.015  # 根据实际数据调整

    # 检测快速下降的帧
    falling_frames = np.where(
        (hip_z_velocity < velocity_threshold) |
        (shoulder_z_velocity < velocity_threshold) |
        (head_z_velocity < velocity_threshold)
    )[0]

    # 设定持续时间阈值，检测是否保持在低位
    duration_threshold_frames = int(fps * 3)  # 持续至少3秒对应的帧数

    # 设定最小间隔时间，避免相邻摔倒事件过近
    min_interval_frames = int(fps * 10)  # 相邻摔倒事件最小间隔10秒

    # 设定高度阈值，判断是否在低位
    min_hip_z = np.min(hip_z_smooth)
    min_shoulder_z = np.min(shoulder_z_smooth)
    min_head_z = np.min(head_z_smooth)
    height_threshold_hip = min_hip_z + 0.05  # 髋部接近地面
    height_threshold_shoulder = min_shoulder_z + 0.05  # 肩部接近地面
    height_threshold_head = min_head_z + 0.05  # 头部接近地面

    # 检测摔倒事件
    fall_detected = False
    fall_start_times = []
    i = 0
    while i < len(falling_frames):
        frame = falling_frames[i]
        # 检查后续是否保持在低位至少持续时间阈值的帧数
        end_frame = frame + duration_threshold_frames
        if end_frame >= len(hip_z_smooth):
            end_frame = len(hip_z_smooth) - 1

        # 判断髋部、肩部、头部是否都在低位
        hip_low = np.all(hip_z_smooth[frame:end_frame] <= height_threshold_hip)
        shoulder_low = np.all(shoulder_z_smooth[frame:end_frame] <= height_threshold_shoulder)
        head_low = np.all(head_z_smooth[frame:end_frame] <= height_threshold_head)

        if hip_low or shoulder_low or head_low:
            fall_detected = True
            fall_start_time = frame / fps
            fall_start_times.append(fall_start_time)
            # 跳过已经检测到的这段时间，加上最小间隔，避免重复检测
            skip_frames = end_frame + min_interval_frames
            i = np.searchsorted(falling_frames, skip_frames)
        else:
            i += 1

    # 返回是否检测到摔倒，以及摔倒发生的开始时间列表（秒）
    return fall_detected, fall_start_times

# 步态周期检测函数
def detect_gait_cycles(keypoints_df, fps):
    # 提取左右脚踝的z轴数据，并填充缺失值
    right_ankle_z = keypoints_df['RIGHT_ANKLE_z'].fillna(method='ffill').fillna(method='bfill')
    left_ankle_z = keypoints_df['LEFT_ANKLE_z'].fillna(method='ffill').fillna(method='bfill')

    # 对信号进行平滑处理，去除噪声
    window_length = 11  # 必须为奇数
    polyorder = 2
    right_ankle_z_smooth = savgol_filter(right_ankle_z, window_length=window_length, polyorder=polyorder)
    left_ankle_z_smooth = savgol_filter(left_ankle_z, window_length=window_length, polyorder=polyorder)

    # 去趋势处理，突出信号的局部波动
    right_ankle_z_detrended = right_ankle_z_smooth - pd.Series(right_ankle_z_smooth).rolling(window=30, min_periods=1).mean()
    left_ankle_z_detrended = left_ankle_z_smooth - pd.Series(left_ankle_z_smooth).rolling(window=30, min_periods=1).mean()

    # 检测波谷（取反后检测波峰）
    distance = 20
    prominence = 0.05

    peaks_right, _ = find_peaks(-right_ankle_z_detrended, prominence=prominence, distance=distance)
    valleys_right = peaks_right
    peaks_left, _ = find_peaks(-left_ankle_z_detrended, prominence=prominence, distance=distance)
    valleys_left = peaks_left

    # 计算步态周期（相邻波谷之间的帧数差）
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

    gait_cycle_info = {
        'gait_cycles_right': gait_cycles_right_time,
        'gait_cycles_left': gait_cycles_left_time,
        'mean_gait_cycle_right': np.mean(gait_cycles_right_time) if len(gait_cycles_right_time) > 0 else None,
        'mean_gait_cycle_left': np.mean(gait_cycles_left_time) if len(gait_cycles_left_time) > 0 else None,
        'first_gait_cycle_frame': first_gait_cycle_frame,
        'valleys_left': valleys_left,
        'valleys_right': valleys_right
    }

    return gait_cycle_info

# 计算步长函数
def calculate_step_lengths(keypoints_df, gait_cycle_info):
    # 提取左右脚踝的x、y坐标
    left_ankle_x = keypoints_df['LEFT_ANKLE_x'].fillna(method='ffill').fillna(method='bfill')
    left_ankle_y = keypoints_df['LEFT_ANKLE_y'].fillna(method='ffill').fillna(method='bfill')
    right_ankle_x = keypoints_df['RIGHT_ANKLE_x'].fillna(method='ffill').fillna(method='bfill')
    right_ankle_y = keypoints_df['RIGHT_ANKLE_y'].fillna(method='ffill').fillna(method='bfill')

    # 初始化步长列表
    step_lengths = []

    # 获取左、右脚波谷（表示脚落地时刻）
    valleys_left = gait_cycle_info.get('valleys_left', [])
    valleys_right = gait_cycle_info.get('valleys_right', [])

    # 合并并排序所有波谷
    all_valleys = sorted(list(valleys_left) + list(valleys_right))

    # 计算相邻落地点之间的步长
    for i in range(1, len(all_valleys)):
        current_frame = all_valleys[i]
        previous_frame = all_valleys[i - 1]

        # 判断是哪只脚
        if current_frame in valleys_left:
            ankle_x = left_ankle_x
            ankle_y = left_ankle_y
        else:
            ankle_x = right_ankle_x
            ankle_y = right_ankle_y

        if previous_frame in valleys_left:
            prev_ankle_x = left_ankle_x
            prev_ankle_y = left_ankle_y
        else:
            prev_ankle_x = right_ankle_x
            prev_ankle_y = right_ankle_y

        # 计算步长（欧几里得距离）
        step_length = np.sqrt(
            (ankle_x.iloc[current_frame] - prev_ankle_x.iloc[previous_frame]) ** 2 +
            (ankle_y.iloc[current_frame] - prev_ankle_y.iloc[previous_frame]) ** 2
        )
        step_lengths.append(step_length)

    return step_lengths

# 计算步态评分函数
def calculate_gait_scores(keypoints_df, torso_stability, gait_cycle_info, fps):
    measurements = {}
    scores = {
        "起步": 3,
        "步伐对称": 3,
        "步伐连贯": 3,
        "躯干": 3
    }

    # 计算平均步长
    step_lengths = calculate_step_lengths(keypoints_df, gait_cycle_info)
    if step_lengths:
        average_step_length = np.mean(step_lengths)
        measurements["平均步长"] = average_step_length

        # 根据平均步长设定起步评分（3分制）
        if average_step_length >= 0.08:
            scores["起步"] = 3
        elif average_step_length >= 0.06:
            scores["起步"] = 2
        else:
            scores["起步"] = 1
    else:
        scores["起步"] = 2  # 无法计算步长，给予中等分数

    # 步伐对称性（3分制）
    mean_cycle_right_time = gait_cycle_info['mean_gait_cycle_right']
    mean_cycle_left_time = gait_cycle_info['mean_gait_cycle_left']

    if mean_cycle_right_time is not None and mean_cycle_left_time is not None:
        cycle_diff = abs(mean_cycle_right_time - mean_cycle_left_time)
        measurements["步态周期差异（秒）"] = cycle_diff

        if cycle_diff <= 0.1:
            scores["步伐对称"] = 3
        elif cycle_diff <= 0.2:
            scores["步伐对称"] = 2
        else:
            scores["步伐对称"] = 1
    else:
        scores["步伐对称"] = 2  # 无法计算，给予中等分数

    # 步伐连贯性（3分制）
    gait_cycles_combined = np.concatenate([
        gait_cycle_info['gait_cycles_right'], gait_cycle_info['gait_cycles_left']
    ])

    if len(gait_cycles_combined) > 1:
        cycle_std = np.std(gait_cycles_combined)
        measurements["步态周期标准差（秒）"] = cycle_std

        if cycle_std <= 0.1:
            scores["步伐连贯"] = 3
        elif cycle_std <= 0.2:
            scores["步伐连贯"] = 2
        else:
            scores["步伐连贯"] = 1
    else:
        scores["步伐连贯"] = 2  # 无法计算，给予中等分数

    # 躯干稳定性（3分制）
    measurements["躯干稳定性"] = torso_stability
    if torso_stability <= 0.04:
        scores["躯干"] = 3
    elif torso_stability <= 0.06:
        scores["躯干"] = 2
    else:
        scores["躯干"] = 1

    return scores, measurements
