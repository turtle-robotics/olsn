/******************************************************
 * ESP32 (Arduino Core 3.3.x) + 4 x N20 DC Motors with Encoders
 * - Uses LEDC API: ledcAttach(pin, freq, resolution), ledcWrite(pin, duty)
 * - Position in encoder ticks (HIGH counts), not degrees
 * - Per-motor:
 *    - Position (ticks)
 *    - Speed (ticks/s)
 *    - Simple position control (target ticks)
 * - Set target positions via Serial:
 *    - "A 360"   -> Motor A to 360 ticks
 *    - "B 1000"  -> Motor B to 1000 ticks
 *    - "C 500"   -> Motor C to 500 ticks
 *    - "D 0"     -> Motor D to 0 ticks
 * - Motors DO NOT move until a serial command is received.
 ******************************************************/

#include <Arduino.h>

// ======================== PIN DEFINITIONS ========================

// Motor driver IN pins [IN1, IN2] per motor
const int MOTOR_IN[4][2] = {
  {25, 26},   // Motor A
  {33, 32},   // Motor B
  {0, 0},   // Motor C
  {0, 0},   // Motor D
};

// PWM pins per motor
const int MOTOR_PWM[4] = {22, 23, 0, 0};

// Encoder Phase-A and Phase-B pins per motor
const DRAM_ATTR int ENC_A[4] = {18, 5, 0,  0};
const DRAM_ATTR int ENC_B[4] = {19, 17, 0, 0};

// ======================== CONSTANTS ========================

const uint32_t pwmFreq       = 20000;
const uint8_t  pwmResolution = 8;       // 8-bit (0–255)

const int   baseDuty[4]  = {150, 150, 150, 150};  // tune per motor if needed
const float kp           = 1.2f;
const float kd           = 0.8f;   // derivative gain — increase to damp overshoot more
const long  TICK_TOL     = 5;

// ======================== MOTOR STATE ========================

// DRAM_ATTR ensures the ISR can always access this safely
volatile DRAM_ATTR long ticks[4] = {0, 0, 0, 0};
         long lastTicks[4] = {0, 0, 0, 0};
         float speed[4]    = {0, 0, 0, 0};   // ticks/s

long  targetTicks[4]  = {0, 0, 0, 0};
bool  controlEnabled  = false;

unsigned long lastSpeedUpdateMs = 0;

// ======================== ENCODER ISRs ========================
// One ISR per motor; reads Phase-B at the moment Phase-A rises.

// Each ISR hardcodes its own Phase-B pin read.
// Avoid indexing arrays inside IRAM_ATTR — the array pointer lives in flash
// and can cause a cache miss / crash during flash operations.
void IRAM_ATTR encISR_A() { ticks[0] += (digitalRead(32) == HIGH) ? 1 : -1; }
void IRAM_ATTR encISR_B() { ticks[1] += (digitalRead(34) == HIGH) ? 1 : -1; }
void IRAM_ATTR encISR_C() { ticks[2] += (digitalRead(21) == HIGH) ? 1 : -1; }
void IRAM_ATTR encISR_D() { ticks[3] += (digitalRead(15) == HIGH) ? 1 : -1; }

void (*encISRs[4])() = {encISR_A, encISR_B, encISR_C, encISR_D};

// ======================== MOTOR HELPERS ========================

void motorForward(int m) {
  digitalWrite(MOTOR_IN[m][0], HIGH);
  digitalWrite(MOTOR_IN[m][1], LOW);
}
void motorReverse(int m) {
  digitalWrite(MOTOR_IN[m][0], LOW);
  digitalWrite(MOTOR_IN[m][1], HIGH);
}
void motorStop(int m) {
  // Active brake: both pins HIGH shorts the motor terminals and resists motion
  digitalWrite(MOTOR_IN[m][0], HIGH);
  digitalWrite(MOTOR_IN[m][1], HIGH);
}
void motorSetSpeed(int m, int duty) {
  duty = constrain(duty, 0, 255);
  ledcWrite(MOTOR_PWM[m], duty);
}

// ======================== SETUP ========================

void setup() {
  Serial.begin(115200);

  for (int m = 0; m < 4; m++) {
    // Driver pins
    pinMode(MOTOR_IN[m][0], OUTPUT);
    pinMode(MOTOR_IN[m][1], OUTPUT);
    pinMode(MOTOR_PWM[m],   OUTPUT);

    // Encoder pins
    pinMode(ENC_A[m], INPUT_PULLUP);
    pinMode(ENC_B[m], INPUT_PULLUP);

    // LEDC
    ledcAttach(MOTOR_PWM[m], pwmFreq, pwmResolution);

    // Start stopped
    motorStop(m);
    motorSetSpeed(m, 0);

    // ISR on Phase-A rising edge
    attachInterrupt(digitalPinToInterrupt(ENC_A[m]), encISRs[m], RISING);
  }

  lastSpeedUpdateMs = millis();
  controlEnabled    = false;

  Serial.println("--- SYSTEM RESTARTED ---");
  Serial.println("Motors will NOT move until you send a command.");
  Serial.println("Commands: A 360  B 1000  C 500  D -200  (ticks)");
}

// ======================== SPEED UPDATE ========================

void updateSpeeds() {
  unsigned long now  = millis();
  unsigned long dtMs = now - lastSpeedUpdateMs;
  if (dtMs < 100) return;
  lastSpeedUpdateMs = now;
  float dtSec = dtMs / 1000.0f;

  for (int m = 0; m < 4; m++) {
    long cur;
    noInterrupts(); cur = ticks[m]; interrupts();
    long d = cur - lastTicks[m];
    lastTicks[m] = cur;
    speed[m] = d / dtSec;
  }
}

// ======================== POSITION CONTROL ========================

void updatePositionControl(int m) {
  long cur;
  noInterrupts(); cur = ticks[m]; interrupts();

  long err = targetTicks[m] - cur;

  if (labs(err) <= TICK_TOL) {
    motorStop(m);
    motorSetSpeed(m, 0);
    return;
  }

  // PD output: proportional pulls toward target, derivative brakes when approaching fast
  // speed[m] sign: positive = moving in the positive-tick direction
  float pd = (labs(err) * kp) - (speed[m] * kd);

  // Anti-stall floor only when far from target; close in, let duty go low naturally
  int duty = (int)pd;
  if (labs(err) > 50 && duty < 70) duty = 70;
  if (duty < 0)   duty = 0;
  if (duty > 255) duty = 255;

  if (err > 0) { motorForward(m); motorSetSpeed(m, duty); }
  else         { motorReverse(m); motorSetSpeed(m, duty); }
}

// ======================== SERIAL COMMAND ========================

void readSerialCommand() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() < 3) return;

  char mc = toupper(line.charAt(0));
  int  m  = -1;
  if      (mc == 'A') m = 0;
  else if (mc == 'B') m = 1;
  else if (mc == 'C') m = 2;
  else if (mc == 'D') m = 3;

  if (m < 0) {
    Serial.println("Unknown motor. Use A, B, C, or D.");
    return;
  }

  int spaceIdx = line.indexOf(' ');
  if (spaceIdx < 0) return;

  String valStr = line.substring(spaceIdx + 1);
  valStr.trim();
  if (valStr.length() == 0) return;

  long target = valStr.toInt();
  targetTicks[m] = target;
  controlEnabled  = true;

  Serial.print("Motor "); Serial.print(mc);
  Serial.print(" -> target: "); Serial.print(target);
  Serial.println(" ticks");
}

// ======================== MAIN LOOP ========================

void loop() {
  readSerialCommand();
  updateSpeeds();

  if (controlEnabled) {
    for (int m = 0; m < 4; m++) {
      updatePositionControl(m);
    }
  }

  // Periodic debug print every 200 ms
  static unsigned long lastPrint = 0;
  unsigned long now = millis();
  if (now - lastPrint >= 200) {
    lastPrint = now;

    long cur[4];
    noInterrupts();
    for (int m = 0; m < 4; m++) cur[m] = ticks[m];
    interrupts();

    const char names[] = "ABCD";
    Serial.println("==== Motor States ====");
    for (int m = 0; m < 4; m++) {
      Serial.print("Motor "); Serial.print(names[m]);
      Serial.print(" | target: "); Serial.print(targetTicks[m]);
      Serial.print("  pos: ");    Serial.print(cur[m]);
      Serial.print("  speed: ");  Serial.print(speed[m], 1);
      Serial.println(" ticks/s");
    }
    Serial.println("----------------------");
  }
}
