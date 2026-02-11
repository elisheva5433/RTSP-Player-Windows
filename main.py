import sys
import vlc
import os
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame, QSlider
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject

class SignalHandler(QObject):
    status_signal = Signal(str, str)

class RTSPPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro RTSP Player")
        self.resize(1100, 800)

        # עיצוב מודרני - Dark Mode
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QLineEdit { 
                background-color: #1e1e1e; color: #ffffff; border: 1px solid #333; 
                padding: 10px; border-radius: 5px; font-size: 14px;
            }
            QPushButton { 
                background-color: #333333; color: white; border: none; 
                padding: 10px 15px; border-radius: 5px; font-weight: bold; min-width: 80px;
            }
            QPushButton:hover { background-color: #444444; }
            #play_btn { background-color: #2e7d32; min-width: 100px; }
            #play_btn:hover { background-color: #388e3c; }
            #stop_btn { background-color: #c62828; min-width: 100px; }
            #stop_btn:hover { background-color: #d32f2f; }
            #skip_btn { background-color: #424242; min-width: 60px; }
            #snap_btn { background-color: #1565c0; }
            #snap_btn:hover { background-color: #1976d2; }
            QLabel { color: #bbbbbb; font-family: 'Segoe UI', sans-serif; }
            QSlider::handle:horizontal { background: #1565c0; width: 14px; border-radius: 7px; margin: -5px 0; }
            QSlider::groove:horizontal { background: #333; height: 4px; border-radius: 2px; }
        """)

        self.signals = SignalHandler()
        self.signals.status_signal.connect(self.update_status)

        # UI Elements
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("הזן כתובת RTSP או גרור קובץ לכאן...")
        
        self.play_button = QPushButton("▶ נגן")
        self.play_button.setObjectName("play_btn")
        self.play_button.clicked.connect(self.play_pause_toggle)

        self.stop_button = QPushButton("■ עצור")
        self.stop_button.setObjectName("stop_btn")
        self.stop_button.clicked.connect(self.stop_video)
        
        self.snap_button = QPushButton("📷 צילום מסך")
        self.snap_button.setObjectName("snap_btn")
        self.snap_button.clicked.connect(self.take_snapshot)

        self.back_button = QPushButton("<< 10 שניות")
        self.back_button.setObjectName("skip_btn")
        self.back_button.clicked.connect(lambda: self.jump_time(-10000))

        self.fwd_button = QPushButton("10 שניות >>")
        self.fwd_button.setObjectName("skip_btn")
        self.fwd_button.clicked.connect(lambda: self.jump_time(10000))

        # Seek Slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderMoved.connect(self.set_video_position)
        self.seek_slider.sliderPressed.connect(self.start_seeking)
        self.seek_slider.sliderReleased.connect(self.end_seeking)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #333;
                height: 6px;
                background: #222;
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #1565c0;
                border: 1px solid #1565c0;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #1976d2;
                border-radius: 3px;
            }
        """)

        # Volume Controls
        self.vol_label = QLabel("עוצמה: 70%")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.setFixedWidth(150)
        self.vol_slider.valueChanged.connect(self.change_volume)

        self.status_label = QLabel("מוכן")
        self.status_label.setAlignment(Qt.AlignCenter)

        # Video Frame
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: #000000; border-radius: 8px; border: 1px solid #222;")

        # Layouts
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        
        # Row 1: URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(self.url_input)
        main_layout.addLayout(url_layout)
        
        # Row 2: Video
        main_layout.addWidget(self.video_frame, stretch=1)

        # Row 3: Seek Bar
        main_layout.addWidget(self.seek_slider)
        
        # Row 4: Centralized Controls
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        controls_layout.addWidget(self.back_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.fwd_button)
        controls_layout.addStretch()
        
        main_layout.addLayout(controls_layout)
        
        # Row 5: Bottom Tools (Volume, Snapshot, Status)
        bottom_tools = QHBoxLayout()
        bottom_tools.addWidget(self.snap_button)
        bottom_tools.addStretch()
        bottom_tools.addWidget(self.vol_label)
        bottom_tools.addWidget(self.vol_slider)
        
        main_layout.addLayout(bottom_tools)
        main_layout.addWidget(self.status_label)

        self.setCentralWidget(container)

        self.is_seeking = False
        self.update_timer = QTimer()
        self.update_timer.setInterval(50) # Reduced from 200ms to 50ms for smoother updates
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start()

        # VLC
        self.instance = vlc.Instance("--no-xlib", "--quiet")
        self.mediaplayer = self.instance.media_player_new()
        self.mediaplayer.audio_set_volume(70)

        if sys.platform == "win32":
            self.mediaplayer.set_hwnd(int(self.video_frame.winId()))

        # Events
        self.event_manager = self.mediaplayer.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self.on_error)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self.on_playing)

    def change_volume(self, value):
        self.mediaplayer.audio_set_volume(value)
        self.vol_label.setText(f"עוצמה: {value}%")

    def play_pause_toggle(self):
        state = self.mediaplayer.get_state()
        if state in [vlc.State.NothingSpecial, vlc.State.Stopped, vlc.State.Ended, vlc.State.Error]:
            self.play_video()
        elif state == vlc.State.Playing:
            self.mediaplayer.pause()
            self.update_status("מושהה", "orange")
        else: # Paused
            self.mediaplayer.play()
            self.update_status("מנגן כעת", "#2e7d32")

    def jump_time(self, ms):
        """jump forward or backward in milliseconds"""
        curr_time = self.mediaplayer.get_time()
        if curr_time != -1:
            self.mediaplayer.set_time(curr_time + ms)

    def start_seeking(self):
        self.is_seeking = True

    def end_seeking(self):
        self.is_seeking = False
        self.mediaplayer.set_position(self.seek_slider.value() / 1000.0)

    def set_video_position(self, value):
        if self.is_seeking:
            self.mediaplayer.set_position(value / 1000.0)

    def update_ui(self):
        """Update the seek slider and sync button state"""
        state = self.mediaplayer.get_state()
        
        # סנכרון טקסט הכפתור לפי מצב הנגן
        if state == vlc.State.Playing:
            self.play_button.setText("Ⅱ השהה")
        else:
            self.play_button.setText("▶ נגן")
            
        # סנכרון הודעת סטטוס בסיום
        if state == vlc.State.Ended:
            self.update_status("הסרטון הסתיים", "#bbbbbb")

        if self.mediaplayer.is_playing() and not self.is_seeking:
            pos = self.mediaplayer.get_position()
            if pos > 0:
                self.seek_slider.setValue(int(pos * 1000))
            
            # Check length to enable/disable seeking
            length = self.mediaplayer.get_length()
            if length <= 0: # Likely a live stream
                self.seek_slider.setEnabled(False)
                self.back_button.setEnabled(False)
                self.fwd_button.setEnabled(False)
            else:
                self.seek_slider.setEnabled(True)
                self.back_button.setEnabled(True)
                self.fwd_button.setEnabled(True)

    def take_snapshot(self):
        if not self.mediaplayer.is_playing():
            self.update_status("נגן משהו לפני צילום מסך", "orange")
            return
            
        # שימוש בתיקיית התמונות האישית של המשתמש (יותר בטוח לעברית)
        pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.abspath(os.path.join(pictures_dir, f"snap_{timestamp}.png"))
        
        # ב-Windows, VLC מעדיף נתיב נקי ומנורמל
        clean_path = os.path.normpath(filename)
        
        # ביצוע הצילום
        result = self.mediaplayer.video_take_snapshot(0, clean_path, 0, 0)
        
        if result == 0:
            self.update_status(f"צילום נשמר בתיקיית התמונות!", "#1565c0")
        else:
            self.update_status("שגיאה בשמירת הצילום", "#c62828")

    def on_error(self, event):
        self.signals.status_signal.emit("שגיאה בחיבור לזרם", "#c62828")

    def on_playing(self, event):
        self.signals.status_signal.emit("מנגן כעת", "#2e7d32")

    def update_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")

    def stop_video(self):
        self.mediaplayer.stop()
        self.play_button.setText("▶ נגן")
        self.update_status("נעצר", "#bbbbbb")

    def play_video(self):
        url = self.url_input.text().strip().replace('"', '').replace("'", "")
        if not url:
            self.update_status("נא להזין כתובת", "orange")
            return

        self.update_status("מתחבר...", "#1565c0")
        
        if os.path.exists(url):
            media = self.instance.media_new_path(os.path.abspath(url))
        else:
            media = self.instance.media_new(url)
            if url.startswith("rtsp"):
                media.add_option(":rtsp-tcp")
                media.add_option(":network-caching=1500")
        
        self.mediaplayer.set_media(media)
        self.mediaplayer.play()
        self.play_button.setText("Ⅱ השהה")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RTSPPlayer()
    window.show()
    sys.exit(app.exec())
