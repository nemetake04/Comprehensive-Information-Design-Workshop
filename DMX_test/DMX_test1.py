import serial
import time
import math
import keyboard
import threading
import sounddevice as sd
import soundfile as sf

PORT = 'COM6'

# sounddvice はWAVファイルしか認識しないので注意
#ここで色のパターンと音声ファイルを一括管理
patterns = {
    '1': {'color': (255, 183, 197), 'music': 'test.wav'},
    '2': {'color': (173, 216, 230), 'music': '海岸4.mp3'},
    '3': {'color': (255, 90,   0),  'music': '水中.mp3'},
    '4': {'color': (200, 225, 255), 'music': '水のしたたる洞窟.mp3'},
}

dmx_data = bytearray([0] * 513)
current_key = None
current_thread = None
stop_flag = threading.Event()

def send_dmx(ser):
    ser.break_condition = True
    time.sleep(0.001)
    ser.break_condition = False
    time.sleep(0.001)
    ser.write(dmx_data)

#色に揺らぎを追加
def apply_color(base_r, base_g, base_b, t):
    r = min(255, max(0, base_r + int(10 * math.sin(t / 2))))
    g = min(255, max(0, base_g + int(10 * math.sin(t / 3))))
    b = min(255, max(0, base_b + int(10 * math.sin(t / 4))))
    master = int(127 * math.sin(t / 1.5) + 128)

    dmx_data[1] = r
    dmx_data[2] = g
    dmx_data[3] = b
    dmx_data[4] = master
    dmx_data[5] = 0

def play_looped_music(path):
    data, samplerate = sf.read(path, dtype='float32')
    while not stop_flag.is_set():
        sd.play(data, samplerate, blocking=True)
    sd.stop()

def start_music_thread(path):
    global current_thread
    stop_music()
    stop_flag.clear()
    current_thread = threading.Thread(target=play_looped_music, args=(path,), daemon=True)
    current_thread.start()

def stop_music():
    stop_flag.set()
    sd.stop()
    if current_thread and current_thread.is_alive():
        current_thread.join(timeout=1)

def main():
    global current_key
    t = 0.0

    with serial.Serial(PORT, baudrate=250000, bytesize=8, stopbits=2, parity='N') as ser:
        print("🎵 [1]=桜 [2]=水色 [3]=紅葉 [4]=冬 [Esc]=終了")

        while True:
            for key in patterns:
                if keyboard.is_pressed(key):
                    if current_key != key:
                        current_key = key
                        color = patterns[key]['color']
                        music = patterns[key]['music']
                        print(f"▶ パターン {key} に切り替え：{music}")
                        start_music_thread(music)
                        time.sleep(0.3)

            if keyboard.is_pressed('esc'):
                print("❌ 終了します")
                stop_music()
                break

            if current_key:
                base_r, base_g, base_b = patterns[current_key]['color']
                apply_color(base_r, base_g, base_b, t)
                send_dmx(ser)

            t += 0.1
            time.sleep(0.05)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_music()
        print("強制終了しました")
