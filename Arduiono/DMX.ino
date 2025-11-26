const int buttonPin = 2;
const int sensorPins[3] = {A0, A2, A6};
const int threshold = 500;  // 明るさのしきい値（環境に応じて調整）

bool lastButtonState = HIGH; // プルアップ使用（未押下はHIGH）
bool lastSensorStates[3] = {false, false, false};

void setup() {
  Serial.begin(9600);  // シリアル通信開始
  pinMode(buttonPin, INPUT_PULLUP);
  
  for (int i = 0; i < 3; i++) {
    pinMode(sensorPins[i], INPUT);
  }
}

void loop() {
  // --- ボタンの状態確認 ---
  bool buttonState = digitalRead(buttonPin);
  if (buttonState == LOW && lastButtonState == HIGH) {
    Serial.println("Button Pressed");
  }
  lastButtonState = buttonState;

  // --- 光センサーの状態確認 ---
  for (int i = 0; i < 3; i++) {
    int sensorValue = analogRead(sensorPins[i]);
    bool isBright = sensorValue > threshold;

    // 明るくなった瞬間にメッセージ送信
    if (isBright && !lastSensorStates[i]) {
      Serial.print("Sensor ");
      Serial.print(i + 1);
      Serial.println(" Bright");
    }

    // 状態更新
    lastSensorStates[i] = isBright;
  }

  delay(100);  // 10秒ごとにチェック
}
