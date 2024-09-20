from PySide6.QtCore import QObject, QThread, Slot, Signal, QIODevice
from tbs_fusion import TBSFusion
import time

class Anthena_5_8(QObject):
    onRssiReceived = Signal(str, str)
    onRssiReadError = Signal()

    def __init__(self, comPort):
        super().__init__()

        self.comPort = comPort


    def setupAnthena(self):
        self.comportThread = QThread()
        self.comportThread.moveToThread(self.comportThread)
        self.comportThread.start()

        self.fusion = TBSFusion(
            self.comPort,  # Serial port to use
            baudrate=9600,  # Baudrate ("Serial Baud" in settings)
            default_address=1,  # Address ("Serial Addr" in settings)
            discard_echo=False,  # Set to False for RS-485
        )

    @Slot(str)
    def setAnthenaFrequency(self, frequency):
        # Set the operating frequency
        self.fusion.set_frequency(int(frequency))

        # Wait for RSSI to stabilize
        # time.sleep(1)
        # self.getFrequencyRssi()



    def getFrequencyRssi(self):
        # Get the frequency and print the RSSI
        freq_received, rssi_a, rssi_b = self.fusion.get_frequency_rssi()
        print('Frequency: %d MHz RSSI A: %0.2f RSSI B: %0.2f'
              % (freq_received, rssi_a, rssi_b))
        print(f'freq_received type: {type(freq_received)}')
        print(f'rssi_a type: {type(rssi_a)}')
        print(f'rssi_b type: {type(rssi_b)}')
        self.onRssiReceived.emit(freq_received, rssi_a)

        '''
        # Perform an RSSI scan in the "F" band
        freqs, rssi = fusion.rssi_scan_range(5740, 5900, 20)
        print(' '.join(['%d MHz: %0.2f' % (f, r) for f, r in zip(freqs, rssi)]))
        
        # Do the same scan but using the frequency list, use only receiver B
        rssi = fusion.rssi_scan_list(freqs, rx_use=2)
        print(' '.join(['%d MHz: %0.2f' % (f, r) for f, r in zip(freqs, rssi)]))
        '''
