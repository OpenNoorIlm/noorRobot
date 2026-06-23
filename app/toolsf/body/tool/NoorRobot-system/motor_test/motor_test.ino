#define RIGHT_FORWARD_PIN   9
#define RIGHT_BACKWARD_PIN  6
#define LEFT_FORWARD_PIN    3
#define LEFT_BACKWARD_PIN   5

const unsigned long RUN_MS = 2000;
const unsigned long PAUSE_MS = 1500;

void stopAll() {
  digitalWrite(RIGHT_FORWARD_PIN, LOW);
  digitalWrite(RIGHT_BACKWARD_PIN, LOW);
  digitalWrite(LEFT_FORWARD_PIN, LOW);
  digitalWrite(LEFT_BACKWARD_PIN, LOW);
}

void runPins(int rightForward, int rightBackward, int leftForward, int leftBackward, const char* label) {
  Serial.println(label);
  digitalWrite(RIGHT_FORWARD_PIN, rightForward ? HIGH : LOW);
  digitalWrite(RIGHT_BACKWARD_PIN, rightBackward ? HIGH : LOW);
  digitalWrite(LEFT_FORWARD_PIN, leftForward ? HIGH : LOW);
  digitalWrite(LEFT_BACKWARD_PIN, leftBackward ? HIGH : LOW);
  delay(RUN_MS);
  stopAll();
  delay(PAUSE_MS);
}

void runSinglePin(int pin, const char* label) {
  Serial.println(label);
  stopAll();
  digitalWrite(pin, HIGH);
  delay(RUN_MS);
  stopAll();
  delay(PAUSE_MS);
}

void setup() {
  pinMode(RIGHT_FORWARD_PIN, OUTPUT);
  pinMode(RIGHT_BACKWARD_PIN, OUTPUT);
  pinMode(LEFT_FORWARD_PIN, OUTPUT);
  pinMode(LEFT_BACKWARD_PIN, OUTPUT);

  stopAll();
  Serial.begin(9600);
  delay(1000);
  Serial.println("Motor test starting");
}

void loop() {
  runSinglePin(RIGHT_FORWARD_PIN, "Single pin: right forward");
  runSinglePin(RIGHT_BACKWARD_PIN, "Single pin: right backward");
  runSinglePin(LEFT_FORWARD_PIN, "Single pin: left forward");
  runSinglePin(LEFT_BACKWARD_PIN, "Single pin: left backward");

  runPins(0, 0, 1, 0, "Left wheels forward together");
  runPins(0, 0, 0, 1, "Left wheels backward together");

  runPins(1, 0, 0, 0, "Right wheels forward together");
  runPins(0, 1, 0, 0, "Right wheels backward together");

  runPins(1, 0, 1, 0, "All wheels forward together");
  runPins(0, 1, 0, 1, "All wheels backward together");
}
