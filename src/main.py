from video_player import VideoPlayer
import os

def main():
    # videos 폴더의 동영상을 자동으로 로드
    # src 폴더에서 실행하므로 상위 폴더의 videos를 참조
    video_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'videos')
    player = VideoPlayer(video_folder=video_folder)
    player.play()

if __name__ == "__main__":
    main()