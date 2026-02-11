import sys
import vlc
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject

class SignalHandler(QObject):
    status_signal = Signal(str, str)

class RTSPPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("נגן RTSP - אתגר התאמה")
        self.resize(1000, 700)

        self.signals = SignalHandler()
        self.signals.status_signal.connect(self.update_status)

        # UI Elements
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("הזן כתובת RTSP (למשל: rtsp://127.0.0.1:554/stream)")
        self.url_input.setFixedHeight(40)
        self.url_input.setStyleSheet("font-size: 14px; padding: 5px;")
        
        self.play_button = QPushButton("Play / נגן")
        self.play_button.setFixedHeight(40)
        self.play_button.setFixedWidth(100)
        self.play_button.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #4CAF50; color: white;")
        self.play_button.clicked.connect(self.play_video)

        self.stop_button = QPushButton("Stop / עצור")
        self.stop_button.setFixedHeight(40)
        self.stop_button.setFixedWidth(100)
        self.stop_button.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #f44336; color: white;")
        self.stop_button.clicked.connect(self.stop_video)

        self.status_label = QLabel("מוכן")
        self.status_label.setStyleSheet("color: #555; font-size: 14px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignCenter)

        # Video Frame
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black; border: 2px solid #333;")

        # Layout
        main_layout = QVBoxLayout()
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.play_button)
        input_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.video_frame)
        main_layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # VLC Instance
        # verbose=2 adds detailed logs to the terminal
        self.instance = vlc.Instance("--no-xlib", "--verbose=2")
        self.mediaplayer = self.instance.media_player_new()

        # Set the video frame for VLC
        if sys.platform == "win32":
            self.mediaplayer.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":  # macOS
            self.mediaplayer.set_nsobject(int(self.video_frame.winId()))
        else:  # Linux (X11)
            self.mediaplayer.set_xwindow(int(self.video_frame.winId()))

        # Events
        self.event_manager = self.mediaplayer.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self.on_error)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self.on_playing)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerBuffering, self.on_buffering)

    def on_error(self, event):
        self.signals.status_signal.emit("שגיאה: לא ניתן להתחבר לזרם או שהכתובת לא תקינה", "red")

    def on_playing(self, event):
        self.signals.status_signal.emit("מנגן כעת", "green")

    def on_buffering(self, event):
        percent = event.u.new_cache
        self.signals.status_signal.emit(f"טוען... {percent}%", "orange")

    def update_status(self, text, color):
        # VLC callbacks are on a different thread, use QTimer or signals if UI updates fail
        # But setStyleSheet and setText on basic widgets usually work okay in PySide
        # However, it's safer to use a signal or QTimer for UI updates from callbacks.
        # For simplicity in this script, I'll use a local update method that might need a thread-safe approach.
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")

    def stop_video(self):
        self.mediaplayer.stop()
        self.update_status("נעצר", "blue")

    def play_video(self):
        url = self.url_input.text().strip()
        if not url:
            self.update_status("שגיאה: נא להזין כתובת", "red")
            return

        # ניקוי גרשיים
        url = url.replace('"', '').replace("'", "")
        
        # עצירה של ניגון קודם אם קיים
        self.mediaplayer.stop()

        print(f"DEBUG: מנסה לנגן: {url}")
        self.update_status("מתחבר...", "blue")
        
        try:
            import os
            # בדיקה אם זה קובץ מקומי
            if os.path.exists(url):
                print("DEBUG: מזוהה כקובץ מקומי")
                # המרה לנתיב אבסולוטי תקני עבור VLC
                abs_path = os.path.abspath(url)
                media = self.instance.media_new_path(abs_path)
            else:
                print("DEBUG: מזוהה ככתובת רשת")
                media = self.instance.media_new(url)
                if url.startswith("rtsp"):
                    media.add_option(":rtsp-tcp")
                    media.add_option(":network-caching=1500") # הגדלת באפר ליציבות
            
            self.mediaplayer.set_media(media)
            
            # וידוא מזהה החלון לפני הנגינה
            if sys.platform == "win32":
                self.mediaplayer.set_hwnd(int(self.video_frame.winId()))
            
            result = self.mediaplayer.play()
            if result == -1:
                self.update_status("VLC: שגיאה בהפעלת המדיה", "red")
        except Exception as e:
            print(f"DEBUG: Exception: {e}")
            self.update_status(f"שגיאת מערכת: {str(e)}", "red")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RTSPPlayer()
    window.show()
    sys.exit(app.exec())
