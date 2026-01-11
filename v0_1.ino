#include <AccelStepper.h>
#include <Servo.h>
#include <math.h>

#define limitSwitch1 11
#define limitSwitch2 10
#define limitSwitch3 9
#define limitSwitch4 A3

AccelStepper stepper1(1, 2, 5); 
AccelStepper stepper2(1, 3, 6);
AccelStepper stepper3(1, 4, 7);
AccelStepper stepper4(1, 12, 13);

Servo gripperServo; 


double x = 10.0;
double y = 10.0;
double L1 = 228;#L1L2这个要知道机械臂两个臂长
double L2 = 136.5; 
double theta1, theta2, phi, z;
int stepper1Position, stepper2Position, stepper3Position, stepper4Position;
const float theta1AngleToSteps = 44.444444;
const float theta2AngleToSteps = 35.555555;
const float phiAngleToSteps = 10;
const float zDistanceToSteps = 100;
byte inputValue[5];
int k = 0;
String content = "";
int data[10];
int theta1Array[100];
int theta2Array[100];
int phiArray[100];
int zArray[100];
int gripperArray[100];
int positionsCounter = 0;

bool new_cmd_mark = false;

void setup() {
  Serial.begin(115200);
  pinMode(limitSwitch1, INPUT_PULLUP);
  pinMode(limitSwitch2, INPUT_PULLUP);
  pinMode(limitSwitch3, INPUT_PULLUP);
  pinMode(limitSwitch4, INPUT_PULLUP);
  stepper1.setMaxSpeed(4000);
  stepper1.setAcceleration(2000);
  stepper2.setMaxSpeed(4000);
  stepper2.setAcceleration(2000);
  stepper3.setMaxSpeed(4000);
  stepper3.setAcceleration(2000);
  stepper4.setMaxSpeed(4000);
  stepper4.setAcceleration(2000);
  gripperServo.attach(A0, 600, 2500);
  data[6] = 0;
  gripperServo.write(data[6]);
  delay(1000);
  data[5] = 100;
//  homing();
}
void loop() {
  if (Serial.available()) {
    content = Serial.readStringUntil('\n');
    for (int i = 0; i < 10; i++) {
      int index = content.indexOf(","); 
      data[i] = atol(content.substring(0, index).c_str()); 
      content = content.substring(index + 1); 
    }
    new_cmd_mark = true;
    if (data[0] == 1) {
      theta1Array[positionsCounter] = data[2] * theta1AngleToSteps; 
      theta2Array[positionsCounter] = data[3] * theta2AngleToSteps;
      phiArray[positionsCounter] = data[4] * phiAngleToSteps;
      zArray[positionsCounter] = data[5] * zDistanceToSteps;
      gripperArray[positionsCounter] = data[6];
      positionsCounter++;
    }
  }
  while (data[1] == 1) {
    stepper1.setSpeed(data[7]);
    stepper2.setSpeed(data[7]);
    stepper3.setSpeed(data[7]);
    stepper4.setSpeed(data[7]);
    stepper1.setAcceleration(data[8]);
    stepper2.setAcceleration(data[8]);
    stepper3.setAcceleration(data[8]);
    stepper4.setAcceleration(data[8]);
    for (int i = 0; i <= positionsCounter - 1; i++) {
      if (data[1] == 0) {
        break;
      }
      stepper1.moveTo(theta1Array[i]);
      stepper2.moveTo(theta2Array[i]);
      stepper3.moveTo(phiArray[i]);
      stepper4.moveTo(zArray[i]);
      while (stepper1.currentPosition() != theta1Array[i] || 
      stepper2.currentPosition() != theta2Array[i] || 
      stepper3.currentPosition() != phiArray[i] || 
      stepper4.currentPosition() != zArray[i]) {
        stepper1.run();
        stepper2.run();
        stepper3.run();
        stepper4.run();
      }
      if (i == 0) {
        gripperServo.write(gripperArray[i]);
      }
      else if (gripperArray[i] != gripperArray[i - 1]) {
        gripperServo.write(gripperArray[i]);
        delay(800); 
      }
      if (Serial.available()) {
        content = Serial.readString(); 
        for (int i = 0; i < 10; i++) {
          int index = content.indexOf(","); // locate the first ","
          data[i] = atol(content.substring(0, index).c_str()); //Extract the number from start to the ","
          content = content.substring(index + 1); //Remove the number from the string
        }
        if (data[1] == 0) {
          break;
        }
        stepper1.setSpeed(data[7]);
        stepper2.setSpeed(data[7]);
        stepper3.setSpeed(data[7]);
        stepper4.setSpeed(data[7]);
        stepper1.setAcceleration(data[8]);
        stepper2.setAcceleration(data[8]);
        stepper3.setAcceleration(data[8]);
        stepper4.setAcceleration(data[8]);
      }
    }
  }
  if(data[0]==1){
    homing();
  }
  if(data[0]==2){
    stepper1Position = data[2] * theta1AngleToSteps;
    stepper2Position = data[3] * theta2AngleToSteps;
    stepper3Position = data[4] * phiAngleToSteps;
    stepper4Position = data[5] * zDistanceToSteps;
    stepper1.setSpeed(data[7]);
    stepper2.setSpeed(data[7]);
    stepper3.setSpeed(data[7]);
    stepper4.setSpeed(data[7]);
    stepper1.setAcceleration(data[8]);
    stepper2.setAcceleration(data[8]);
    stepper3.setAcceleration(data[8]);
    stepper4.setAcceleration(data[8]);
    stepper1.moveTo(stepper1Position);
    stepper2.moveTo(stepper2Position);
    stepper3.moveTo(stepper3Position);
    stepper4.moveTo(stepper4Position);
    while (stepper1.currentPosition() != stepper1Position || 
    stepper2.currentPosition() != stepper2Position || 
    stepper3.currentPosition() != stepper3Position || 
    stepper4.currentPosition() != stepper4Position) {
      stepper1.run();
      stepper2.run();
      stepper3.run();
      stepper4.run();
    }
    delay(100);
    gripperServo.write(data[6]);
    delay(300);
  }
  if(new_cmd_mark == true){
    Serial.println("DONE");
    new_cmd_mark = false;
    data[0]=0;
  }
}
void serialFlush() {
  while (Serial.available() > 0) {  
    Serial.read();         
  }
}
void homing() {
  while (digitalRead(limitSwitch4) != 1) {
    stepper4.setSpeed(1500);
    stepper4.runSpeed();
    stepper4.setCurrentPosition(18000);
  }
  delay(20);
  stepper4.moveTo(10000);
  while (stepper4.currentPosition() != 10000) {
    stepper4.run();
  }
  while (digitalRead(limitSwitch3) != 1) {
    stepper3.setSpeed(-1100);
    stepper3.runSpeed();
    stepper3.setCurrentPosition(-1662); 
  }
  delay(20);
  stepper3.moveTo(0);
  while (stepper3.currentPosition() != 0) {
    stepper3.run();
  }
  while (digitalRead(limitSwitch2) != 1) {
    stepper2.setSpeed(-1300);
    stepper2.runSpeed();
    stepper2.setCurrentPosition(-5850); 
  }
  delay(20);
  stepper2.moveTo(0);
  while (stepper2.currentPosition() != 0) {
    stepper2.run();
  }
  while (digitalRead(limitSwitch1) != 1) {
    stepper1.setSpeed(-1200);
    stepper1.runSpeed();
    stepper1.setCurrentPosition(-3955); 
  }
  delay(20);
  stepper1.moveTo(0);
  while (stepper1.currentPosition() != 0) {
    stepper1.run();
  }
}
