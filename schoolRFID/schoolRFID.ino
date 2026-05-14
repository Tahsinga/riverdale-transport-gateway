#include <WiFi.h>
#include <HTTPClient.h>
#include <MFRC522v2.h>
#include <MFRC522DriverSPI.h>
#include <MFRC522DriverPinSimple.h>
#include <MFRC522Debug.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// --- CONFIGURE THESE ---
const char* WIFI_SSID = "riverdale_esp";
const char* WIFI_PASS = "1234567890";
const char* SERVER_URL = "http://192.168.1.99:8000/api/rfid-scan/";
const int SCAN_DELAY_MS = 1200;
// -----------------------

// --- PIN MAP ---
//
//  RC522:
//    SS   -> GPIO15
//    RST  -> GPIO27
//    MOSI -> GPIO23
//    MISO -> GPIO19
//    SCK  -> GPIO18
//    VCC  -> 3.3V  (NOT 5V)
//    GND  -> GND
//
//  LCD (PCF8574 I2C):
//    SDA  -> GPIO21
//    SCL  -> GPIO22
//    VCC  -> 5V
//    GND  -> GND
//
//  Buzzer:
//    Signal -> GPIO32
//
#define RC522_SS_PIN  15
#define RC522_RST_PIN 27
#define BUZZER_PIN    32

LiquidCrystal_I2C lcd(0x27, 16, 2);
// -----------------------

MFRC522DriverPinSimple ss_pin(RC522_SS_PIN);
MFRC522DriverSPI driver{ss_pin};
MFRC522 mfrc522{driver};

// --- Buzzer helper ---
void beep(int count, int onMs = 100, int offMs = 100) {
  for (int i = 0; i < count; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(onMs);
    digitalWrite(BUZZER_PIN, LOW);
    if (i < count - 1) delay(offMs);
  }
}

// --- LCD helper ---
void lcdMsg(const char* row0, const char* row1 = "") {
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print(row0);
  lcd.setCursor(0, 1); lcd.print(row1);
}

void setup() {
  // Silence buzzer FIRST before anything else — prevents float-triggered beeps at boot
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // RST high before SPI init
  pinMode(RC522_RST_PIN, OUTPUT);
  digitalWrite(RC522_RST_PIN, HIGH);

  Serial.begin(115200);
  delay(200); // let power rails stabilise

  Wire.begin(); // SDA=21, SCL=22
  lcd.init();
  lcd.backlight();
  lcdMsg("RFID Reader", "Starting up...");
  delay(800);

  beep(2, 150, 100);

  // -----------------------------------------------
  // RC522 VERSION CHECK — retries 3 times
  // -----------------------------------------------
  lcdMsg("Testing RC522", "");
  delay(300);

  MFRC522::PCD_Version ver = MFRC522::PCD_Version::Version_Unknown;

  for (int attempt = 1; attempt <= 3; attempt++) {
    // Show which attempt we're on
    lcd.setCursor(0, 1);
    lcd.print("Attempt " + String(attempt) + "/3   ");

    digitalWrite(RC522_RST_PIN, LOW);
    delay(50);
    digitalWrite(RC522_RST_PIN, HIGH);
    delay(50);

    mfrc522.PCD_Init();
    delay(100);

    ver = mfrc522.PCD_GetVersion();
    if (ver != MFRC522::PCD_Version::Version_Unknown) break;

    delay(300);
  }

  if (ver == MFRC522::PCD_Version::Version_Unknown) {
    // All 3 attempts failed — SPI dead
    // Show message and stay here so user can read it
    lcdMsg("RC522 SPI FAIL", "Check SS/MOSI");
    delay(3000);
    lcdMsg("RST=27 SS=15", "MOSI=23 SCK=18");
    delay(3000);
    lcdMsg("VCC=3.3V only", "Check wiring!");
    // No halt loop — restart instead so user can try again
    ESP.restart();
  }

  // SPI alive
  if      (ver == MFRC522::PCD_Version::Version_1_0) lcdMsg("RC522 OK", "FW: v1.0");
  else if (ver == MFRC522::PCD_Version::Version_2_0) lcdMsg("RC522 OK", "FW: v2.0");
  else                                                lcdMsg("RC522 OK", "FW: clone OK");
  beep(1, 80);
  delay(1500);
  // -----------------------------------------------

  // WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  lcdMsg("Connecting WiFi", "");
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 30) {
    delay(500);
    lcd.setCursor(tries % 16, 1);
    lcd.print(".");
    tries++;
  }

  lcd.clear();
  if (WiFi.status() == WL_CONNECTED) {
    lcd.setCursor(0, 0); lcd.print("WiFi Connected");
    lcd.setCursor(0, 1); lcd.print(WiFi.localIP().toString().substring(0, 16));
  } else {
    lcdMsg("WiFi Failed", "Offline mode");
  }
  delay(1500);

  lcdMsg("Ready to scan", "Tap card...");
}

String uidToString(const MFRC522::Uid &uid) {
  String s = "";
  for (byte i = 0; i < uid.size; i++) {
    if (uid.uidByte[i] < 0x10) s += "0";
    s += String(uid.uidByte[i], HEX);
  }
  s.toUpperCase();
  return s;
}

void postUid(const String &uid) {
  if (WiFi.status() != WL_CONNECTED) {
    lcdMsg("No WiFi!", uid.substring(0, 16).c_str());
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  String payload = "{\"uid\": \"" + uid + "\"}";

  int code = http.POST(payload);
  if (code > 0) {
    String resp = http.getString();
    resp.trim();
    lcd.clear();
    lcd.setCursor(0, 0); lcd.print("HTTP " + String(code));
    lcd.setCursor(0, 1); lcd.print(resp.substring(0, 16));
  } else {
    lcd.clear();
    lcd.setCursor(0, 0); lcd.print("POST Failed");
    lcd.setCursor(0, 1); lcd.print(http.errorToString(code).substring(0, 16));
  }
  http.end();
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent()) return;
  if (!mfrc522.PICC_ReadCardSerial()) return;

  String uid = uidToString(mfrc522.uid);

  beep(1);

  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("UID:");
  lcd.setCursor(0, 1); lcd.print(uid.substring(0, 16));

  postUid(uid);

  delay(SCAN_DELAY_MS);
  mfrc522.PICC_HaltA();

  lcdMsg("Ready to scan", "Tap card...");
}