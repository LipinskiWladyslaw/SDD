from PySide6.QtCore import QObject, QThread, Slot, Signal, QIODevice
from PySide6.QtSerialPort import QSerialPort
import re

class Antenna_1_2(QObject):
    onRssiReceived = Signal(str, str)
    onRssiReadError = Signal()

    rssi_answer = ''
    currentFrequency = None

    def __init__(self, comPort):
        super().__init__()

        self.comPort = comPort

    def setupComPort(self):
        self.comportThread = QThread()
        self.comportThread.moveToThread(self.comportThread)
        self.comportThread.start()

        self.serial = QSerialPort()
        self.serial.readyRead.connect(self.onReadyRead)

        self.openPort()


    def openPort(self):
        if self.serial.isOpen():
            self.serial.close()
        self.serial.setPortName(self.comPort)
        self.serial.setBaudRate(QSerialPort.BaudRate.Baud9600)
        self.serial.setDataBits(QSerialPort.DataBits.Data8)
        self.serial.setParity(QSerialPort.Parity.NoParity)
        self.serial.setStopBits(QSerialPort.StopBits.OneStop)
        self.serial.open(QIODevice.ReadWrite)


    @Slot()
    def onReadyRead(self):
        finalRssiLinePart = '\n'

        rx = self.serial.readLine()

        try:
            rxstring = rx.data().decode("utf-8")
            self.rssi_answer += rxstring
            if finalRssiLinePart in rxstring:
                rssi = self.extractValueFromRssiAnswer(self.rssi_answer)
                self.onRssiReceived.emit(self.currentFrequency, rssi)
                self.rssi_answer = ''
        except:
            self.onRssiReadError.emit()

    @Slot(str)
    def setAntennaFrequency(self, frequency):
        if self.serial.isOpen():
            if self.currentFrequency == frequency:
                return
            data = f'#SET {frequency}'
            txs = ','.join(map(str, data)) + '\n'
            self.serial.write(txs.encode())
            self.currentFrequency = frequency


    def extractValueFromRssiAnswer(self, rssi):
        m = re.match(".* (\d+)", rssi) # expecting "#RSSI 123"
        return m.group(1)


