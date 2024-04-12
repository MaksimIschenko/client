import serial
import setting
import time

if __name__ == "__main__":
    ser = serial.Serial(setting.SERPORT1, setting.BRATE)
    try:
        while True:
            ser.write(b'D,s,4,IMU,*\r\n')
            response = ser.readline()
            if len(response.decode()) != 1:
                print("Получены данные: ", response.decode())
            time.sleep(1)
    except serial.SerialException:
        print("Ошибка при работе с последовательным портом.")
    except KeyboardInterrupt:
        print("Программа остановлена пользователем")
    finally:
        ser.close()

