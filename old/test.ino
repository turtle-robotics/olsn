/*
  MyoWare Example_01_analogRead_SINGLE
  SparkFun Electronics
  Pete Lewis
  3/24/2022
  License: This code is public domain but you buy me a beverage if you use this and we meet someday.
  This code was adapted from the MyoWare analogReadValue.ino example found here:
  https://github.com/AdvancerTechnologies/MyoWare_MuscleSensor

  This example streams the data from a single MyoWare sensor attached to ADC A0.
  Graphical representation is available using Serial Plotter (Tools > Serial Plotter menu).

  *Only run on a laptop using its battery. Do not plug in laptop charger/dock/monitor.
  
  *Do not touch your laptop trackpad or keyboard while the MyoWare sensor is powered.

  Hardware:
  SparkFun RedBoard Artemis (or Arduino of choice)
  USB from Artemis to Computer.
  Output from sensor connected to your Arduino pin A0
  
  This example code is in the public domain.
*/

const int THRESHOLD = 350; // adjust for open/closed hand detection
const int WINDOW_SIZE = 10; // moving average window (higher = smoother, more lag)

const int MOTOR_PWM_PIN = 2; // PWM speed control
const int MOTOR_DIR_PIN_A = 5; // direction/enable
const int MOTOR_DIR_PIN_B = 4; // direction/enable
const int MOTOR_PWM_MIN = 0; // minimum PWM once above threshold
const int MOTOR_PWM_MAX = 150; // maximum PWM
const int MOTOR_PWM_REVERSE = 150; // reverse speed when returning to zero
const int PWM_REVERSE_THRESHOLD = 130; // reverse to zero when below this
const int EMG_MAX = 500; // max ADC value (12-bit)
const float ADC_REF_VOLTAGE = 3.3f; // volts
const int ENCODER_PIN_A = 3; // encoder A
const int ENCODER_PIN_B = 6; // encoder B

volatile long encoderCount = 0;
static int lastEncA = LOW;
static int lastEncB = LOW;

void updateEncoderISR()
{
  int encA = digitalRead(ENCODER_PIN_A);
  int encB = digitalRead(ENCODER_PIN_B);

  if (encA != lastEncA) {
    // If B is different from A, direction is forward; else reverse
    encoderCount += (encA != encB) ? 1 : -1;
  }

  lastEncA = encA;
  lastEncB = encB;
}

void setup() 
{
  Serial.begin(115200);
  while (!Serial); // optionally wait for serial terminal to open
  Serial.println("MyoWare Example_01_analogRead_SINGLE");
  Serial.println("Raw,Filtered,Threshold,Hand,PWM,Voltage"); // labels for Serial Plotter


  pinMode(MOTOR_PWM_PIN, OUTPUT);
  pinMode(MOTOR_DIR_PIN_A, OUTPUT);
  pinMode(MOTOR_DIR_PIN_B, OUTPUT);
  pinMode(ENCODER_PIN_A, INPUT_PULLUP);
  pinMode(ENCODER_PIN_B, INPUT_PULLUP);
  lastEncA = digitalRead(ENCODER_PIN_A);
  lastEncB = digitalRead(ENCODER_PIN_B);
  attachInterrupt(digitalPinToInterrupt(ENCODER_PIN_A), updateEncoderISR, CHANGE);
  analogWrite(MOTOR_PWM_PIN, 0);
  digitalWrite(MOTOR_DIR_PIN_A, LOW);
  digitalWrite(MOTOR_DIR_PIN_B, LOW);
}

void loop() 
{  
  int sensorValue = analogRead(A0); // read the input on analog pin A0
  static int samples[WINDOW_SIZE] = {0};
  static int index = 0;
  static long sum = 0;

  sum -= samples[index];
  samples[index] = sensorValue;
  sum += samples[index];
  index = (index + 1) % WINDOW_SIZE;

  int filteredValue = sum / WINDOW_SIZE;
  int pwmValue = 0;
  float emgVoltage = filteredValue; //(filteredValue * ADC_REF_VOLTAGE) / EMG_MAX;

  pwmValue = constrain(filteredValue*0.4, MOTOR_PWM_MIN, MOTOR_PWM_MAX);


  if (pwmValue >= PWM_REVERSE_THRESHOLD && encoderCount < 1000) {
    // Forward drive when above threshold
    analogWrite(MOTOR_PWM_PIN, pwmValue);
    digitalWrite(MOTOR_DIR_PIN_A, LOW);
    digitalWrite(MOTOR_DIR_PIN_B, HIGH);
  } else if (encoderCount > 50) {
    // Reverse until we reach zero position
    analogWrite(MOTOR_PWM_PIN, MOTOR_PWM_REVERSE);
    digitalWrite(MOTOR_DIR_PIN_A, HIGH);
    digitalWrite(MOTOR_DIR_PIN_B, LOW);
  } else if (encoderCount < 0) {
    analogWrite(MOTOR_PWM_PIN, MOTOR_PWM_REVERSE);
    digitalWrite(MOTOR_DIR_PIN_A, LOW);
    digitalWrite(MOTOR_DIR_PIN_B, HIGH);
  } else {
    // At zero, stop
    analogWrite(MOTOR_PWM_PIN, 0);
    digitalWrite(MOTOR_DIR_PIN_A, LOW);
    digitalWrite(MOTOR_DIR_PIN_B, LOW);
  }

  Serial.print(sensorValue);
  Serial.print(",");
  Serial.print((int)filteredValue);
  Serial.print(",");
  Serial.print(THRESHOLD);
  Serial.print(",");
  Serial.print(pwmValue);
  Serial.print(",");
  Serial.print(emgVoltage, 3);
  Serial.print(",");
  long encoderSnapshot;
  noInterrupts();
  encoderSnapshot = encoderCount;
  interrupts();
  Serial.println(encoderSnapshot);

  delay(5); // to avoid overloading the serial terminal
}