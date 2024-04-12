import sys
import glob
import serial
import time


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

if __name__ == "__main__":
    print("----------------------------------")
    print("  Старт поисков доступных портов  ")
    print("----------------------------------")
    ports = serial_ports()
    if not ports:
        print("\t  Порты не найдены")
        print("----------------------------------")
    else:
        for i, port in enumerate(ports):
            print(f"\t#{i}: {port}")
    print("       Поиск портов завершён      ")
    print("----------------------------------")

