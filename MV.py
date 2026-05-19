#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from moviepy import AudioFileClip
    from moviepy.config import get_setting
except ImportError:
    from moviepy.editor import AudioFileClip
    from moviepy.config import get_setting

import numpy as np

# 註冊 HEIC/HEIF 格式支援
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False


# ===== 常數定義 =====
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
FONT_SIZE = 80
FONT_COLOR = (255, 255, 255)
OUTLINE_COLOR = (0, 0, 0)
OUTLINE_WIDTH = 3
PROCESSING_MAX_SIZE = 2400
BLUR_RADIUS = 20

if HEIC_SUPPORTED:
    SUPPORTED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif')
else:
    SUPPORTED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.webp')

SUPPORTED_AUDIO_FORMATS = ('.mp3', '.wav', '.m4a')


def get_ffmpeg_path():
    """取得 FFmpeg 路徑（優先使用 MoviePy 內建）"""
    try:
        # 方法1：使用 MoviePy 的 ffmpeg
        ffmpeg_path = get_setting("FFMPEG_BINARY")
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            return ffmpeg_path
    except:
        pass
    
    try:
        # 方法2：檢查系統 PATH
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              timeout=2)
        if result.returncode == 0:
            return 'ffmpeg'
    except:
        pass
    
    # 方法3：常見安裝位置
    common_paths = [
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        os.path.expanduser('~/ffmpeg/bin/ffmpeg.exe'),
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


def parse_lrc(lrc_path: str) -> List[Tuple[float, str]]:
    """解析 LRC 格式歌詞檔"""
    lyrics = []
    lrc_pattern = re.compile(r'\[(\d+):(\d+)\.(\d+)\](.*)$')
    
    try:
        with open(lrc_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                match = lrc_pattern.match(line)
                if match:
                    minutes = int(match.group(1))
                    seconds = int(match.group(2))
                    centiseconds = int(match.group(3))
                    text = match.group(4).strip()
                    total_seconds = minutes * 60 + seconds + centiseconds / 100.0
                    lyrics.append((total_seconds, text))
        
        lyrics.sort(key=lambda x: x[0])
        return lyrics
        
    except Exception as e:
        raise ValueError(f"無法解析 LRC 檔案：{e}")


def load_images(folder_path: str) -> List[str]:
    """從資料夾載入照片路徑，依檔名升冪排序"""
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"照片資料夾不存在：{folder_path}")
    
    image_files = []
    for file in os.listdir(folder_path):
        if file.lower().endswith(SUPPORTED_IMAGE_FORMATS):
            image_files.append(os.path.join(folder_path, file))
    
    if not image_files:
        raise ValueError(f"資料夾內沒有找到任何支援的圖片檔案（{SUPPORTED_IMAGE_FORMATS}）")
    
    image_files.sort()
    return image_files


def load_and_preprocess_image(image_path: str) -> Image.Image:
    """載入並預處理圖片"""
    try:
        img = Image.open(image_path).convert('RGB')
        
        width, height = img.size
        max_dim = max(width, height)
        
        if max_dim > PROCESSING_MAX_SIZE:
            scale = PROCESSING_MAX_SIZE / max_dim
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return img
        
    except Exception as e:
        raise ValueError(f"無法載入圖片 {image_path}：{e}")


def create_blurred_background_fast(image: Image.Image) -> Image.Image:
    """建立模糊背景"""
    original_width, original_height = image.size
    scale = max(VIDEO_WIDTH / original_width, VIDEO_HEIGHT / original_height)
    
    new_width = int(original_width * scale)
    new_height = int(original_height * scale)
    
    blurred = image.resize((new_width, new_height), Image.Resampling.BILINEAR)
    
    left = (new_width - VIDEO_WIDTH) // 2
    top = (new_height - VIDEO_HEIGHT) // 2
    blurred = blurred.crop((left, top, left + VIDEO_WIDTH, top + VIDEO_HEIGHT))
    
    blurred = blurred.filter(ImageFilter.BoxBlur(BLUR_RADIUS))
    
    return blurred


def resize_foreground_fast(image: Image.Image) -> Image.Image:
    """縮放原始照片"""
    original_width, original_height = image.size
    scale = min(VIDEO_WIDTH / original_width, VIDEO_HEIGHT / original_height)
    
    new_width = int(original_width * scale)
    new_height = int(original_height * scale)
    resized = image.resize((new_width, new_height), Image.Resampling.BILINEAR)
    
    return resized


def draw_subtitle_fast(canvas: Image.Image, text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    """在畫布上繪製帶描邊的字幕"""
    if not text:
        return canvas
    
    draw = ImageDraw.Draw(canvas)
    
    max_chars_per_line = 30
    lines = []
    current_line = ""
    
    for char in text:
        if len(current_line) < max_chars_per_line:
            current_line += char
        else:
            lines.append(current_line)
            current_line = char
    
    if current_line:
        lines.append(current_line)
    
    line_height = FONT_SIZE + 10
    total_height = len(lines) * line_height
    start_y = int(VIDEO_HEIGHT * 4 / 5) - total_height // 2
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (VIDEO_WIDTH - text_width) // 2
        y = start_y + i * line_height
        
        offsets = [(-OUTLINE_WIDTH, -OUTLINE_WIDTH), (0, -OUTLINE_WIDTH), (OUTLINE_WIDTH, -OUTLINE_WIDTH),
                   (-OUTLINE_WIDTH, 0), (OUTLINE_WIDTH, 0),
                   (-OUTLINE_WIDTH, OUTLINE_WIDTH), (0, OUTLINE_WIDTH), (OUTLINE_WIDTH, OUTLINE_WIDTH)]
        
        for offset_x, offset_y in offsets:
            draw.text((x + offset_x, y + offset_y), line, font=font, fill=OUTLINE_COLOR)
        
        draw.text((x, y), line, font=font, fill=FONT_COLOR)
    
    return canvas


def create_base_frame_fast(image: Image.Image) -> Image.Image:
    """建立基礎影格"""
    canvas = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    
    blurred_bg = create_blurred_background_fast(image)
    canvas.paste(blurred_bg, (0, 0))
    
    resized_fg = resize_foreground_fast(image)
    fg_x = (VIDEO_WIDTH - resized_fg.width) // 2
    fg_y = (VIDEO_HEIGHT - resized_fg.height) // 2
    canvas.paste(resized_fg, (fg_x, fg_y))
    
    return canvas


def get_subtitle_at_time(t: float, lyrics: List[Tuple[float, str]]) -> str:
    """取得指定時間點應顯示的字幕"""
    if not lyrics:
        return ""
    
    current_lyric = ""
    for time_point, text in lyrics:
        if t >= time_point:
            current_lyric = text
        else:
            break
    
    return current_lyric


def validate_output_path(output_path: str) -> str:
    """驗證並修正輸出路徑"""
    output_path = output_path.strip().strip('"').strip("'")
    
    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, "output.mp4")
        print(f"   ⚠ 輸出路徑為資料夾，自動改為：{output_path}")
    
    _, ext = os.path.splitext(output_path)
    if not ext:
        output_path += ".mp4"
        print(f"   ⚠ 未指定副檔名，自動改為：{output_path}")
    elif ext.lower() not in ['.mp4', '.avi', '.mov', '.mkv']:
        raise ValueError(f"輸出檔案副檔名必須是影片格式，目前為：{ext}")
    
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        raise FileNotFoundError(f"輸出資料夾不存在：{output_dir}")
    
    return output_path


def build_video_with_ffmpeg(image_files: List[str], audio_path: str, lrc_path: str, 
                            font_path: str, output_path: str, ffmpeg_path: str):
    """使用 FFmpeg pipe 建立影片（最快方法）"""
    
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    
    lyrics = parse_lrc(lrc_path)
    num_images = len(image_files)
    duration_per_image = audio_duration / num_images
    total_frames = int(audio_duration * VIDEO_FPS)
    
    font = ImageFont.truetype(font_path, FONT_SIZE)
    
    print(f"   總影格數: {total_frames} 幀")
    
    temp_video = output_path.replace('.mp4', '_temp_video.mp4')
    
    ffmpeg_cmd = [
        ffmpeg_path,
        '-y',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{VIDEO_WIDTH}x{VIDEO_HEIGHT}',
        '-pix_fmt', 'rgb24',
        '-r', str(VIDEO_FPS),
        '-i', '-',
        '-an',
        '-vcodec', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        temp_video
    ]
    
    process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    t_start = time.time()
    
    current_photo_index = -1
    current_base_frame = None
    last_subtitle = None
    cached_frame_with_subtitle = None
    frames_written = 0
    last_progress_time = t_start
    
    try:
        for frame_num in range(total_frames):
            current_time = frame_num / VIDEO_FPS
            photo_index = min(int(current_time / duration_per_image), num_images - 1)
            
            if photo_index != current_photo_index:
                print(f"      載入照片 {photo_index + 1}/{num_images}")
                img = load_and_preprocess_image(image_files[photo_index])
                current_base_frame = create_base_frame_fast(img)
                current_photo_index = photo_index
                last_subtitle = None
            
            current_subtitle = get_subtitle_at_time(current_time, lyrics)
            
            if current_subtitle != last_subtitle:
                cached_frame_with_subtitle = current_base_frame.copy()
                cached_frame_with_subtitle = draw_subtitle_fast(cached_frame_with_subtitle, current_subtitle, font)
                last_subtitle = current_subtitle
            
            frame_bytes = np.array(cached_frame_with_subtitle).tobytes()
            process.stdin.write(frame_bytes)
            frames_written += 1
            
            current_time_now = time.time()
            if current_time_now - last_progress_time >= 2.0:
                progress = (frames_written / total_frames) * 100
                elapsed = current_time_now - t_start
                fps = frames_written / elapsed if elapsed > 0 else 0
                eta = (total_frames - frames_written) / fps if fps > 0 else 0
                
                print(f"      進度: {progress:.1f}% | {fps:.1f} fps | 剩餘 {eta:.0f}s")
                last_progress_time = current_time_now
        
        process.stdin.close()
        stdout, stderr = process.communicate(timeout=60)
        
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg 編碼失敗")
        
        t_encode = time.time() - t_start
        print(f"   ✓ 影格生成完成 (耗時 {t_encode:.1f}s, 平均 {total_frames/t_encode:.1f} fps)")
        
    except Exception as e:
        process.kill()
        raise e
    
    print("   合併音訊...")
    t_start = time.time()
    
    ffmpeg_merge_cmd = [
        ffmpeg_path,
        '-y',
        '-i', temp_video,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        output_path
    ]
    
    result = subprocess.run(ffmpeg_merge_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"音訊合併失敗")
    
    print(f"   ✓ 音訊合併完成 (耗時 {time.time()-t_start:.1f}s)")
    
    if os.path.exists(temp_video):
        os.remove(temp_video)
    
    audio_clip.close()


def build_video_with_moviepy(image_files: List[str], audio_path: str, lrc_path: str, 
                             font_path: str, output_path: str):
    """使用 MoviePy 建立影片（降級方案，但已優化）"""
    print("\n   使用方法：MoviePy ImageClip（相容模式）")
    
    from moviepy.editor import ImageClip, concatenate_videoclips
    
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    
    lyrics = parse_lrc(lrc_path)
    num_images = len(image_files)
    duration_per_image = audio_duration / num_images
    
    font = ImageFont.truetype(font_path, FONT_SIZE)
    
    print(f"   {num_images} 張照片，每張播放 {duration_per_image:.2f} 秒")
    print("   生成影片片段...")
    
    clips = []
    t_start = time.time()
    
    for i, image_path in enumerate(image_files):
        print(f"      處理照片 {i+1}/{num_images}")
        
        start_time = i * duration_per_image
        end_time = (i + 1) * duration_per_image
        
        # 載入並處理照片
        img = load_and_preprocess_image(image_path)
        base_frame = create_base_frame_fast(img)
        
        # 找出這張照片時間內的字幕變化
        lyrics_changes = []
        current_lyric = ""
        
        # 找起始字幕
        for time_point, text in lyrics:
            if time_point <= start_time:
                current_lyric = text
        
        lyrics_changes.append((start_time, current_lyric))
        
        # 找區間內的變化
        for time_point, text in lyrics:
            if start_time < time_point < end_time:
                lyrics_changes.append((time_point, text))
        
        # 為每個字幕狀態生成片段
        for j, (lyric_time, lyric_text) in enumerate(lyrics_changes):
            if j < len(lyrics_changes) - 1:
                sub_duration = lyrics_changes[j + 1][0] - lyric_time
            else:
                sub_duration = end_time - lyric_time
            
            frame_with_subtitle = base_frame.copy()
            frame_with_subtitle = draw_subtitle_fast(frame_with_subtitle, lyric_text, font)
            
            frame_array = np.array(frame_with_subtitle)
            sub_clip = ImageClip(frame_array, duration=sub_duration)
            clips.append(sub_clip)
    
    print(f"   ✓ 片段生成完成 (耗時 {time.time()-t_start:.1f}s)")
    print(f"   合併 {len(clips)} 個片段...")
    
    t_start = time.time()
    final_video = concatenate_videoclips(clips, method="compose")
    print(f"   ✓ 合併完成 (耗時 {time.time()-t_start:.1f}s)")
    
    print("   加入音訊並編碼輸出...")
    t_start = time.time()
    final_video = final_video.set_audio(audio_clip)
    
    final_video.write_videofile(
        output_path,
        fps=VIDEO_FPS,
        codec='libx264',
        audio_codec='aac',
        temp_audiofile='temp-audio.m4a',
        remove_temp=True,
        preset='ultrafast',
        threads=4,
        verbose=False,
        logger=None
    )
    
    print(f"   ✓ 編碼完成 (耗時 {time.time()-t_start:.1f}s)")
    
    audio_clip.close()
    final_video.close()


def main():
    """主程式入口"""
    if HEIC_SUPPORTED:
        print("✓ HEIC 格式支援已啟用")
    else:
        print("⚠ 若要支援 HEIC 格式，請執行：pip install pillow-heif")
    
    print(f"📷 支援的圖片格式：{', '.join(SUPPORTED_IMAGE_FORMATS)}")
    
    try:
        photo_folder = input("請輸入照片資料夾路徑：").strip()
        audio_path = input("請輸入音樂檔路徑：").strip()
        lrc_path = input("請輸入歌詞字幕檔路徑（lrc檔）：").strip()
        font_path = input("請輸入字型檔路徑（ttf檔）：").strip()
        output_path = input("請輸入輸出影片檔路徑（如 D:\\MV\\output.mp4）：").strip()
        
        print("\n🔍 驗證檔案...")
        
        if not os.path.isdir(photo_folder):
            raise FileNotFoundError(f"照片資料夾不存在：{photo_folder}")
        print(f"   ✓ 照片資料夾：{photo_folder}")
        
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"音樂檔不存在：{audio_path}")
        if not audio_path.lower().endswith(SUPPORTED_AUDIO_FORMATS):
            raise ValueError(f"音樂檔格式不支援，請使用：{SUPPORTED_AUDIO_FORMATS}")
        print(f"   ✓ 音樂檔：{audio_path}")
        
        if not os.path.isfile(lrc_path):
            raise FileNotFoundError(f"字幕檔不存在：{lrc_path}")
        print(f"   ✓ 字幕檔：{lrc_path}")
        
        if not os.path.isfile(font_path):
            raise FileNotFoundError(f"字型檔不存在：{font_path}")
        if not font_path.lower().endswith(('.ttf', '.otf')):
            raise ValueError(f"字型檔格式不支援，請使用 .ttf 或 .otf")
        print(f"   ✓ 字型檔：{font_path}")
        
        output_path = validate_output_path(output_path)
        print(f"   ✓ 輸出路徑：{output_path}")
        
        image_files = load_images(photo_folder)
        print(f"   ✓ 找到 {len(image_files)} 張照片")
        
        # 偵測 FFmpeg
        print("\n🔍 偵測 FFmpeg...")
        ffmpeg_path = get_ffmpeg_path()
        
        if ffmpeg_path:
            print(f"   ✓ 找到 FFmpeg: {ffmpeg_path}")
            use_direct_ffmpeg = True
        else:
            print("   ⚠ 未找到 FFmpeg，將使用 MoviePy 相容模式")
            print("   （若想獲得最佳效能，請安裝 FFmpeg）")
            use_direct_ffmpeg = False
        
        print("\n🎬 開始製作影片...")
        start_time = time.time()
        
        if use_direct_ffmpeg:
            build_video_with_ffmpeg(image_files, audio_path, lrc_path, font_path, output_path, ffmpeg_path)
        else:
            build_video_with_moviepy(image_files, audio_path, lrc_path, font_path, output_path)
        
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ 影片製作完成！")
        print(f"   輸出檔案：{output_path}")
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"   檔案大小：{file_size:.1f} MB")
        
        print(f"\n⏱️  總處理時間: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分鐘)")
        print(f"   平均速度: {elapsed_time/len(image_files):.2f} 秒/張")
        
        if elapsed_time < 200:
            improvement = (336 - elapsed_time) / 336 * 100
        
    except KeyboardInterrupt:
        print("\n\n⚠️  使用者中斷執行")
    except Exception as e:
        print(f"\n\n❌ 錯誤：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
