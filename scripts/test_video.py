"""
视频摔倒检测测试脚本

用法：
    python scripts/test_video.py                    # 使用默认测试视频
    python scripts/test_video.py video.mp4          # 处理指定视频文件
    python scripts/test_video.py --camera           # 使用摄像头
    python scripts/test_video.py --save             # 处理并保存结果
"""

import sys
import os
import cv2
import argparse
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8')

# 降低日志级别
logging.getLogger('ultralytics').setLevel(logging.WARNING)

from backend import FallDetector

# ============ 配置区域 ============
# 测试视频目录
TEST_VIDEO_DIR = Path(__file__).parent / "fall_test_video"
# 默认测试视频
DEFAULT_VIDEO = TEST_VIDEO_DIR / "4.mp4"
# =================================


def process_video(video_source, save_output=False, show_window=True, output_dir=None):
    """
    处理视频进行摔倒检测
    
    Args:
        video_source: 视频路径或摄像头索引（0=默认摄像头）
        save_output: 是否保存处理后的视频
        show_window: 是否显示实时窗口
        output_dir: 输出目录（默认与输入视频同目录）
    """
    # 初始化检测器（两阶段检测模式）
    print("正在加载模型...")
    detector = FallDetector(use_two_stage=True)
    
    if detector.fall_model is None:
        print("❌ 摔倒检测模型加载失败！请先训练模型。")
        return
    
    print(f"✅ 摔倒检测模型加载成功！类别: {detector.fall_model.names}")
    if detector.person_model is not None:
        print(f"✅ 人体检测模型加载成功（两阶段模式）")
        print("   第一阶段：COCO 预训练模型检测人体")
        print("   第二阶段：摔倒检测模型判断摔倒/正常")
    else:
        print("⚠️ 人体检测模型未加载，使用单阶段模式")
    
    # 打开视频源
    if isinstance(video_source, int) or video_source == "0":
        cap = cv2.VideoCapture(int(video_source) if isinstance(video_source, str) else video_source)
        source_name = f"摄像头 {video_source}"
        is_camera = True
    else:
        if not os.path.exists(video_source):
            print(f"❌ 视频文件不存在: {video_source}")
            return
        cap = cv2.VideoCapture(video_source)
        source_name = Path(video_source).name
        is_camera = False
    
    if not cap.isOpened():
        print(f"❌ 无法打开视频源: {video_source}")
        return
    
    # 获取视频信息
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_camera else 0
    
    print(f"\n视频信息:")
    print(f"  - 来源: {source_name}")
    print(f"  - 分辨率: {width}x{height}")
    print(f"  - 帧率: {fps:.1f} FPS")
    if total_frames > 0:
        print(f"  - 总帧数: {total_frames}")
        print(f"  - 时长: {total_frames/fps:.1f} 秒")
    
    # 设置输出视频
    out = None
    output_path = None
    if save_output and not is_camera:
        video_path = Path(video_source)
        # 确定输出目录
        if output_dir:
            out_dir = Path(output_dir)
        else:
            out_dir = video_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = out_dir / f"{video_path.stem}_detected.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        print(f"  - 输出: {output_path}")
    
    print("\n开始处理...")
    if show_window:
        print("按 'q' 退出，按 's' 截图")
    
    frame_idx = 0
    fall_events = []
    
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            
            # 检测
            result = detector.detect_frame(frame)
            
            # 绘制结果
            output_frame = detector.draw_results(frame, result)
            
            # 添加状态信息
            status_text = f"Frame: {frame_idx}"
            if result['fall_detected']:
                status_text += f" | FALL DETECTED! ({result['confidence']:.2f})"
                fall_events.append({
                    'frame': frame_idx,
                    'time': frame_idx / fps,
                    'confidence': result['confidence']
                })
            else:
                status_text += f" | Normal ({result['total_persons']} persons)"
            
            # 绘制状态栏
            cv2.rectangle(output_frame, (0, 0), (width, 35), (0, 0, 0), -1)
            cv2.putText(output_frame, status_text, (10, 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 保存帧
            if out is not None:
                out.write(output_frame)
            
            # 显示窗口
            if show_window:
                cv2.imshow('Fall Detection', output_frame)
                
                key = cv2.waitKey(1 if is_camera else 30) & 0xFF
                if key == ord('q'):
                    print("\n用户中止")
                    break
                elif key == ord('s'):
                    screenshot_path = f"screenshot_{frame_idx}.jpg"
                    cv2.imwrite(screenshot_path, output_frame)
                    print(f"  截图已保存: {screenshot_path}")
            
            frame_idx += 1
            
            # 打印进度
            if not is_camera and total_frames > 0 and frame_idx % 30 == 0:
                progress = (frame_idx / total_frames) * 100
                print(f"\r  处理进度: {progress:.1f}% ({frame_idx}/{total_frames})", end='', flush=True)
    
    except KeyboardInterrupt:
        print("\n用户中止")
    
    finally:
        cap.release()
        if out is not None:
            out.release()
        if show_window:
            cv2.destroyAllWindows()
    
    # 打印摘要
    print("\n" + "=" * 50)
    print("检测完成！")
    print("=" * 50)
    print(f"处理帧数: {frame_idx}")
    print(f"检测到摔倒事件: {len(fall_events)} 次")
    
    if fall_events:
        print("\n摔倒事件详情:")
        for i, event in enumerate(fall_events[:10]):
            print(f"  {i+1}. 时间: {event['time']:.2f}s (帧 {event['frame']}), 置信度: {event['confidence']:.2f}")
        if len(fall_events) > 10:
            print(f"  ... 还有 {len(fall_events) - 10} 个事件")
    
    if output_path:
        print(f"\n结果视频已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='视频摔倒检测测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
示例:
  python scripts/test_video.py                     使用默认测试视频
  python scripts/test_video.py video.mp4           处理指定视频文件
  python scripts/test_video.py --camera            使用摄像头实时检测
  python scripts/test_video.py --save              处理并保存结果视频
  python scripts/test_video.py --no-show           只处理不显示窗口

默认测试视频: {DEFAULT_VIDEO}
        """
    )
    
    parser.add_argument('video', nargs='?', default=None,
                       help=f'视频文件路径（默认: {DEFAULT_VIDEO.name}）')
    parser.add_argument('--camera', '-c', action='store_true',
                       help='使用摄像头')
    parser.add_argument('--save', '-s', action='store_true',
                       help='保存处理后的视频')
    parser.add_argument('--no-show', action='store_true',
                       help='不显示实时窗口')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("视频摔倒检测测试")
    print("=" * 50)
    
    # 确定视频源
    if args.camera:
        video_source = 0
    elif args.video:
        video_source = args.video
    else:
        # 使用默认测试视频
        if DEFAULT_VIDEO.exists():
            video_source = str(DEFAULT_VIDEO)
            print(f"使用默认测试视频: {DEFAULT_VIDEO.name}")
        else:
            print(f"❌ 默认测试视频不存在: {DEFAULT_VIDEO}")
            print("请将测试视频放入 scripts/fall_test_video/ 目录")
            return
    
    process_video(
        video_source=video_source,
        save_output=args.save,
        show_window=not args.no_show,
        output_dir=TEST_VIDEO_DIR if not args.camera else None
    )


if __name__ == "__main__":
    main()

