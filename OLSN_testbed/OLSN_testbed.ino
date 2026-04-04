// Pin Definitions
const int MOTOR_AIN[2] = {26,27};
const int MOTOR_BIN[2] = {18,19};
const int MOTOR_CIN[2] = {2,4};
const int MOTOR_DIN[2] = {17,5};
//const int MOTOR_EIN[2] = {1,3};

const int MOTOR_AENC[2] = {22, 23};

const int MOTOR_PWMA = 25;

//PWM Settings
const int freq = 50000;
const int pwmChannel = 0;
const int resolution = 8;
int dutyCycle = 64;

//ADC Settings
const int adc_channels [3] = {12,13,14};

int adc_reading[3] = {};

void setup() {
  //Baud rate
  Serial.begin(115200);
  // Set all pins as outputs
  pinMode(MOTOR_AIN[0], OUTPUT);
  pinMode(MOTOR_AIN[1], OUTPUT);
  pinMode(MOTOR_BIN[0], OUTPUT);
  pinMode(MOTOR_BIN[1], OUTPUT);
  pinMode(MOTOR_CIN[0], OUTPUT);
  pinMode(MOTOR_CIN[1], OUTPUT);
  pinMode(MOTOR_DIN[0], OUTPUT);
  pinMode(MOTOR_DIN[1], OUTPUT);

 // pinMode(MOTOR_EIN[0], OUTPUT);
 // pinMode(MOTOR_EIN[1], OUTPUT); 
  pinMode(MOTOR_PWMA, OUTPUT);

  ledcAttachChannel(MOTOR_PWMA, freq, resolution, pwmChannel);

  //Set up PWM
  ledcWrite(MOTOR_PWMA, dutyCycle);


}

void stopMotor(const int MOTOR[2]) {
  digitalWrite(MOTOR[0], LOW);
  digitalWrite(MOTOR[1], LOW);

}

void CurlFinger(const int MOTOR[2]) {
  digitalWrite(MOTOR[0], HIGH);
  digitalWrite(MOTOR[1], LOW);
  Serial.print("Curling");
  Serial.print("\n");

}

void UncurlFinger(const int MOTOR[2]) {
  digitalWrite(MOTOR[0], LOW);
  digitalWrite(MOTOR[1], HIGH);
  Serial.println("Uncurling");
  Serial.println("\n");

}

void readEncoder(const int ENC[2]) {

  int a_enc1 = analogRead(ENC[0]);
  int a_enc2 = analogRead(ENC[1]);
  Serial.println(a_enc1, a_enc2);
}

void loop() {
  // //Get readings from ADC Channels
  // for (int i = 0; i < 3; i++){
  //   adc_reading[i] = analogRead(adc_channels[1]);
  //   Serial.println(adc_reading[i]);
  // }
  
  readEncoder(MOTOR_AENC);
  //Move Finger
  CurlFinger(MOTOR_AIN);
  CurlFinger(MOTOR_BIN);
  CurlFinger(MOTOR_CIN);
  CurlFinger(MOTOR_DIN);
  delay(1000);

  stopMotor(MOTOR_AIN);
  stopMotor(MOTOR_BIN);
  stopMotor(MOTOR_CIN);
  stopMotor(MOTOR_DIN);
  delay(1000);

  UncurlFinger(MOTOR_AIN);
  UncurlFinger(MOTOR_BIN);
  UncurlFinger(MOTOR_CIN);
  UncurlFinger(MOTOR_DIN);
  delay(1000);

  stopMotor(MOTOR_AIN);
  stopMotor(MOTOR_BIN);
  stopMotor(MOTOR_CIN);
  stopMotor(MOTOR_DIN);
  delay(1000);

  

}