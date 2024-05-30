from flask import Flask, render_template, request
import requests
from urllib.parse import unquote, urlencode
from dotenv import load_dotenv
import os
from datetime import datetime
import time
import RPi.GPIO as GPIO
import threading

# LED 초기 상태 설정(OFF)
app = Flask(__name__)


GPIO.setmode(GPIO.BCM)
led_list = [18, 23, 24, 25]
GPIO.setwarnings(False)
servo_pin = 12

GPIO.setup(servo_pin, GPIO.OUT)
GPIO.setup(led_list, GPIO.OUT)
GPIO.output(led_list, False)


# 날짜 포맷으로 지정해주는 함수
def get_current_date_string():
    current_date = datetime.now().date()
    return current_date.strftime("%Y%m%d")


# 30분 단위로 예보가 있기 때문에 시간을 구분
def get_current_hour_string():
    now = datetime.now()
    if now.minute <= 45:
        if now.hour == 0:
            base_time = "2330"
        else:
            pre_hour = now.hour - 1
            if pre_hour < 10:
                base_time = "0" + str(pre_hour) + "30"
            else:
                base_time = str(pre_hour) + "30"
    else:
        if now.hour <= 10:
            base_time = "0" + str(now.hour) + "30"
        else:
            base_time = str(now.hour) + "30"

    return base_time


# 발급받은 api key
load_dotenv()
myWeatherKey = os.environ.get("WEATHER_FORECAST_KEY")
# print(myWeatherKey)


url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
queryString = "?" + urlencode(
    {
        "serviceKey": unquote(myWeatherKey),
        "numOfRows": "60",
        "pageNo": "1",
        "dataType": "JSON",
        "base_date": get_current_date_string(),
        "base_time": get_current_hour_string(),
        "nx": "63",
        "ny": "110",
    }
)


@app.route("/", methods=["GET", "POST"])
def index():
    response = requests.get(url + queryString)
    data = response.json()
    data = data["response"]["body"]["items"]["item"]

    categories = {
        "T1H": "기온",
        "SKY": "하늘 상태",
        "PTY": "강수 형태",
        "RN1": "1시간 강수량",
        "REH": "습도",
        "WSD": "풍속",
    }

    sky_conditions = {
        "1": "맑음",
        "3": "구름 많음",
        "4": "흐림",
    }

    pty_type = {
        "0": "없음",
        "1": "비",
        "2": "비/눈",
        "3": "눈",
        "5": "빗방울",
        "6": "빗방울눈날림",
        "7": "눈날림",
    }

    results = {}
    for d in data:
        category = d["category"]
        if category in categories and "fcstValue" in d:
            if category == "SKY":
                results[categories[category]] = sky_conditions[d["fcstValue"]]
            elif category == "PTY":
                results[categories[category]] = pty_type[d["fcstValue"]]
            else:
                results[categories[category]] = d["fcstValue"]
        else:
            pass

    return render_template("index.html", weather=results)


# 자동제어 모드
@app.route("/auto/on")
def auto_on():
    response = requests.get(url + queryString)
    data = response.json()
    response_data = data["response"]
    body_data = response_data["body"]
    items_data = body_data["items"]

    item_list = items_data.get("item")

    for item in item_list:
        if item.get("category") == "T1H":  # 기온
            temp_str = item.get("fcstValue")
        if item.get("category") == "RN1":  # 강수량
            rain_str = item.get("fcstValue")
        if item.get("category") == "REH":  # 습도
            hum_str = item.get("fcstValue")
        if item.get("category") == "WSD":  # 풍속
            wsd_str = item.get("fcstValue")
            break

    rain_value_str = rain_str.replace("mm", "")

    current_time = datetime.now()
    hour = current_time.hour

    try:  # 기온
        temp = int(temp_str)
        wsd = int(wsd_str)
        if temp >= 25:
            GPIO.output(23, GPIO.HIGH)

        else:
            GPIO.output(23, GPIO.LOW)

    except:
        pass

    try:  # 습도
        hum = int(hum_str)
        if hum >= 60:
            GPIO.output(24, GPIO.HIGH)

        else:
            GPIO.output(24, GPIO.LOW)

    except:
        pass

    try:  # 정원 물
        rain = int(rain_value_str)
        if rain >= 1:
            GPIO.output(25, GPIO.LOW)
        else:
            pass

    except:
        pass

    try:  # 창문 닫기
        p = GPIO.PWM(servo_pin, 50)
        p.start(0)
        rain = int(rain_value_str)
        if rain >= 1:
            p.ChangeDutyCycle(12.5)
            time.sleep(1)
            p.ChangeDutyCycle(2.5)
            p.stop()
        else:
            pass

    except:
        pass

    try:
        if hour >= 18 and hour <= 22:
            GPIO.output(18, GPIO.HIGH)
        else:
            GPIO.output(18, GPIO.LOW)
    except:
        pass

    return "ok"


@app.route("/auto/off")
def auto_off():
    try:
        GPIO.cleanup()
        return "ok"
    except:
        return "fail"


@app.route("/led/on")
def led_on():
    try:
        GPIO.output(18, GPIO.HIGH)
        return "ok"
    except:
        return "fail"


@app.route("/led/off")
def led_off():
    try:
        GPIO.output(18, GPIO.LOW)
        return "ok"
    except:
        return "fail"


@app.route("/aircon/on")
def aircon_on():
    try:
        GPIO.output(23, GPIO.HIGH)
        return "ok"
    except:
        return "fail"


@app.route("/aircon/off")
def aircon_off():
    try:
        GPIO.output(23, GPIO.LOW)
        return "ok"
    except:
        return "fail"


@app.route("/hum/on")
def hum_on():
    try:
        GPIO.output(24, GPIO.HIGH)

        return "ok"
    except:
        return "fail"


@app.route("/hum/off")
def hum_off():
    try:
        GPIO.output(24, GPIO.LOW)
        return "ok"
    except:
        return "fail"


@app.route("/garden/on")
def garden_on():
    try:
        GPIO.output(25, GPIO.HIGH)
        return "ok"
    except:
        return "fail"


@app.route("/garden/off")
def garden_off():
    try:
        GPIO.output(25, GPIO.LOW)
        return "ok"
    except:
        return "fail"


@app.route("/window/open")
def window_open():
    p = GPIO.PWM(servo_pin, 50)
    p.start(0)
    try:
        p.ChangeDutyCycle(2.5)
        time.sleep(1)
        p.ChangeDutyCycle(12.5)
        p.stop()
        return "ok"
    except KeyboardInterrupt:
        GPIO.cleanup()
        return "fail"


@app.route("/window/close")
def window_close():
    p = GPIO.PWM(servo_pin, 50)
    p.start(0)
    try:
        p.ChangeDutyCycle(12.5)
        time.sleep(1)
        p.ChangeDutyCycle(2.5)
        p.stop()
        return "ok"
    except KeyboardInterrupt:
        GPIO.cleanup()
        return "fail"


if __name__ == "__main__":
    app.run(debug=True, port=5000)
    GPIO.cleanup()
