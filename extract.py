import os
import cv2
import pysrt

def total_seconds(sub):
    return sub.hours * 3600 + sub.minutes * 60 + sub.seconds + sub.milliseconds / 1000.0

def extract_frames_with_subtitles(movie_path, subtitle_path, output_dir, start_time_in_seconds=None, end_time_in_seconds=None):
    subs = pysrt.open(subtitle_path)

    video = cv2.VideoCapture(movie_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    fps_int = max(1, int(round(fps)))  # integer fps for sampling and file naming
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Get original video dimensions
    original_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Calculate new dimensions maintaining aspect ratio
    target_width = 1920  # Full HD width
    target_height = int((target_width / original_width) * original_height)

    if end_time_in_seconds is None:
        end_time_in_seconds = total_frames / fps

    # Use project-root tracking file so extraction always starts/resumes from the same place.
    project_root = os.path.dirname(os.path.abspath(__file__))
    tracking_file = os.path.join(project_root, 'frame_extraction_progress.txt')
    os.makedirs(output_dir, exist_ok=True)
    
    if os.path.exists(tracking_file):
        # stored_index is the "seconds" index used in frame filenames (e.g. frame_0123.jpg)
        try:
            with open(tracking_file, 'r') as f:
                stored_index = int(f.read().strip())
            start_frame = stored_index * fps_int
            print(f"Resuming from stored frame index {stored_index} (start_frame={start_frame})")
        except Exception:
            print("Invalid tracking file content; starting from 0")
            start_frame = 0
    else:
        # initialize tracking file with start_time (in seconds / frame-index) or 0
        start_index = int(start_time_in_seconds) if start_time_in_seconds is not None else 0
        with open(tracking_file, 'w') as f:
            f.write(str(start_index))
        start_frame = start_index * fps_int
        print(f"Initializing tracking file to frame index {start_index} (start_frame={start_frame})")

    start_frame = max(0, start_frame)
    end_frame = min(total_frames, int(end_time_in_seconds * fps))
 
    video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    print(f"Starting frame extraction from frame {start_frame} (time: {start_time_in_seconds} seconds)")
 
    frame_count = start_frame

    while frame_count <= end_frame:
        ret, frame = video.read()
        if not ret or frame_count > end_frame:
            break

        if frame_count % fps_int == 0:
            current_time = frame_count / fps

            subtitle_text = ''
            for sub in subs:
                if total_seconds(sub.start) <= current_time <= total_seconds(sub.end):
                    subtitle_text = sub.text.replace('"', '')
                    break

            # Use INTER_LANCZOS4 for better quality upscaling
            frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)

            if subtitle_text:
                # Improved subtitle rendering
                font = cv2.FONT_HERSHEY_DUPLEX
                font_scale = 1.5  # Increased for better readability at higher resolution
                font_thickness = 2
                
                # Add subtle shadow/outline for better subtitle visibility
                shadow_color = (0, 0, 0)
                text_color = (255, 255, 255)
                
                # Calculate text size and position
                text_size, _ = cv2.getTextSize(subtitle_text, font, font_scale, font_thickness)
                text_x = (target_width - text_size[0]) // 2
                text_y = target_height - 50  # Position from bottom
                
                # Draw shadow/outline
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    cv2.putText(frame, subtitle_text, 
                              (text_x + dx, text_y + dy), 
                              font, font_scale, shadow_color, 
                              font_thickness, cv2.LINE_AA)
                
                # Draw main text
                cv2.putText(frame, subtitle_text, 
                          (text_x, text_y), 
                          font, font_scale, text_color, 
                          font_thickness, cv2.LINE_AA)

            # Save with higher quality; use integer fps for naming
            saved_index = frame_count // fps_int
            frame_file = os.path.join(output_dir, f'frame_{saved_index:04d}.jpg')
            cv2.imwrite(frame_file, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(f"Extracted Frame {saved_index}")

            # Update tracking file with the saved index (so it matches filenames)
            try:
                with open(tracking_file, 'w') as f:
                    f.write(str(saved_index))
            except Exception as e:
                print(f"Warning: failed to update tracking file: {e}")

        frame_count += 1

    video.release()
    print(f"Total frames extracted: {frame_count // int(fps)}")

def main():
    movie_path = r'D:\Pirates_of_the_Caribbean_The_Curse_of_the_Black_Pearl_2003_BluRay.mkv'
    subtitle_path = r'D:\Downloads\Pirates.of.the.Caribbean.Curse.of.the.Black.Pearl.2003.1080p.BrRip.x264.Deceit.YIFY.English.srt' 
    output_dir = 'frames'
    start_time_in_seconds = 53*60 + 27  # 53:27 in seconds -> 3207
    end_time_in_seconds = None

    extract_frames_with_subtitles(movie_path, subtitle_path, output_dir, start_time_in_seconds, end_time_in_seconds)

if __name__ == '__main__':
    main()