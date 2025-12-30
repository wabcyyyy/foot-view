"""
摔倒检测模块
使用两阶段检测：
1. 第一阶段：COCO 预训练模型检测人体
2. 第二阶段：摔倒检测模型检测摔倒，通过 IoU 匹配关联到人体

这样可以避免将非人类物体误检为人
"""

import os
import logging
from pathlib import Path

import cv2
import numpy as np

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 模型路径配置
MODEL_DIR = Path(__file__).parent / "models"
FALL_DETECTION_MODEL = MODEL_DIR / "fall_detection.pt"  # 摔倒检测模型
PERSON_DETECTION_MODEL = "yolov8n.pt"  # COCO 预训练模型（自动下载）


def calculate_iou(box1, box2):
    """
    计算两个边界框的 IoU（交并比）
    
    Args:
        box1, box2: [x1, y1, x2, y2] 格式的边界框
    
    Returns:
        float: IoU 值 (0-1)
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    union = area1 + area2 - intersection
    
    if union <= 0:
        return 0.0
    
    return intersection / union


class FallDetector:
    """
    摔倒检测器 - 两阶段检测 + IoU 匹配
    
    第一阶段：使用 COCO 预训练模型检测人体（准确区分人与非人）
    第二阶段：使用摔倒检测模型检测摔倒，通过 IoU 匹配关联
    """
    
    def __init__(self, 
                 fall_model_path=None, 
                 person_model_path=None,
                 confidence_threshold=0.5,
                 person_confidence=0.5,
                 fall_confidence=0.6,  # 摔倒检测需要更高置信度
                 iou_threshold=0.3,    # IoU 匹配阈值
                 use_two_stage=True):
        """
        初始化摔倒检测器
        
        Args:
            fall_model_path: 摔倒检测模型路径
            person_model_path: 人体检测模型路径（COCO 预训练）
            confidence_threshold: 通用置信度阈值（向后兼容）
            person_confidence: 人体检测置信度阈值
            fall_confidence: 摔倒检测置信度阈值（更高以减少误报）
            iou_threshold: IoU 匹配阈值
            use_two_stage: 是否使用两阶段检测（推荐）
        """
        self.person_confidence = person_confidence
        self.fall_confidence = fall_confidence
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.use_two_stage = use_two_stage
        
        self.fall_model = None
        self.person_model = None
        
        self.fall_model_path = fall_model_path or FALL_DETECTION_MODEL
        self.person_model_path = person_model_path or PERSON_DETECTION_MODEL
        
        self._load_models()
    
    def _load_models(self):
        """加载模型"""
        try:
            from ultralytics import YOLO
            
            # 加载摔倒检测模型
            if os.path.exists(self.fall_model_path):
                logging.info(f"加载摔倒检测模型: {self.fall_model_path}")
                self.fall_model = YOLO(str(self.fall_model_path))
                logging.info(f"摔倒检测模型类别: {self.fall_model.names}")
            else:
                logging.warning(f"摔倒检测模型不存在: {self.fall_model_path}")
            
            # 加载人体检测模型（两阶段模式）
            if self.use_two_stage:
                logging.info(f"加载人体检测模型: {self.person_model_path}")
                self.person_model = YOLO(self.person_model_path)
                logging.info("人体检测模型加载成功（COCO 预训练）")
                
        except ImportError:
            logging.error("未安装 ultralytics，请运行: pip install ultralytics")
        except Exception as e:
            logging.error(f"加载模型失败: {e}")
    
    @property
    def model(self):
        """向后兼容：返回摔倒检测模型"""
        return self.fall_model
    
    def _detect_persons(self, frame):
        """
        使用 COCO 模型检测人体
        
        Returns:
            list: 人体边界框列表 [{'bbox': [x1,y1,x2,y2], 'confidence': float}, ...]
        """
        if self.person_model is None:
            return []
        
        results = self.person_model(frame, verbose=False, conf=self.person_confidence, classes=[0])
        
        persons = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for box in boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                
                if cls_id == 0:  # person class
                    bbox = box.xyxy[0].cpu().numpy().tolist()
                    persons.append({
                        'bbox': bbox,
                        'confidence': conf
                    })
        
        return persons
    
    def _detect_falls(self, frame):
        """
        使用摔倒检测模型检测摔倒
        
        Returns:
            list: 检测结果列表 [{'bbox': [...], 'is_fall': bool, 'confidence': float}, ...]
        """
        if self.fall_model is None:
            return []
        
        results = self.fall_model(frame, verbose=False, conf=self.fall_confidence)
        
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for box in boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                class_name = result.names[cls_id].lower()
                bbox = box.xyxy[0].cpu().numpy().tolist()
                
                detections.append({
                    'bbox': bbox,
                    'is_fall': class_name == 'fall',
                    'confidence': conf,
                    'class_name': class_name
                })
        
        return detections
    
    def _match_detections(self, persons, fall_detections):
        """
        通过 IoU 匹配将摔倒检测结果关联到人体
        
        Args:
            persons: 人体检测列表
            fall_detections: 摔倒检测列表
        
        Returns:
            list: 匹配后的人体列表，包含摔倒状态
        """
        matched_persons = []
        
        for person in persons:
            person_bbox = person['bbox']
            person_conf = person['confidence']
            
            # 默认为正常状态
            is_fall = False
            fall_conf = 0.0
            best_iou = 0.0
            
            # 查找与此人体重叠的摔倒检测
            for detection in fall_detections:
                iou = calculate_iou(person_bbox, detection['bbox'])
                
                if iou > self.iou_threshold and iou > best_iou:
                    best_iou = iou
                    if detection['is_fall']:
                        is_fall = True
                        fall_conf = detection['confidence']
            
            matched_persons.append({
                'bbox': person_bbox,
                'is_fall': is_fall,
                'confidence': person_conf,
                'fall_confidence': fall_conf,
                'class_name': 'fall' if is_fall else 'normal',
                'iou': best_iou
            })
        
        return matched_persons
    
    def _detect_single_stage(self, frame):
        """单阶段检测（直接使用摔倒检测模型）"""
        if self.fall_model is None:
            return {
                'fall_detected': False,
                'confidence': 0.0,
                'persons': [],
                'fall_count': 0,
                'normal_count': 0,
                'total_persons': 0
            }
        
        results = self.fall_model(frame, verbose=False, conf=self.confidence_threshold)
        
        persons = []
        fall_detected = False
        max_fall_confidence = 0.0
        fall_count = 0
        normal_count = 0
        
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for box in boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                class_name = result.names[cls_id]
                bbox = box.xyxy[0].cpu().numpy().tolist()
                
                is_fall = (class_name.lower() == 'fall')
                
                persons.append({
                    'bbox': bbox,
                    'is_fall': is_fall,
                    'confidence': conf,
                    'fall_confidence': conf if is_fall else 0.0,
                    'class_name': 'fall' if is_fall else 'normal'
                })
                
                if is_fall:
                    fall_detected = True
                    fall_count += 1
                    max_fall_confidence = max(max_fall_confidence, conf)
                else:
                    normal_count += 1
        
        return {
            'fall_detected': fall_detected,
            'confidence': max_fall_confidence,
            'persons': persons,
            'fall_count': fall_count,
            'normal_count': normal_count,
            'total_persons': len(persons)
        }
    
    def detect_frame(self, frame):
        """
        检测单帧图像中的摔倒
        
        Args:
            frame: 输入图像 (numpy array, BGR 格式)
        
        Returns:
            dict: {
                'fall_detected': bool,
                'confidence': float,
                'persons': [{'bbox': [...], 'is_fall': bool, 'confidence': float}, ...],
                'fall_count': int,
                'normal_count': int,
                'total_persons': int
            }
        """
        # 单阶段模式
        if not self.use_two_stage or self.person_model is None:
            return self._detect_single_stage(frame)
        
        # 两阶段模式
        # 第一阶段：检测人体
        detected_persons = self._detect_persons(frame)
        
        if not detected_persons:
            return {
                'fall_detected': False,
                'confidence': 0.0,
                'persons': [],
                'fall_count': 0,
                'normal_count': 0,
                'total_persons': 0
            }
        
        # 第二阶段：检测摔倒（在完整图像上）
        fall_detections = self._detect_falls(frame)
        
        # 通过 IoU 匹配
        persons = self._match_detections(detected_persons, fall_detections)
        
        # 统计
        fall_detected = False
        max_fall_confidence = 0.0
        fall_count = 0
        normal_count = 0
        
        for person in persons:
            if person['is_fall']:
                fall_detected = True
                fall_count += 1
                max_fall_confidence = max(max_fall_confidence, person['fall_confidence'])
            else:
                normal_count += 1
        
        return {
            'fall_detected': fall_detected,
            'confidence': max_fall_confidence,
            'persons': persons,
            'fall_count': fall_count,
            'normal_count': normal_count,
            'total_persons': len(persons)
        }
    
    def detect_frames_buffer(self, frame_buffer, fps, skip_frames=3):
        """
        使用预读取的帧缓存进行摔倒检测（优化版本，避免重复读取视频）
        
        Args:
            frame_buffer: 预读取的帧列表 [(frame_idx, frame), ...]
            fps: 视频帧率
            skip_frames: 跳帧检测间隔（每隔多少帧检测一次，默认3）
        
        Returns:
            tuple: (是否检测到摔倒, 摔倒发生时间列表, 详细检测结果)
        """
        if not frame_buffer:
            return False, [], []
        
        # ========== 时序分析参数配置 ==========
        window_duration = 1.5
        window_size = max(5, int(fps * window_duration / skip_frames))  # 调整窗口大小
        vote_threshold = 0.5
        min_fall_duration = 1.0
        min_fall_frames = max(2, int(fps * min_fall_duration / skip_frames))  # 调整最小帧数
        cooldown_duration = 2.0
        cooldown_frames = int(fps * cooldown_duration / skip_frames)
        # =====================================
        
        frame_results = []
        fall_events = []
        detection_window = []
        
        in_fall_event = False
        fall_event_start_frame = None
        fall_event_confidence_sum = 0.0
        fall_event_frame_count = 0
        frames_since_last_event = cooldown_frames
        
        # 跳帧检测
        for i, (frame_idx, frame) in enumerate(frame_buffer):
            if i % skip_frames != 0:
                continue
            
            result = self.detect_frame(frame)
            result['frame'] = frame_idx
            result['time'] = frame_idx / fps
            
            detection_window.append(result['fall_detected'])
            if len(detection_window) > window_size:
                detection_window.pop(0)
            
            if len(detection_window) >= min(window_size, 3):
                fall_ratio = sum(detection_window) / len(detection_window)
                smoothed_fall_detected = fall_ratio >= vote_threshold
            else:
                smoothed_fall_detected = False
            
            result['smoothed_fall_detected'] = smoothed_fall_detected
            result['fall_ratio'] = fall_ratio if len(detection_window) >= 3 else 0.0
            frame_results.append(result)
            
            frames_since_last_event += 1
            
            if smoothed_fall_detected:
                if not in_fall_event and frames_since_last_event >= cooldown_frames:
                    in_fall_event = True
                    fall_event_start_frame = frame_idx
                    fall_event_confidence_sum = result['confidence']
                    fall_event_frame_count = 1
                elif in_fall_event:
                    fall_event_confidence_sum += result['confidence']
                    fall_event_frame_count += 1
            else:
                if in_fall_event:
                    fall_duration_frames = frame_idx - fall_event_start_frame
                    
                    if fall_duration_frames >= min_fall_frames * skip_frames:
                        avg_confidence = fall_event_confidence_sum / max(1, fall_event_frame_count)
                        fall_events.append({
                            'start_time': fall_event_start_frame / fps,
                            'end_time': frame_idx / fps,
                            'start_frame': fall_event_start_frame,
                            'end_frame': frame_idx,
                            'duration': fall_duration_frames / fps,
                            'confidence': avg_confidence
                        })
                        frames_since_last_event = 0
                        logging.info(f"确认摔倒事件: {fall_event_start_frame/fps:.2f}s - {frame_idx/fps:.2f}s")
                    
                    in_fall_event = False
                    fall_event_start_frame = None
                    fall_event_confidence_sum = 0.0
                    fall_event_frame_count = 0
        
        # 处理结束时仍在进行的摔倒事件
        if in_fall_event and fall_event_start_frame is not None:
            last_frame_idx = frame_buffer[-1][0] if frame_buffer else 0
            fall_duration_frames = last_frame_idx - fall_event_start_frame
            if fall_duration_frames >= min_fall_frames * skip_frames:
                avg_confidence = fall_event_confidence_sum / max(1, fall_event_frame_count)
                fall_events.append({
                    'start_time': fall_event_start_frame / fps,
                    'end_time': last_frame_idx / fps,
                    'start_frame': fall_event_start_frame,
                    'end_frame': last_frame_idx,
                    'duration': fall_duration_frames / fps,
                    'confidence': avg_confidence
                })
        
        fall_detected = len(fall_events) > 0
        fall_times = [event['start_time'] for event in fall_events]
        
        if fall_detected:
            logging.info(f"帧缓存摔倒检测完成: 发现 {len(fall_events)} 个摔倒事件（跳帧={skip_frames}）")
        else:
            logging.info(f"帧缓存摔倒检测完成: 未发现摔倒事件（跳帧={skip_frames}）")
        
        return fall_detected, fall_times, frame_results
    
    def detect_video(self, video_path, fps=None):
        """
        检测整个视频中的摔倒事件
        
        使用滑动窗口 + 多数投票机制来减少误判：
        - 滑动窗口：分析过去 N 帧的检测结果
        - 多数投票：窗口内超过指定比例的帧检测到摔倒才判定为真正摔倒
        - 状态平滑：避免单帧闪烁导致的误判
        
        Args:
            video_path: 视频文件路径
            fps: 视频帧率（如果为 None 则自动获取）
        
        Returns:
            tuple: (是否检测到摔倒, 摔倒发生时间列表, 详细检测结果)
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logging.error(f"无法打开视频: {video_path}")
            return False, [], []
        
        if fps is None:
            fps = cap.get(cv2.CAP_PROP_FPS)
        
        # ========== 时序分析参数配置 ==========
        window_duration = 1.5  # 滑动窗口时长（秒）
        window_size = max(5, int(fps * window_duration))  # 滑动窗口大小（帧数）
        vote_threshold = 0.5  # 多数投票阈值：窗口内超过50%的帧检测到摔倒才算
        min_fall_duration = 1.0  # 摔倒事件最小持续时间（秒）
        min_fall_frames = max(3, int(fps * min_fall_duration))  # 最小持续帧数
        cooldown_duration = 2.0  # 两次摔倒事件之间的冷却时间（秒）
        cooldown_frames = int(fps * cooldown_duration)
        # =====================================
        
        frame_results = []
        fall_events = []
        
        # 滑动窗口缓存：存储最近 window_size 帧的检测结果
        detection_window = []
        
        # 状态追踪
        in_fall_event = False
        fall_event_start_frame = None
        fall_event_confidence_sum = 0.0
        fall_event_frame_count = 0
        frames_since_last_event = cooldown_frames  # 初始化为已过冷却期
        
        frame_idx = 0
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            
            result = self.detect_frame(frame)
            result['frame'] = frame_idx
            result['time'] = frame_idx / fps
            
            # 维护滑动窗口
            detection_window.append(result['fall_detected'])
            if len(detection_window) > window_size:
                detection_window.pop(0)
            
            # 计算窗口内的摔倒比例
            if len(detection_window) >= min(window_size, 3):  # 至少3帧才开始判断
                fall_ratio = sum(detection_window) / len(detection_window)
                smoothed_fall_detected = fall_ratio >= vote_threshold
            else:
                smoothed_fall_detected = False
            
            # 将平滑后的结果存入
            result['smoothed_fall_detected'] = smoothed_fall_detected
            result['fall_ratio'] = fall_ratio if len(detection_window) >= 3 else 0.0
            frame_results.append(result)
            
            # 更新冷却计数器
            frames_since_last_event += 1
            
            # 时序状态机
            if smoothed_fall_detected:
                if not in_fall_event and frames_since_last_event >= cooldown_frames:
                    # 开始新的摔倒事件
                    in_fall_event = True
                    fall_event_start_frame = frame_idx
                    fall_event_confidence_sum = result['confidence']
                    fall_event_frame_count = 1
                elif in_fall_event:
                    # 继续当前摔倒事件
                    fall_event_confidence_sum += result['confidence']
                    fall_event_frame_count += 1
            else:
                if in_fall_event:
                    # 摔倒事件结束，检查是否满足最小持续时间
                    fall_duration_frames = frame_idx - fall_event_start_frame
                    
                    if fall_duration_frames >= min_fall_frames:
                        # 确认为有效摔倒事件
                        avg_confidence = fall_event_confidence_sum / max(1, fall_event_frame_count)
                        fall_events.append({
                            'start_time': fall_event_start_frame / fps,
                            'end_time': frame_idx / fps,
                            'start_frame': fall_event_start_frame,
                            'end_frame': frame_idx,
                            'duration': fall_duration_frames / fps,
                            'confidence': avg_confidence
                        })
                        frames_since_last_event = 0  # 重置冷却计数器
                        logging.info(f"确认摔倒事件: {fall_event_start_frame/fps:.2f}s - {frame_idx/fps:.2f}s, "
                                   f"持续 {fall_duration_frames/fps:.2f}s, 置信度 {avg_confidence:.2f}")
                    else:
                        logging.debug(f"摔倒事件过短被过滤: {fall_duration_frames/fps:.2f}s < {min_fall_duration}s")
                    
                    # 重置状态
                    in_fall_event = False
                    fall_event_start_frame = None
                    fall_event_confidence_sum = 0.0
                    fall_event_frame_count = 0
            
            frame_idx += 1
        
        # 处理视频结束时仍在进行的摔倒事件
        if in_fall_event and fall_event_start_frame is not None:
            fall_duration_frames = frame_idx - fall_event_start_frame
            if fall_duration_frames >= min_fall_frames:
                avg_confidence = fall_event_confidence_sum / max(1, fall_event_frame_count)
                fall_events.append({
                    'start_time': fall_event_start_frame / fps,
                    'end_time': frame_idx / fps,
                    'start_frame': fall_event_start_frame,
                    'end_frame': frame_idx,
                    'duration': fall_duration_frames / fps,
                    'confidence': avg_confidence
                })
        
        cap.release()
        
        fall_detected = len(fall_events) > 0
        fall_times = [event['start_time'] for event in fall_events]
        
        if fall_detected:
            logging.info(f"视频摔倒检测完成: 发现 {len(fall_events)} 个摔倒事件")
        else:
            logging.info("视频摔倒检测完成: 未发现摔倒事件")
        
        return fall_detected, fall_times, frame_results
    
    def draw_results(self, frame, result):
        """
        在图像上绘制检测结果
        
        Args:
            frame: 输入图像
            result: detect_frame 的返回结果
        
        Returns:
            frame: 绘制了结果的图像
        """
        output = frame.copy()
        
        for person in result.get('persons', []):
            bbox = person['bbox']
            x1, y1, x2, y2 = [int(v) for v in bbox]
            
            is_fall = person.get('is_fall', False)
            conf = person.get('confidence', 0.0)
            fall_conf = person.get('fall_confidence', 0.0)
            
            # 颜色：红色=摔倒，绿色=正常
            color = (0, 0, 255) if is_fall else (0, 255, 0)
            
            # 绘制边界框
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签：FALL 或 NORMAL
            if is_fall:
                label = f"FALL {fall_conf:.2f}"
            else:
                label = f"NORMAL {conf:.2f}"
            
            # 绘制标签背景
            (text_width, text_height), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(output, (x1, y1 - text_height - 10), 
                         (x1 + text_width, y1), color, -1)
            cv2.putText(output, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return output


# 向后兼容的函数接口
_detector = None


def get_detector(model_path=None, confidence_threshold=0.5, use_two_stage=True):
    """获取或创建摔倒检测器实例"""
    global _detector
    if _detector is None:
        _detector = FallDetector(
            fall_model_path=model_path, 
            confidence_threshold=confidence_threshold,
            use_two_stage=use_two_stage
        )
    return _detector


def detect_fall(keypoints_df=None, fps=30, video_path=None, model_path=None, frame_buffer=None):
    """
    检测摔倒事件
    
    Args:
        keypoints_df: 关键点数据（向后兼容，当前未使用）
        fps: 视频帧率
        video_path: 视频文件路径（当 frame_buffer 为 None 时使用）
        model_path: 模型路径
        frame_buffer: 预读取的帧缓存列表（优化性能，避免重复读取视频）
    
    Returns:
        tuple: (是否检测到摔倒, 摔倒时间列表)
    """
    if frame_buffer is not None:
        # 使用预读取的帧进行检测（优化模式）
        detector = get_detector(model_path)
        fall_detected, fall_times, _ = detector.detect_frames_buffer(frame_buffer, fps)
        return fall_detected, fall_times
    
    if video_path is None:
        logging.warning("未提供视频路径或帧缓存，无法进行摔倒检测")
        return False, []
    
    detector = get_detector(model_path)
    fall_detected, fall_times, _ = detector.detect_video(video_path, fps)
    return fall_detected, fall_times


def detect_fall_in_frame(frame, model_path=None, confidence_threshold=0.5):
    """检测单帧中的摔倒"""
    detector = get_detector(model_path, confidence_threshold)
    return detector.detect_frame(frame)


def format_fall_warning(fall_detected, fall_start_times):
    """格式化摔倒警告信息"""
    if fall_detected and fall_start_times:
        fall_times_str = [f"{t:.2f}" for t in fall_start_times]
        return f"警告：在 {', '.join(fall_times_str)} 秒检测到摔倒"
    return ""


def get_fall_events_details(fall_detected, fall_times, frame_results=None):
    """
    获取摔倒事件的详细信息
    
    Args:
        fall_detected: 是否检测到摔倒
        fall_times: 摔倒时间列表
        frame_results: 帧检测结果列表（可选）
    
    Returns:
        dict: 摔倒事件详细信息
    """
    return {
        'fall_detected': fall_detected,
        'fall_count': len(fall_times) if fall_times else 0,
        'fall_times': fall_times or [],
        'warning_message': format_fall_warning(fall_detected, fall_times)
    }
