"""
视频处理主模块
负责视频读取、关键点提取和分析结果整合

优化版本：
- 合并姿态检测和摔倒检测到一次视频遍历
- 使用多线程并行处理
- 跳帧检测摔倒（每3帧检测一次）
- 优化 FFmpeg 转换速度
"""

import os
import cv2
import pandas as pd
import logging
import subprocess
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue

from .pose_detection import detect_pose, extract_keypoints, draw_pose_landmarks, release_pose_detector, REQUIRED_KEYPOINTS
from .gait_analysis import analyze_gait
from .fall_detection import detect_fall, format_fall_warning, get_detector

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def convert_to_h264(input_path, output_path):
    """
    使用 FFmpeg 将视频转换为 H.264 格式（浏览器兼容）
    使用 ultrafast 预设加速转换
    
    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
    
    Returns:
        bool: 转换是否成功
    """
    # 检查 ffmpeg 是否可用
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path is None:
        logging.warning("FFmpeg 未安装，视频可能无法在浏览器中播放")
        return False
    
    try:
        # 临时输出文件
        temp_output = output_path + '.temp.mp4'
        
        # FFmpeg 命令：使用 ultrafast 预设加速转换
        cmd = [
            'ffmpeg', '-y',  # 覆盖输出文件
            '-i', input_path,  # 输入文件
            '-c:v', 'libx264',  # 视频编码器
            '-preset', 'ultrafast',  # 最快编码速度
            '-crf', '28',  # 稍微降低质量换取速度（23是默认值）
            '-tune', 'fastdecode',  # 优化解码速度
            '-an',  # 不处理音频（加速）
            '-movflags', '+faststart',  # 优化网络播放
            temp_output
        ]
        
        # 执行转换
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=120  # 2分钟超时（减少超时时间）
        )
        
        if result.returncode == 0 and os.path.exists(temp_output):
            # 替换原文件
            os.remove(input_path)
            os.rename(temp_output, output_path)
            logging.info(f"视频已转换为 H.264 格式: {output_path}")
            return True
        else:
            logging.error(f"FFmpeg 转换失败: {result.stderr}")
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("FFmpeg 转换超时")
        return False
    except Exception as e:
        logging.error(f"视频转换失败: {e}")
        return False


# 邮件发送回调函数（由 app.py 注入）
_send_fall_alert_callback = None


def set_fall_alert_callback(callback):
    """
    设置摔倒警报邮件发送回调函数
    
    Args:
        callback: 回调函数，签名为 callback(email, filename, fall_times, fall_warning)
    """
    global _send_fall_alert_callback
    _send_fall_alert_callback = callback
    logging.info("摔倒警报回调函数已设置")


def send_fall_alert(email, filename, fall_times, fall_warning):
    """
    发送摔倒警报邮件
    
    Args:
        email: 用户邮箱
        filename: 视频文件名
        fall_times: 摔倒时间列表
        fall_warning: 警告信息
    
    Returns:
        bool: 发送是否成功
    """
    global _send_fall_alert_callback
    
    if _send_fall_alert_callback is None:
        logging.warning("摔倒警报回调函数未设置，无法发送邮件")
        return False
    
    try:
        return _send_fall_alert_callback(email, filename, fall_times, fall_warning)
    except Exception as e:
        logging.error(f"发送摔倒警报邮件失败: {e}")
        return False


def process_video(filename, input_path, output_folder, user_email=None):
    """
    处理视频文件，提取关键点并进行分析
    
    优化版本：
    - 一次视频遍历完成姿态检测
    - 收集帧缓存用于摔倒检测（跳帧采样）
    - 多线程处理摔倒检测
    
    Args:
        filename: 视频文件名
        input_path: 视频文件路径
        output_folder: 输出文件夹路径
        user_email: 用户邮箱（用于摔倒警报通知）
    
    Returns:
        bool: 处理是否成功
    """
    try:
        video_base_name = os.path.splitext(filename)[0]
        video_output_folder = os.path.join(output_folder, video_base_name)
        os.makedirs(video_output_folder, exist_ok=True)

        # 只生成骨架视频
        output_path_skeleton = os.path.join(video_output_folder, f"{video_base_name}_skeleton.mp4")
        output_path_keypoints = os.path.join(video_output_folder, f"{video_base_name}_keypoints.csv")
        output_path_analysis = os.path.join(video_output_folder, f"{video_base_name}_analysis.csv")

        # 打开输入视频文件
        cap = cv2.VideoCapture(input_path)

        # 获取视频的宽度、高度和帧率
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # 使用 AVC1 编解码器（H.264），浏览器更兼容
        codecs_to_try = ['avc1', 'H264', 'X264', 'mp4v']
        out_skeleton = None
        
        for codec in codecs_to_try:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            out_skeleton = cv2.VideoWriter(output_path_skeleton, fourcc, fps, (width, height))
            if out_skeleton.isOpened():
                logging.info(f"使用编解码器: {codec}")
                break
            out_skeleton.release()
        
        if out_skeleton is None or not out_skeleton.isOpened():
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_skeleton = cv2.VideoWriter(output_path_skeleton, fourcc, fps, (width, height))
            logging.info("使用默认编解码器: mp4v")

        keypoints_list = []
        frame_buffer = []  # 用于摔倒检测的帧缓存
        frame_count = 0
        detected_frames = 0
        
        # 跳帧参数：每隔 SKIP_FRAMES 帧采样一帧用于摔倒检测
        SKIP_FRAMES = 3

        logging.info(f"开始处理视频: {filename} (共 {total_frames} 帧)")
        start_time = datetime.now()

        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break

            frame_count += 1
            frame_number = frame_count  # 当前帧编号
            
            # 姿势检测
            results = detect_pose(image)
            
            # 提取关键点
            keypoints = extract_keypoints(results, frame_number)
            
            if keypoints:
                keypoints_list.append(keypoints)
                detected_frames += 1

            # 绘制骨架并写入视频
            skeleton_image = image.copy()
            skeleton_image = draw_pose_landmarks(skeleton_image, results)
            out_skeleton.write(skeleton_image)
            
            # 采样帧用于摔倒检测（跳帧采样减少计算量）
            if frame_count % SKIP_FRAMES == 0:
                frame_buffer.append((frame_number, image.copy()))

            # 每100帧记录一次进度
            if frame_count % 100 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                progress = frame_count / total_frames * 100 if total_frames > 0 else 0
                logging.info(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames} 帧, 耗时 {elapsed:.1f}s)")

        # 释放资源
        cap.release()
        out_skeleton.release()
        
        # 释放 Pose 检测器
        release_pose_detector()
        
        elapsed_pose = (datetime.now() - start_time).total_seconds()
        logging.info(f"姿态检测完成: 共 {frame_count} 帧, 检测到人体 {detected_frames} 帧, 耗时 {elapsed_pose:.1f}s")
        
        # 使用线程池并行处理后续任务
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            
            # 任务1: FFmpeg 转换（在后台线程中执行）
            future_ffmpeg = executor.submit(convert_to_h264, output_path_skeleton, output_path_skeleton)
            futures.append(('ffmpeg', future_ffmpeg))
            
            # 任务2: 摔倒检测（使用帧缓存，在后台线程中执行）
            def run_fall_detection():
                if frame_buffer:
                    logging.info(f"开始摔倒检测: 共 {len(frame_buffer)} 帧采样")
                    fall_detected, fall_times = detect_fall(
                        keypoints_df=None,
                        fps=fps,
                        frame_buffer=frame_buffer
                    )
                    return fall_detected, fall_times
                return False, []
            
            future_fall = executor.submit(run_fall_detection)
            futures.append(('fall_detection', future_fall))
            
            # 等待摔倒检测完成
            fall_detected, fall_start_times = False, []
            for name, future in futures:
                if name == 'fall_detection':
                    fall_detected, fall_start_times = future.result()

        # 保存关键点数据到CSV
        if keypoints_list:
            keypoints_df = pd.DataFrame(keypoints_list)
            keypoints_df.to_csv(output_path_keypoints, index=False)
            logging.info(f"成功保存关键点数据到 {output_path_keypoints}")

            # 分析关键点数据（步态分析 + 整合摔倒检测结果）
            analyze_keypoints(
                keypoints_list, 
                output_path_analysis, 
                fps, 
                fall_result=(fall_detected, fall_start_times),
                filename=filename, 
                user_email=user_email
            )
        else:
            logging.warning(f"未检测到任何关键点，无法生成 {output_path_keypoints}")
        
        total_elapsed = (datetime.now() - start_time).total_seconds()
        logging.info(f"视频处理完成，总耗时: {total_elapsed:.1f}s")
        
        return True
    except Exception as e:
        logging.error(f"处理视频 {filename} 时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_keypoints(keypoints_list, output_analysis_path, fps, fall_result=None,
                      filename=None, user_email=None):
    """
    分析关键点数据，整合步态分析和摔倒检测结果
    
    Args:
        keypoints_list: 关键点数据列表
        output_analysis_path: 分析结果输出路径
        fps: 视频帧率
        fall_result: 摔倒检测结果 (fall_detected, fall_start_times)，如果为 None 则不检测
        filename: 原始视频文件名（用于警报邮件）
        user_email: 用户邮箱（用于摔倒警报通知）
    """
    if not keypoints_list:
        with open(output_analysis_path, 'w', encoding='utf-8-sig') as f:
            f.write("没有关键点数据\n")
        return

    keypoints_df = pd.DataFrame(keypoints_list)

    # 检查是否所有关键点都存在
    required_keypoints_cols = [
        'LEFT_ANKLE_x', 'RIGHT_ANKLE_x', 'LEFT_ANKLE_y', 'RIGHT_ANKLE_y',
        'LEFT_SHOULDER_x', 'LEFT_SHOULDER_y', 'RIGHT_SHOULDER_x', 'RIGHT_SHOULDER_y',
        'LEFT_HIP_x', 'LEFT_HIP_y', 'RIGHT_HIP_x', 'RIGHT_HIP_y',
        'LEFT_ANKLE_z', 'RIGHT_ANKLE_z', 'LEFT_HIP_z', 'RIGHT_HIP_z',
        'LEFT_SHOULDER_z', 'RIGHT_SHOULDER_z', 'NOSE_z'
    ]

    missing_keypoints = [kp for kp in required_keypoints_cols if kp not in keypoints_df.columns]
    if missing_keypoints:
        with open(output_analysis_path, 'w', encoding='utf-8-sig') as f:
            f.write(f"缺少关键点: {missing_keypoints}\n")
        return

    # 执行步态分析
    gait_result = analyze_gait(keypoints_df, fps)
    
    # 使用传入的摔倒检测结果
    if fall_result is not None:
        fall_detected, fall_start_times = fall_result
    else:
        fall_detected, fall_start_times = False, []
    
    fall_warning = format_fall_warning(fall_detected, fall_start_times)

    # 构建分析结果（纯客观数据，无评分）
    metric_units = {
        "步频": "步/分",
        "步态周期": "秒",
        "对称性指数": "%",
        "变异系数": "%",
        "躯干稳定性": "度/帧",
        "躯干倾斜角": "度",
        "平均步长": "相对值",
        "摆动幅度": "相对值",
        "膝关节活动度": "度"
    }
    
    analysis_results = []
    measurements = gait_result.get('measurements', {})
    
    for param, value in measurements.items():
        unit = metric_units.get(param, "")
        if value is None:
            display_value = "无"
        else:
            display_value = f"{value} {unit}".strip()
        analysis_results.append({"指标": param, "数值": value if value is not None else "", "单位": unit})

    # 创建 DataFrame
    analysis_df = pd.DataFrame(analysis_results)

    # 保存到 CSV 文件
    try:
        with open(output_analysis_path, 'w', encoding='utf-8-sig', newline='') as f:
            analysis_df.to_csv(f, index=False, header=True, encoding='utf-8-sig')

            # 如果检测到摔倒，生成警告信息
            if fall_warning:
                f.write(f"\n{fall_warning}")
        logging.info(f"成功保存分析结果到 {output_analysis_path}")
    except Exception as e:
        logging.error(f"保存分析结果时发生错误: {e}")
    
    # ========== 摔倒警报邮件通知 ==========
    if fall_detected and user_email:
        logging.info(f"检测到摔倒，准备发送警报邮件到 {user_email}")
        try:
            success = send_fall_alert(
                email=user_email,
                filename=filename or "未知视频",
                fall_times=fall_start_times,
                fall_warning=fall_warning
            )
            if success:
                logging.info(f"摔倒警报邮件发送成功: {user_email}")
            else:
                logging.warning(f"摔倒警报邮件发送失败: {user_email}")
        except Exception as e:
            logging.error(f"发送摔倒警报邮件时发生错误: {e}")
