import cv2
import numpy as np
from pathlib import Path
import os
from transitions import create_transition

class VideoPlayer:
    def __init__(self, video_folder='videos'):
        self.video_folder = video_folder
        self.videos = self.load_videos()
        self.current_index = 0
        self.transition_frames = 20  # 전환 프레임 수
        self.show_ui = True  # UI 표시 여부
        self.display_size = (720, 1280)  # 표시 크기 (width, height)
        # 기본 전환 효과 (slide). 필요시 다른 효과로 교체 가능
        self.transition = create_transition('slide', direction='down')
        
        # 마우스 드래그 상태
        self.mouse_down = False
        self.mouse_start_y = 0
        self.swipe_threshold = 100  # 스와이프 감지 최소 거리 (픽셀)
        self.swipe_action = None  # 'next', 'prev', or None
        
    def load_videos(self):
        """videos 폴더에서 동영상 파일 로드"""
        # 지원 확장자에 mp3 추가 (오디오 파일은 아래 검사에서 자동 제외)
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.mp3']
        candidates = [str(f) for f in Path(self.video_folder).glob('*')
                      if f.suffix.lower() in video_extensions]

        # OpenCV로 실제 재생 가능한 비디오만 필터링
        valid_videos = []
        for path in sorted(candidates):
            cap = cv2.VideoCapture(path)
            if cap.isOpened():
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if frame_count > 0 and width > 0 and height > 0:
                    valid_videos.append(path)
            cap.release()

        return valid_videos
    
    # 슬라이드 전환 로직은 transitions 모듈로 분리되었습니다.
    
    def resize_with_aspect_ratio(self, frame, target_size):
        """
        비디오 비율을 유지하면서 리사이즈 (letterbox/pillarbox)
        """
        target_w, target_h = target_size
        h, w = frame.shape[:2]

        # 비율 계산
        ratio = min(target_w / w, target_h / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)

        # 리사이즈
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # 검은 배경에 중앙 정렬
        result = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        x_offset = (target_w - new_w) // 2
        y_offset = (target_h - new_h) // 2
        result[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return result
    def get_frame(self, cap, target_size):
        """비디오에서 프레임 읽기 및 리사이즈"""
        ret, frame = cap.read()
        if not ret:
            return None
        return self.resize_with_aspect_ratio(frame, target_size)
    
    def draw_ui_overlay(self, frame, video_name, current_frame, total_frames):
        """
        화면에 UI 오버레이 추가
        - 상단: 현재 영상 이름
        - 하단: 진행도 바, 조작 힌트
        """
        if not self.show_ui:
            return frame
        
        overlay = frame.copy()
        h, w = frame.shape[:2]
        
        # 반투명 배경 - 상단
        cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 0), -1)
        # 반투명 배경 - 하단
        cv2.rectangle(overlay, (0, h-120), (w, h), (0, 0, 0), -1)
        
        # 블렌딩
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        # 상단: 영상 이름
        font = cv2.FONT_HERSHEY_SIMPLEX
        video_name_short = os.path.basename(video_name)
        if len(video_name_short) > 40:
            video_name_short = video_name_short[:37] + "..."
        
        cv2.putText(frame, video_name_short, (20, 40), 
                   font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        # 영상 번호 표시
        video_info = f"{self.current_index + 1}/{len(self.videos)}"
        cv2.putText(frame, video_info, (20, 75), 
                   font, 0.6, (180, 180, 180), 1, cv2.LINE_AA)
        
        # 진행도 바
        progress = current_frame / max(total_frames, 1)
        bar_y = h - 90
        bar_width = w - 40
        bar_height = 8
        
        # 배경 바 (회색)
        cv2.rectangle(frame, (20, bar_y), (20 + bar_width, bar_y + bar_height), 
                     (80, 80, 80), -1)
        
        # 진행 바 (흰색)
        progress_width = int(bar_width * progress)
        if progress_width > 0:
            cv2.rectangle(frame, (20, bar_y), (20 + progress_width, bar_y + bar_height), 
                         (255, 255, 255), -1)
        
        # 시간 표시
        current_time = current_frame / max(total_frames, 1) * (total_frames / 30)  # 대략적인 시간
        time_text = f"{int(current_time)}s"
        cv2.putText(frame, time_text, (w - 100, bar_y + bar_height + 25), 
                   font, 0.5, (180, 180, 180), 1, cv2.LINE_AA)
        
        # 하단: 조작 힌트
        hints = [
            ("↑/W", "이전"),
            ("↓/S", "다음"),
            ("Space", "일시정지"),
            ("H", "UI 숨김"),
            ("Q", "종료")
        ]
        
        x_start = 20
        y_pos = h - 40
        for key, action in hints:
            text = f"{key}: {action}"
            cv2.putText(frame, text, (x_start, y_pos), 
                       font, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
            x_start += 130
        
        return frame
    
    def mouse_callback(self, event, x, y, flags, param):
        """마우스 드래그 스와이프 처리"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_down = True
            self.mouse_start_y = y
            self.swipe_action = None
        
        elif event == cv2.EVENT_LBUTTONUP:
            if self.mouse_down:
                delta_y = y - self.mouse_start_y
                if abs(delta_y) >= self.swipe_threshold:
                    if delta_y < 0:
                        # 드래그 위로 → 다음 영상
                        self.swipe_action = 'next'
                    else:
                        # 드래그 아래로 → 이전 영상
                        self.swipe_action = 'prev'
            self.mouse_down = False
    
    def play(self):
        """비디오 재생 메인 루프"""
        if not self.videos:
            print("videos 폴더에 동영상 파일이 없습니다!")
            return
        
        print(f"\n{'='*60}")
        print(f"  Video Transition Player")
        print(f"{'='*60}")
        print(f"총 {len(self.videos)}개의 동영상 발견\n")
        
        for i, video in enumerate(self.videos):
            print(f"  {i+1}. {os.path.basename(video)}")
        
        print(f"\n{'='*60}")
        print("조작법:")
        print("  ↑ / W    : 이전 영상")
        print("  ↓ / S    : 다음 영상")
        print("  마우스 드래그 ↑ : 다음 영상")
        print("  마우스 드래그 ↓ : 이전 영상")
        print("  Space    : 일시정지/재생")
        print("  H        : UI 표시/숨김")
        print("  Q        : 종료")
        print(f"{'='*60}\n")
        
        cap = cv2.VideoCapture(self.videos[self.current_index])
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 30  # 기본값
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 윈도우 설정
        window_name = 'Video Player'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.display_size[0], self.display_size[1])
        # 마우스 콜백 등록
        cv2.setMouseCallback(window_name, self.mouse_callback)
        # 창을 최상위로 설정 (포커스 문제 해결)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
        print("⚠️  OpenCV 창을 클릭하여 포커스를 맞춘 후 키를 눌러주세요!\n")
        print("🖱️  마우스 드래그로도 영상 전환이 가능합니다!\n")
        
        paused = False
        
        while True:
            if not paused:
                ret, frame = cap.read()
                
                # 현재 비디오 끝나면 처음부터 반복
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                
                if ret:
                    # 비율 유지하며 리사이즈
                    frame = self.resize_with_aspect_ratio(frame, self.display_size)
                    
                    # UI 오버레이 추가
                    current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                    frame = self.draw_ui_overlay(
                        frame, 
                        self.videos[self.current_index],
                        current_frame,
                        total_frames
                    )
                    
                    cv2.imshow(window_name, frame)
            
            # 키 입력 대기 (특수키 포함)
            wait_time = 1 if paused else int(1000 / fps)
            key = cv2.waitKeyEx(wait_time)
            
            # 마우스 스와이프 처리
            if self.swipe_action == 'next':
                next_index = (self.current_index + 1) % len(self.videos)
                self.transition_to_video(cap, next_index, 'down')
                cap.release()
                cap = cv2.VideoCapture(self.videos[next_index])
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.current_index = next_index
                paused = False
                print(f"🖱️ → {os.path.basename(self.videos[self.current_index])}")
                self.swipe_action = None
            elif self.swipe_action == 'prev':
                prev_index = (self.current_index - 1) % len(self.videos)
                self.transition_to_video(cap, prev_index, 'up')
                cap.release()
                cap = cv2.VideoCapture(self.videos[prev_index])
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.current_index = prev_index
                paused = False
                print(f"🖱️ ← {os.path.basename(self.videos[self.current_index])}")
                self.swipe_action = None
            
            # 디버깅 - 키 코드 출력 (원본과 마스킹 버전 모두)
            if key != -1 and key != 255:
                masked = key & 0xFF
                ch = chr(masked) if 32 <= masked <= 126 else 'N/A'
                print(f"Key pressed: {key}, masked: {masked}, char: {ch}")
            
            # 다음 영상 (s 또는 아래 화살표)
            # 소문자/대문자 모두 확인, 화살표는 다양한 코드 시도
            # 다음 영상: S/s 또는 아래 화살표 (2621440)
            if key in (ord('s'), ord('S'), 2621440):
                next_index = (self.current_index + 1) % len(self.videos)
                self.transition_to_video(cap, next_index, 'down')
                cap.release()
                cap = cv2.VideoCapture(self.videos[next_index])
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.current_index = next_index
                paused = False
                print(f"→ {os.path.basename(self.videos[self.current_index])}")
            
            # 이전 영상 (w 또는 위 화살표)
            # 소문자/대문자 모두 확인, 화살표는 다양한 코드 시도
            # 이전 영상: W/w 또는 위 화살표 (2490368)
            elif key in (ord('w'), ord('W'), 2490368):
                prev_index = (self.current_index - 1) % len(self.videos)
                self.transition_to_video(cap, prev_index, 'up')
                cap.release()
                cap = cv2.VideoCapture(self.videos[prev_index])
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.current_index = prev_index
                paused = False
                print(f"← {os.path.basename(self.videos[self.current_index])}")
            
            # 일시정지/재생
            elif key in (32, ord(' ')):  # Space
                paused = not paused
                print("⏸ 일시정지" if paused else "▶ 재생")
            
            # UI 토글
            elif key in (ord('h'), ord('H')):
                self.show_ui = not self.show_ui
                print(f"UI {'표시' if self.show_ui else '숨김'}")
            
            # 종료
            elif key in (ord('q'), ord('Q')):
                print("\n프로그램 종료")
                break
        
        cap.release()
        cv2.destroyAllWindows()
    
    def transition_to_video(self, current_cap, next_index, direction):
        """비디오 전환 효과"""
        # 현재 프레임
        current_frame = self.get_frame(current_cap, self.display_size)
        if current_frame is None:
            return
        
        # 다음 비디오의 첫 프레임
        next_cap = cv2.VideoCapture(self.videos[next_index])
        next_frame = self.get_frame(next_cap, self.display_size)
        next_cap.release()
        
        if next_frame is None:
            return
        
        # 전환 애니메이션 (transitions 모듈의 Transition 사용)
        for i in range(self.transition_frames):
            progress = (i + 1) / self.transition_frames
            # Ease-out 효과 (부드러운 감속)
            progress = 1 - (1 - progress) ** 3

            transition_frame = self.transition.render(
                current_frame, next_frame, progress, direction=direction
            )
            cv2.imshow('Video Player', transition_frame)
            cv2.waitKey(16)  # ~60fps