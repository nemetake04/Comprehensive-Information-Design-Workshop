import serial
import time
import math
import keyboard
import threading
import sounddevice as sd
import soundfile as sf

# DMXケーブルのポート
PORT_DMX = 'COM6'
# Arduinoシリアル通信のポート
PORT_ARDUINO = 'COM5'
BAUD_ARDUINO = 9600

# プリセット定義
patterns = {
    '1': {
        'start_color': (0, 255, 0),
        'end_color': (255, 0, 190),
        'music': 'music_spring.wav'
    },
    '2': {
        'start_color': (0, 255, 0),
        'end_color': (50, 50, 255),
        'music': 'music_summer.wav'
    },
    '3': {
        'start_color': (40, 196, 40),
        'end_color': (255, 70, 0),
        'music': 'music_autumn.wav'
    },
    '4': {
        'start_color': (200, 225, 255),
        'end_color': (40, 255, 100),
        'music': 'music_winter.wav'
    }
}

pattern_keys = list(patterns.keys())
current_pattern_index = 0
current_key = pattern_keys[current_pattern_index]
current_music_key = current_key
current_thread = None
stop_flag = threading.Event()

dmx_data = bytearray([0] * 513)
last_switch_time = 0

def lerp(a, b, t):
    return int(a + (b - a) * t)

def send_dmx(ser):
    ser.break_condition = True
    time.sleep(0.001)
    ser.break_condition = False
    time.sleep(0.001)
    ser.write(dmx_data)

def apply_color(t_global, t_local):
    start_r, start_g, start_b = patterns[current_key]['start_color']
    end_r, end_g, end_b = patterns[current_key]['end_color']

    color_progress = min(1.0, max(0.0, (t_local - 15.0) / 5.0))
    r = lerp(start_r, end_r, color_progress)
    g = lerp(start_g, end_g, color_progress)
    b = lerp(start_b, end_b, color_progress)

    r = min(255, max(0, r + int(10 * math.sin(t_global / 2))))
    g = min(255, max(0, g + int(10 * math.sin(t_global / 3))))
    b = min(255, max(0, b + int(10 * math.sin(t_global / 4))))

    fade_progress = min(1.0, t_local / 2.0)
    r = int(r * fade_progress)
    g = int(g * fade_progress)
    b = int(b * fade_progress)
    master = int(127 * math.sin(t_global / 1.5) + 128)
    master = int(master * fade_progress)

    dmx_data[1:6] = bytes([r, g, b, master, 0])

def play_looped_music(path):
    data, samplerate = sf.read(path, dtype='float32')
    while not stop_flag.is_set():
        sd.play(data, samplerate, blocking=True)
    sd.stop()

def play_once_sound(path):
    def play():
        try:
            data, samplerate = sf.read(path, dtype='float32')
            sd.play(data, samplerate, blocking=True)
        except Exception as e:
            print(f"⚠ 音声再生エラー: {e}")
    threading.Thread(target=play, daemon=True).start()

def start_music_thread(path):
    global current_thread
    stop_music()
    if current_thread and current_thread.is_alive():
        current_thread.join(timeout=1)
    stop_flag.clear()
    current_thread = threading.Thread(target=play_looped_music, args=(path,), daemon=True)
    current_thread.start()

def stop_music():
    stop_flag.set()
    sd.stop()
    if current_thread and current_thread.is_alive():
        current_thread.join(timeout=1)

def initialize_pattern(index):
    global current_key, current_music_key, current_pattern_index, t_local
    current_pattern_index = index % len(pattern_keys)
    current_key = pattern_keys[current_pattern_index]
    current_music_key = current_key
    music = patterns[current_music_key]['music']
    print(f"▶ 初期パターン {current_key}：{music}")
    start_music_thread(music)
    t_local = 0.0

def switch_to_pattern(index):
    global current_key, current_music_key, current_pattern_index, t_local, last_switch_time, music3_played
    now = time.time()
    if now - last_switch_time < 0.5:
        print("⏳ 切り替え間隔が短すぎるため無視")
        return
    last_switch_time = now
    current_pattern_index = index % len(pattern_keys)
    current_key = pattern_keys[current_pattern_index]
    current_music_key = current_key
    music = patterns[current_music_key]['music']
    print(f"▶ 切り替え → パターン {current_key}：{music}")
    start_music_thread(music)
    t_local = 0.0
    music3_played = False


def main():
    global current_pattern_index, current_key, t_local
    t_global = 0.0
    t_local = 0.0
    last_announcement_time = -1
    pattern_active = False

    ser_dmx = serial.Serial(PORT_DMX, baudrate=250000, bytesize=8, stopbits=2, parity='N')
    ser_arduino = serial.Serial(PORT_ARDUINO, BAUD_ARDUINO, timeout=1)
    time.sleep(2)
    start_time = time.time()

    print("🎵 起動しました。Arduinoの入力待機中（ボタン or 光センサー）")

    try:
        while True:
            for key in pattern_keys:
                if keyboard.is_pressed(key):
                    idx = pattern_keys.index(key)
                    if not pattern_active or current_key != key:
                        switch_to_pattern(idx)
                        pattern_active = True
                        last_announcement_time = -1
                        t_global = 0.0
                        time.sleep(0.3)

            if ser_arduino.in_waiting:
                if time.time() - start_time < 1.0:
                    ser_arduino.readline()
                else:
                    line = ser_arduino.readline().decode('utf-8').strip()
                    if line == "Button Pressed":
                        print("🟢 ボタンが押されました！")
                        if not pattern_active or current_key != pattern_keys[0]:
                            switch_to_pattern(0)
                            pattern_active = True
                            last_announcement_time = -1
                            t_global = 0.0
                    elif line == "Sensor 1 Bright":
                        print("🟡 センサー1が明るい！")
                        if not pattern_active or current_key != pattern_keys[1]:
                            switch_to_pattern(1)
                            pattern_active = True
                            last_announcement_time = -1
                            t_global = 0.0
                    elif line == "Sensor 2 Bright":
                        print("🟠 センサー2が明るい！")
                        if not pattern_active or current_key != pattern_keys[2]:
                            switch_to_pattern(2)
                            pattern_active = True
                            last_announcement_time = -1
                            t_global = 0.0
                    elif line == "Sensor 3 Bright":
                        print("🔴 センサー3が明るい！")
                        if not pattern_active or current_key != pattern_keys[3]:
                            switch_to_pattern(3)
                            pattern_active = True
                            last_announcement_time = -1
                            t_global = 0.0

            if pattern_active:
                remaining = int(20 - t_local)

                if 0 < remaining <= 10 and remaining != last_announcement_time:
                    print(f"🎚 {remaining}秒後に色が変化します…")
                    last_announcement_time = remaining
                elif remaining == 0 and last_announcement_time != 0:
                    print("🌈 色が変化しました！")
                    last_announcement_time = 0

                apply_color(t_global, t_local)
                send_dmx(ser_dmx)

                t_global += 0.05
                t_local += 0.05

            time.sleep(0.05)

            if keyboard.is_pressed('esc'):
                print("❌ 終了します")
                break

    except KeyboardInterrupt:
        print("強制終了しました")

    finally:
        stop_music()
        ser_dmx.close()
        ser_arduino.close()


if __name__ == "__main__":
    main()
