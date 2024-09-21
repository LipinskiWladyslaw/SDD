from PySide6.QtCore import QObject, Slot, Signal


class AntennaBase(QObject):
    onRssiReceived = Signal(str, str)
    onRssiReadError = Signal()
    comPort = str()

    def setupComPort(self):
        pass

    @Slot(str)
    def setAntennaFrequency(self, frequency):
        pass

