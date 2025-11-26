import serial
import time
import math
import keyboard
import threading
import sounddevice as sd
import soundfile as sf

#DMXケーブルのポート
PORT_DMX = 'COM6'
#Arduinoシリアル通信のポート
PORT_ARDUINO = 'COM5'
#What is This
BAUD_ARDUINO = 9600

#以前違う音楽再生関数の使いまわし
#このプログラムの場合使用している関数がWAVしか対応していないので注意
patterns = {
    '1': {'color': (255, 183, 197), 'music': 'test.wav'},
    '2': {'color': (173, 216, 230), 'music': '海岸4.mp3'},
    '3': {'color': (255, 90,   0),  'music': '水中.mp3'},
    '4': {'color': (200, 225, 255), 'music': '水のしたたる洞窟.mp3'},
}

pattern_keys = list(patterns.keys())
current_pattern_index = 0
current_key = pattern_keys[current_pattern_index]
current_thread = None
stop_flag = threading.Event()

dmx_data = bytearray([0] * 513)

def send_dmx(ser):
    ser.break_condition = True
    time.sleep(0.001)
    ser.break_condition = False
    time.sleep(0.001)
    ser.write(dmx_data)

#光の変化サイン波を使っている
#今後光度の変化だけじゃなく、色の変化も混ぜたい
def apply_color(base_r, base_g, base_b, t):
    r = min(255, max(0, base_r + int(10 * math.sin(t / 2))))
    g = min(255, max(0, base_g + int(10 * math.sin(t / 3))))
    b = min(255, max(0, base_b + int(10 * math.sin(t / 4))))
    master = int(127 * math.sin(t / 1.5) + 128)
    dmx_data[1:6] = bytes([r, g, b, master, 0])

#音楽再生
def play_looped_music(path):
    data, samplerate = sf.read(path, dtype='float32')
    while not stop_flag.is_set():
        sd.play(data, samplerate, blocking=True)
    sd.stop()

#ループ再生
def start_music_thread(path):
    global current_thread
    stop_music()
    stop_flag.clear()
    current_thread = threading.Thread(target=play_looped_music, args=(path,), daemon=True)
    current_thread.start()

#ループ終了
def stop_music():
    stop_flag.set()
    sd.stop()
    if current_thread and current_thread.is_alive():
        current_thread.join(timeout=1)

#パターン選択
def switch_to_pattern(index):
    global current_key
    current_key = pattern_keys[index % len(pattern_keys)]
    color = patterns[current_key]['color']
    music = patterns[current_key]['music']
    print(f"▶ パターン {current_key} に切り替え：{music}")
    start_music_thread(music)

def main():
    global current_pattern_index
    t = 0.0

    ser_dmx = serial.Serial(PORT_DMX, baudrate=250000, bytesize=8, stopbits=2, parity='N')
    ser_arduino = serial.Serial(PORT_ARDUINO, BAUD_ARDUINO, timeout=1)
    time.sleep(2)  # Arduino 初期化待ち

    print("🎵 [1]=桜 [2]=水色 [3]=紅葉 [4]=冬 [Esc]=終了")
    switch_to_pattern(current_pattern_index)

    try:
        while True:
            # キーボード入力処理
            for key in pattern_keys:
                if keyboard.is_pressed(key):
                    idx = pattern_keys.index(key)
                    if current_key != key:
                        current_pattern_index = idx
                        switch_to_pattern(current_pattern_index)
                        time.sleep(0.3)

            # Arduino からの入力チェック
            if ser_arduino.in_waiting:
                line = ser_arduino.readline().decode('utf-8').strip()
                if line == "Button Pressed":
                    print("🟢 ボタンが押されました！")
                    current_pattern_index = (current_pattern_index + 1) % len(pattern_keys)
                    switch_to_pattern(current_pattern_index)

            # ESCで終了
            if keyboard.is_pressed('esc'):
                print("❌ 終了します")
                break

            # 色の適用と送信
            if current_key:
                base_r, base_g, base_b = patterns[current_key]['color']
                apply_color(base_r, base_g, base_b, t)
                send_dmx(ser_dmx)

            t += 0.1
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("強制終了しました")

    finally:
        stop_music()
        ser_dmx.close()
        ser_arduino.close()

if __name__ == "__main__":
    main()
