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
 *    - "C 0"     -> Motor C to tick 0 (if you reset ticks)
 * - Motors DO NOT move until a serial command is received.
 ******************************************************/

#include <Arduino.h>

// ======================== PIN DEFINITIONS ========================

// Motor A
const int MOTOR_AIN[2] = {35, 32};   // IN1, IN2 to driver
const int MOTOR_APWM   = 23;         // PWM to driver

// Encoders (Phase A only, one per motor)
const int ENC_APIN = 14;
const int ENC_BPIN = 12;

// ======================== CONSTANTS ========================

// PWM settings
const uint32_t pwmFreq       = 20000;   // 20 kHz
const uint8_t  pwmResolution = 8;       // 8-bit (0–255)

// Base duty when moving (tune as needed; 0–255)
int baseDutyA = 150;

float kp = 1.2;
// ======================== ENCODER STATE ========================

volatile long ticksA = 0;

volatile long lastTicksA = 0;

float speedA_ticksPerSec = 0.0f;

unsigned long lastSpeedUpdateMs = 0;

// ======================== POSITION-CONTROL STATE (IN TICKS) ========================

long targetTicksA = 0;

// Tolerance in ticks: how close is "good enough"
const long TICK_TOLERANCE = 5;   // e.g., within ±5 encoder counts

// Control active flag
bool anyControlEnabled = false;

// ======================== ENCODER ISRs ========================

// Count rising edges on Phase A for each motor

void IRAM_ATTR handleEncoder() {
  int bState = digitalRead(ENC_BPIN);
  if (bState == HIGH) {
    ticksA++; // Spinning one way
  } else {
    ticksA--; // Spinning the other way
  }
}

// ======================== MOTOR HELPERS ========================

// ----- Motor A -----
void motorA_forward() { digitalWrite(MOTOR_AIN[0], HIGH); digitalWrite(MOTOR_AIN[1], LOW); }
void motorA_reverse() { digitalWrite(MOTOR_AIN[0], LOW);  digitalWrite(MOTOR_AIN[1], HIGH); }
void motorA_stop()    { digitalWrite(MOTOR_AIN[0], LOW);  digitalWrite(MOTOR_AIN[1], LOW); }
void motorA_setSpeed(int duty) {
  duty = constrain(duty, 0, 255);
  ledcWrite(MOTOR_APWM, duty);   // write by pin
}

// ======================== SETUP ========================

void setup() {
  Serial.begin(115200);

  // Motor pins
  pinMode(MOTOR_AIN[0], OUTPUT);
  pinMode(MOTOR_AIN[1], OUTPUT);
  pinMode(MOTOR_APWM,   OUTPUT);

  // Encoder pins
  pinMode(ENC_APIN, INPUT_PULLUP);
  pinMode(ENC_BPIN, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENC_APIN), handleEncoder, RISING);

  // LEDC PWM attach by pin
  ledcAttach(MOTOR_APWM, pwmFreq, pwmResolution);

  // Start with motors stopped, controller disabled
  motorA_stop(); motorA_setSpeed(0);

  lastSpeedUpdateMs = millis();

  targetTicksA = 0;
  
  anyControlEnabled = false;

  Serial.println("--- SYSTEM RESTARTED ---");
  Serial.println("Motors will NOT move until you send a command.");
  Serial.println("Enter commands like: A 360  or  B 1000  (motor + target ticks)");
}



// ======================== SPEED UPDATE ========================

void updateSpeeds() {
  unsigned long now = millis();
  unsigned long dtMs = now - lastSpeedUpdateMs;
  if (dtMs < 100) return;   // update every 100 ms
  lastSpeedUpdateMs = now;
  float dtSec = dtMs / 1000.0f;

  long curA;
  noInterrupts();
  curA = ticksA;
  
  interrupts();
  long dA = curA - lastTicksA; lastTicksA = curA;
  speedA_ticksPerSec = dA / dtSec;
}

// ======================== POSITION CONTROL (IN TICKS) ========================

// index: 0=A, 1=B, 2=C, 3=D
void updatePositionControlForMotor(int index) {
  long curTicks, targetTicks;

  noInterrupts(); curTicks = ticksA; interrupts();
  targetTicks = targetTicksA; 
  long errorTicks = targetTicks - curTicks;

  // 1. Tolerance Check
  if (labs(errorTicks) <= TICK_TOLERANCE) {
      motorA_stop(); 
      motorA_setSpeed(0); 
      return;
  }

  // 2. Calculate Duty using Absolute Value
  // We use labs() because duty must be positive for the PWM controller
  int duty = labs(errorTicks) * kp;

  // 3. The "Anti-Stall" Floor
  // Even if the error is small, we need at least ~70 PWM to move the N20 gears
  if (duty < 70) duty = 70; 
  
  // 4. Cap it at 255
  if (duty > 255) duty = 255;

  // 5. Direction Logic
  if (errorTicks > 0) { 
      motorA_forward(); 
      motorA_setSpeed(duty);
  } else { 
      // This will now trigger when target (0) < current (2000)
      motorA_reverse(); 
      motorA_setSpeed(duty); 
  }
}


// convenience setter – also enables control
void setTargetTicks(long ticksTarget) {
  anyControlEnabled = true;   // enable control after the first command
    targetTicksA = ticksTarget; 
}


// ======================== SERIAL INPUT (IN TICKS) ========================

// Parse commands like "A 360", "b 1000", etc. (ticks, not degrees)
void readSerialCommand() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() < 3) return;  // need at least "A x"

  char motorChar = line.charAt(0);
  motorChar = toupper(motorChar);

  int spaceIdx = line.indexOf(' ');
  if (spaceIdx < 0) return;

  String valStr = line.substring(spaceIdx + 1);
  valStr.trim();
  if (valStr.length() == 0) return;

  long targetTicks = valStr.toInt();   // now interpreted as ticks (HIGH counts)


  setTargetTicks(targetTicks);

  Serial.print("Set target for motor ");
  Serial.print(motorChar);
  Serial.print(" to ");
  Serial.print(targetTicks);
  Serial.println(" ticks");
}


// ======================== MAIN LOOP ========================

void loop() {
  // Handle user input
  readSerialCommand();

  // Update speed estimations (in ticks/s)
  updateSpeeds();

  // Only run position control after at least one command
  if (anyControlEnabled) {
    updatePositionControlForMotor(0);
    
  }

  // Read positions
  long pA, pB, pC, pD;
  noInterrupts();
  pA = ticksA;
 
  interrupts();

  // Periodic debug print
  static unsigned long lastPrint = 0;
  unsigned long now = millis();
  if (now - lastPrint >= 200) {
    lastPrint = now;

    Serial.println("==== Motor States ====");
    Serial.print("Target: "); Serial.print(targetTicksA); Serial.println(" ticks");
    Serial.print("Current: "); Serial.print(pA); Serial.print(" ticks, ");
    Serial.print(speedA_ticksPerSec); Serial.println(" ticks/s");
    Serial.println("----------------------");
  }
}