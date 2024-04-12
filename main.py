import socket
import json
import time
from datetime import datetime
import serial
import logging
from threading import Thread
import setting
import sys


class SharedData():
    """
    Класс, представляющий общие данные для всех потоков.
    """
    def __init__(self):
        # Структура сообщения в TCP-порт
        self.snd_msg = {'status': None, 'available_ports': [], 'msg_data': {}}
        # Список команд в последовательный порт
        self.cmds = []

def get_time():
    """
    Возвращает текущее время в формате "HH:MM:SS.mmm".
    """
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


# Конфигурируем логгер
logging.basicConfig(level=logging.INFO, filename=f"logfile.log", filemode="a")


class TCPThread():
    """
    Класс, представляющий поток TCP.

    Attributes:
        shared_data (object): Общий объект данных.

    Methods:
        run(): Starts the TCP thread and establishes a connection with the server.
    """

    def __init__(self, shared_data: SharedData):
        super().__init__()
        self.shared_data = shared_data

    def run(self):
        """
        Запускает поток TCP и устанавливает соединение с сервером.
        """
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                    client.settimeout(5)
                    client.connect((setting.HOST, setting.EPORT))

                    logging.info(f"[{get_time()}] - TCPThread: Connected to server.")
                    print(f"[{get_time()}] - TCPThread: Connected to server.")

                    # Отправляем данные о статусе соединения серверу. (рукопожатие)
                    self.shared_data.snd_msg["status"] = "CONNECTEDTOSERVER"
                    data_to_resp = json.dumps(self.shared_data.snd_msg).encode()
                    client.sendall(data_to_resp)

                    # Обрабатываем соединение с сервером.
                    self.process_connection(client)

            except Exception as e:
                # Логируем ошибки и ждем перед попыткой переподключения.
                logging.error(f"[{get_time()}] - TCPThread: {e}")
                print(f"[{get_time()}] - TCPThread: {e}")
                time.sleep(0.5)

    def process_connection(self, client):
        """
        Обрабатывает соединение с сервером.

        Args:
            client (socket.socket): Сокет клиента.
        """
        while True:
            try:
                
                # Получаем данные от сервера.
                raw_data = client.recv(1024).decode()
                data = json.loads(raw_data)

                if not len(data["cmd"]) == 0:
                    logging.info(f"[{get_time()}] - TCPThread: Received data: {raw_data}")
                    print(f"[{get_time()}] - TCPThread: Received data: {raw_data}")
                
                # Конвертируем данные из TCP в последовательный порт.
                self.convert_tcp_to_serial(data)

                if len(data['cmd']) == 0:
                    self.shared_data.snd_msg['status'] = "CONNECTEDTOSERVER"
                    self.shared_data.snd_msg['msg_data']['INFO'] = socket.gethostbyname(socket.gethostname())
                    
                #self.shared_data.snd_msg['available_ports'] = self.avail_dev()
                self.shared_data.snd_msg['msg_data']["INFO"] = [socket.gethostbyname(socket.gethostname())]
                
                # Отправляем данные серверу.
                data_to_resp = json.dumps(self.shared_data.snd_msg).encode()
                client.sendall(data_to_resp)

                if not self.shared_data.snd_msg['msg_data'] == {'INFO': ['127.0.1.1']}:
                    logging.info(f"[{get_time()}] - TCPThread: Sent data: {self.shared_data.snd_msg}")
                    print(f"[{get_time()}] - TCPThread: Sent data: {self.shared_data.snd_msg}")
                
                # Очищаем содержимое отправляемого пакета.
                try:
                    self.shared_data.snd_msg = {'status': None, 'available_ports': [], 'msg_data': {}}
                except Exception as e:
                    logging.error(f"[{get_time()}] - TCPThread: {e}")
                    print(f"[{get_time()}] - TCPThread: {e}")
                
                # Задержка перед отправкой следующего пакета.
                time.sleep(0.1)

            except json.decoder.JSONDecodeError:
                # Если возникает ошибка декодирования JSON, прерываем цикл.
                logging.error(f"[{get_time()}] - TCPThread: {e}")
                print(f"[{get_time()}] - TCPThread: {e}")
                break
            except Exception as e:
                # Логируем другие ошибки и прерываем цикл.
                logging.error(f"[{get_time()}] - TCPThread: {e}")
                print(f"[{get_time()}] - TCPThread: {e}")
                break


    def convert_tcp_to_serial(self, data):
        """
        Конвертирует данные из TCP в последовательный порт.

        Args:
            data (dict): Данные из TCP.
        """

        try:

            if "GPS" in data['cmd']:    
                """ ЗАПРОС GPS"""
                #self.shared_data.cmds.append('D,s,4,GPS,*\r\n')
                self.shared_data.cmds.append('GPS')

            if "IMU" in data['cmd']:
                """ ЗАПРОС IMU """
                #self.shared_data.cmds.append('D,s,4,IMU,*\r\n')
                self.shared_data.cmds.append('IMU')

            if "MTRCMD" in data['cmd']:
                """ УПРАВЛЕНИЕ МОТОРОМ ВКЛ/ВЫКЛ """
                
                if data['msg_data']['MTRCMD'] == 'START':
                    self.shared_data.cmds.append('D,s,ESTART,*,\r\n')
                        
                if data['msg_data']['MTRCMD'] == 'STOP':
                    self.shared_data.cmds.append('D,s,ESTOP,*,\r\n')

            if 'SETMODE' in data['cmd']:

                if data['msg_data']['SETMODE'] == 'RMT':
                    print('D,s,5,RC,*,\r\n')
                    self.shared_data.cmds.append('D,s,5,RC,*,\r\n')

                if data['msg_data']['SETMODE'] == 'MAN': ...
            
            if "MANKEYCMD" in data['cmd']:
                """ РУЧНОЕ УПРАВЛЕНИЕ """            
                _raw_cmd = data['msg_data']['MANKEYCMD']
                _cmd = f'D,s,3,{_raw_cmd[0]},{_raw_cmd[1:]},*,\r\n'
                self.shared_data.cmds.append(_cmd)

            if "MANLINECMD" in data["cmd"]:
                self.shared_data.cmds.append(data['msg_data']['MANLINECM'])
        
        except Exception as e:
            logging.error(f"[{get_time()}] - TCPThread: func <convert_tcp_to_serial> : {e}")
            print(f"[{get_time()}] - TCPThread: func <convert_tcp_to_serial> : {e}")


class SerialThread():
    """
    Класс, представляющий поток последовательного порта.

    Attributes:
        shared_data (object): Общий объект данных.

    Methods:
        write(): Отправляет данные в последовательный порт.
        read(): Читает данные из последовательного порта.
        stop(): Останавливает поток последовательного порта.
    """

    def __init__(self, shared_data: SharedData):
        super().__init__()
        self.shared_data = shared_data
        self.ser_select = 0
        

    def write(self):
        """
        Отправляет данные в последовательный порт.
        """

        # Попытка подключиться к плате
        try:
            self.ser = serial.Serial(setting.SERPORT1, setting.BRATE, timeout=5)
            self.ser_select = 0
            logging.warning(f"[{get_time()}] - Connect to {setting.SERPORT1} device.")
            print(f"[{get_time()}] - Connect to {setting.SERPORT1} device.")
        except:
            self.ser = serial.Serial(setting.SERPORT2, setting.BRATE, timeout=5)
            self.ser_select += 1
            logging.warning(f"[{get_time()}] - Connect to {setting.SERPORT2} device.")
            print(f"[{get_time()}] - Connect to {setting.SERPORT2} device.")

        while True:
            
            # В ходе работы теряем содинение с платой
            # из-за чего происходит переопределение порта:
            # "/dev/ttyACM0 <--> /dev/ttyACM1
            if self.ser_select == 0:
                try:
                    self.ser = serial.Serial(setting.SERPORT1, setting.BRATE, timeout=5)
                    if not self.ser.is_open:
                        self.ser.close()
                        self.ser.open()
                        logging.warning(f"[{get_time()}] - Connect to {setting.SERPORT1} device.")
                        print(f"[{get_time()}] - Connect to {setting.SERPORT1} device.")

                except Exception as e:
                    logging.error(f"[{get_time()}] - Can not connect to {setting.SERPORT1} device.")
                    print(f"[{get_time()}] - Can not connect to {setting.SERPORT1} device.")
                    self.ser_select = 1
                    continue
            
            if self.ser_select == 1:
                try:
                    self.ser = serial.Serial(setting.SERPORT2, setting.BRATE, timeout=5)
                    if not self.ser.is_open:
                        self.ser.close()
                        self.ser.open()
                        logging.warning(f"[{get_time()}] - Connect to {setting.SERPORT2} device.")
                        print(f"[{get_time()}] - Connect to {setting.SERPORT2} device.")
                except Exception as e:
                    logging.error(f"[{get_time()}] - Can not connect to {setting.SERPORT2} device.")
                    print(f"[{get_time()}] - Can not connect to {setting.SERPORT2} device.")
                    self.ser_select = 0
                    continue

            time.sleep(0.1)
            # Проверяем, есть ли команды для отправки
            # если есть, то пишем в послежовательный порт
            if len(self.shared_data.cmds) != 0:
                for cmd in self.shared_data.cmds:
                    # Отправляем данные в порт
                    try:
                        if cmd  == 'GPS':
                            self.ser.write(b'D,s,4,GPS,*\r\n')
                            
                        if cmd == 'IMU':
                            self.ser.write(b'D,s,4,IMU,*\r\n')
                        
                        if cmd != 'GPS' and cmd != 'IMU':
                            _b_cmd = cmd.encode("utf-8")
                            self.ser.write(_b_cmd)
                        logging.info(f"[{get_time()}] - SerialThread <write>: Sent data: {cmd}")
                        print(f"[{get_time()}] - SerialThread <write>: Sent data: {cmd}")
                    except Exception as e:
                        logging.error(f"[{get_time()}] - SerialThread <write>: {e}")
                        print(f"[{get_time()}] - SerialThread <write>: {e}")
                        break
                    
            # Очистка списка команд после отправки
            self.shared_data.cmds.clear()

    def read(self):
        """
        Читает данные из последовательного порта.
        """
        try:
            # Задержка 1 с, на инициализацию и запуск порта
            time.sleep(1)

            while True:
                
                # Проверяем, открыт ли порт
                # Если порт закрыт, то пропускаем итерацию
                if not self.ser.is_open:
                    continue
                
                # Читаем данные из порта
                try:
                    ser_data = self.ser.readline()
                except Exception as e:
                    logging.error(f"[{get_time()}] - SerialThread <read.readline>: {e}")
                    logging.error(f"[{get_time()}] - SerialThread <read.readline> with data: {ser_data}")
                    print(f"[{get_time()}] - SerialThread <read.readline>: {e}")
                    continue
                
                # Конвертируем данные из последовательного порта
                try:
                    rcv_data = ser_data.decode()
                except Exception as e:
                    logging.error(f"[{get_time()}] - SerialThread <read.decode>: {e}")
                    print(f"[{get_time()}] - SerialThread <read.decode>: {e}")
                    continue

                logging.info(f"[{get_time()}] - SerialThread <read> rcv_data: {rcv_data}")
                print(f"[{get_time()}] - SerialThread <read.decode> rcv_data: {rcv_data}")

                # Ответ на запрос GPS
                if rcv_data.startswith("D,s,1,1"):
                    self.shared_data.snd_msg['status'] = "RESPONSE"
                    self.shared_data.snd_msg['msg_data']["GPSRESPONSE"] = rcv_data
                    logging.info(f"[{get_time()}] - SerialThread: Received data: {rcv_data}")
                    print(f"[{get_time()}] - SerialThread: Received data: {rcv_data}")

                # Ответ на запрос IMU
                if rcv_data.startswith("D,s,1,3"):
                    self.shared_data.snd_msg['status'] = "RESPONSE"
                    self.shared_data.snd_msg['msg_data']["IMURESPONSE"] = rcv_data
                    logging.info(f"[{get_time()}] - SerialThread: Received data: {rcv_data}")
                    print(f"[{get_time()}] - SerialThread: Received data: {rcv_data}")

                if rcv_data.startswith("D,s,1,5"):
                    self.shared_data.snd_msg['status'] = "REMOTE"
                    self.shared_data.snd_msg['msg_data']["REMOTE_VERIFY"] = rcv_data
                    logging.info(f"[{get_time()}] - SerialThread: Received data: {rcv_data}")
                    print(f"[{get_time()}] - SerialThread: Received data: {rcv_data}")

                time.sleep(0.1)
                
        except Exception as e:
            logging.info(f"[{get_time()}] - SerialThread: <read>: {e}")
            print(f"[{get_time()}] - SerialThread: <read>: {e}")



    def stop(self):
        """
        Останавливает поток последовательного порта.
        """
        self.ser.close()


if __name__ == "__main__":

    logging.info(f"[{get_time()}] - Starting main thread...")

    # Создаем общие данные для всех потоков
    shared_data = SharedData()

    # Создаем потоки
    tcp_thread = TCPThread(shared_data)
    serial_thread = SerialThread(shared_data)

    # Запускаем потоки
    t1 = Thread(target=tcp_thread.run)
    t2 = Thread(target=serial_thread.write)
    t3 = Thread(target=serial_thread.read)
    t1.start()
    t2.start()
    t3.start()

    try:
        t1.join()
        t2.join()
        t3.join()

    except KeyboardInterrupt:
        # Обрабатываем прерывание пользователем и останавливаем потоки.
        logging.info(f"[{get_time()}] - Received KeyboardInterrupt. Stopping...")
        tcp_thread.stop()
        serial_thread.stop()
        # Добавлен для ожидания завершения работы потока после остановки.
        t1.join()
        t2.join()
        t3.join()
        logging.info(f"[{get_time()}] - Application has been stopped gracefully.")

    except Exception as e:
        # Логируем ошибки и завершаем работу приложения
        logging.error(f"[{get_time()}] - {e}")
        print(f"[{get_time()}] - {e}")
        logging.info(f"[{get_time()}] - Application has been stopped with errors.")
    finally:
        # Завершаем работу логгера и выходим из приложения
        logging.info(f"[{get_time()}] - Application has been stopped.")
        print(f"[{get_time()}] - Application has been stopped.")
        logging.shutdown()
        sys.exit(0)
