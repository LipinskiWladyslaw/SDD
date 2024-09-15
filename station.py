# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox, QListWidget,
QGroupBox, QButtonGroup, QGridLayout, QRadioButton, QToolButton, QDialog
)
from PySide6.QtCore import Signal, Slot, Qt, QMetaEnum, QThread, QTimer
from PySide6.QtGui import QPixmap, QIcon
from iterator import FrequencyIterator
from utility import findPresetByName
from rabbitMQ_utils import RabbitMQPublisher, RabbitMQConsumer

import threading
import logging

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

# TODO: history track frequency/RSSI
# TODO: global STOP button
# TODO: Stop iterator button(reset frequency preset index)
# TODO: 1.2/5.8 iterator restart?

class IteratorMode(QMetaEnum):
    WithinPreset = 'Within Preset'
    ByStep = 'By Step'

class StationWidget(QWidget):
    iteratorDelayMinimum = 1
    iteratorDelayMaximum = 10
    defaultIteratorDelay = 3
    defaultIteratorMode = IteratorMode.WithinPreset

    publishFrequency = Signal(str)
    requestRabbitMQSetup = Signal()
    rabbitMQPublisherStart = Signal()
    rabbitMQConsumerStart = Signal()

    def __init__(self, config, presets, *args, **kwargs):
        super().__init__(*args, **kwargs)

        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

        self.presets = presets
        self.config = config
        self.currentPreset = findPresetByName(config["defaultPresetName"], config, presets)

        self.stationName = self.config["stationName"]

        self.frequency = self.currentPreset["minFrequency"]
        self.frequencyHistory = []
        self.frequencyStep = 10
        self.isFrequencyIteratorActive = False
        self.iteratorMode = self.defaultIteratorMode
        self.iterator = None
        self.iteratorDelay = self.defaultIteratorDelay

        self.frequencyStepOptions = ['1', '5', '10', '20']
        self.maxHistoryLength = 50

        self.frequencySpinnerMinimum = self.currentPreset["minFrequency"]
        self.frequencySpinnerMaximum = self.currentPreset["maxFrequency"]
        self.frequencySpinnerDefaultStep = 10

        # Setup UI elements
        self.setupUiElements()

        # Setup UI layout
        self.setupUiLayout()

        # Setup handlers
        self.setupHandlers()

        # Sync UI with data
        self.syncUI()

        # Setup RabbitMQ
        self.requestRabbitMQSetup.connect(self.setupRabbitMQ)
        QTimer.singleShot(100, lambda :self.requestRabbitMQSetup.emit())


    @Slot(str)
    def onPublishedCallback(self, value):
        print(f'PUBLISHED: {value}')

    @Slot(str)
    def onReceivedCallback(self, value):
        print(f'RECEIVED: {value}')

    def setupUiElements(self):
        self.stationTitle = QLabel(
            f'{self.config["location"]} [{self.config["stationName"]}]',
            alignment=Qt.AlignHCenter,
            objectName='stationTitle'
            )

        self.frequencySpinner = QSpinBox(
            self,
            minimum=self.frequencySpinnerMinimum,
            maximum=self.frequencySpinnerMaximum,
            singleStep=self.frequencySpinnerDefaultStep,
            objectName='frequencySpinner'
        )

        self.frequencySpinnerStepList = QComboBox(self, objectName='frequencySpinnerStepList')
        self.frequencySpinnerStepList.addItems(self.frequencyStepOptions)

        self.frequencyHistoryList = QListWidget(self)

        self.iteratorFrequencyWithinPresetModeRadio = QRadioButton(IteratorMode.WithinPreset)
        self.iteratorFrequencyByStepModeRadio = QRadioButton(IteratorMode.ByStep)

        self.iteratorFrequencyRadioGroup = QButtonGroup(self, exclusive=True)
        self.iteratorFrequencyRadioGroup.addButton(self.iteratorFrequencyWithinPresetModeRadio)
        self.iteratorFrequencyRadioGroup.addButton(self.iteratorFrequencyByStepModeRadio)

        self.iteratorFrequencyPresetList = QComboBox(self)
        self.iteratorFrequencyPresetList.addItems(map(lambda preset:preset["name"], self.presets))

        self.iteratorFrequencyPresetHelp = QToolButton(self, objectName='iteratorFrequencyPresetHelp')
        self.questionMarkIcon = QIcon(QPixmap(':/img/question_mark.png'))
        self.iteratorFrequencyPresetHelp.setIcon(self.questionMarkIcon)

        self.iteratorFrequencyStepList = QComboBox(self)
        self.iteratorFrequencyStepList.addItems(self.frequencyStepOptions)

        self.iteratorToggle = QToolButton(self, objectName='iteratorToggle')
        self.playIcon = QIcon(QPixmap(':/img/play.png'))
        self.stopIcon = QIcon(QPixmap(':/img/stop.png'))


        self.iteratorToggle.setIcon(self.playIcon)

        self.iteratorDelaySpinner = QSpinBox(
            self,
            minimum=self.iteratorDelayMinimum,
            maximum=self.iteratorDelayMaximum,
            objectName='iteratorDelaySpinner'
        )



    def setupUiLayout(self):
        mainColumnWrapper = QVBoxLayout(self)
        mainColumnWrapper.setSpacing(20)

        mainColumnWrapper.addWidget(self.stationTitle)

        frequencySpinnerRow = QHBoxLayout()
        frequencySpinnerRow.addWidget(self.frequencySpinner)
        frequencySpinnerRow.addWidget(self.frequencySpinnerStepList)

        mainColumnWrapper.addLayout(frequencySpinnerRow)
        mainColumnWrapper.addWidget(self.frequencyHistoryList)

        iteratorRadioGroupBox = QGroupBox('Iterator', self)
        iteratorRadioGroupBox.setAlignment(Qt.AlignHCenter)
        mainColumnWrapper.addWidget(iteratorRadioGroupBox)

        iteratorRadioGroupGrid = QGridLayout(iteratorRadioGroupBox)
        iteratorRadioGroupGrid.setVerticalSpacing(15)
        iteratorRadioGroupGrid.setContentsMargins(20,10,20,20)
        iteratorRadioGroupGrid.addWidget(self.iteratorFrequencyWithinPresetModeRadio, 0, 0)
        iteratorRadioGroupGrid.addWidget(self.iteratorFrequencyPresetList, 0, 1)
        iteratorRadioGroupGrid.addWidget(self.iteratorFrequencyPresetHelp, 0, 2)
        iteratorRadioGroupGrid.addWidget(self.iteratorFrequencyByStepModeRadio, 1, 0)
        iteratorRadioGroupGrid.addWidget(self.iteratorFrequencyStepList, 1, 1)

        iteratorToggleRow = QHBoxLayout()
        iteratorToggleRow.addWidget(self.iteratorToggle)
        iteratorToggleRow.addWidget(self.iteratorDelaySpinner)
        mainColumnWrapper.addLayout(iteratorToggleRow)



    def setupHandlers(self):
        self.frequencySpinner.valueChanged.connect(self.setFrequency)

        self.frequencyHistoryList.itemDoubleClicked.connect(self.onFrequencyHistoryItemDoubleClicked)

        self.iteratorFrequencyPresetList.currentIndexChanged.connect(self.onFrequencyPresetIndexChanged)
        self.iteratorFrequencyPresetHelp.clicked.connect(self.showPresetFrequenciesDialog)

        self.frequencySpinnerStepList.currentIndexChanged.connect(self.onFrequencyStepIndexChanged)
        self.iteratorFrequencyStepList.currentIndexChanged.connect(self.onFrequencyStepIndexChanged)

        self.iteratorFrequencyRadioGroup.buttonClicked.connect(self.setIteratorMode)

        self.iteratorToggle.clicked.connect(self.onFrequencyIteratorToggled)

        self.iteratorDelaySpinner.valueChanged.connect(self.setIteratorDelay)


    def syncUI(self):
        self.frequencySpinner.setValue(self.frequency)

        self.frequencyHistoryList.clear()
        self.frequencyHistoryList.addItems(self.frequencyHistory)

        self.frequencySpinner.setSingleStep(self.frequencyStep)
        self.frequencySpinnerStepList.setCurrentIndex(self.frequencySpinnerStepList.findText(str(self.frequencyStep)))
        self.iteratorFrequencyStepList.setCurrentIndex(self.iteratorFrequencyStepList.findText(str(self.frequencyStep)))

        if self.iteratorMode == IteratorMode.WithinPreset:
            self.iteratorFrequencyWithinPresetModeRadio.setChecked(True)
        elif self.iteratorMode == IteratorMode.ByStep:
            self.iteratorFrequencyByStepModeRadio.setChecked(True)

        self.iteratorFrequencyPresetList.setCurrentIndex(
            self.presets.index(findPresetByName(self.currentPreset['name'], self.config, self.presets))
        )

        self.iteratorToggle.setIcon(self.stopIcon if self.isFrequencyIteratorActive else self.playIcon)

        self.iteratorDelaySpinner.setValue(self.iteratorDelay)


    def closeEvent(self):
        print('CLOSING EMIT------------------------------')
        self.onClose.emit()

    def setupRabbitMQ(self):

        self.rabbitMQPublisher = RabbitMQPublisher(self.stationName)

        self.publisherThread = QThread()
        self.rabbitMQPublisher.moveToThread(self.publisherThread)
        self.publisherThread.start()

        self.publishFrequency.connect(self.rabbitMQPublisher.publish)
        self.rabbitMQPublisher.published.connect(self.onPublishedCallback)
        self.rabbitMQPublisherStart.connect(self.rabbitMQPublisher.start)

        self.rabbitMQPublisherStart.emit()


        self.rabbitMQConsumer = RabbitMQConsumer(self.stationName)

        self.consumerThread = QThread()
        self.rabbitMQConsumer.moveToThread(self.consumerThread)
        self.consumerThread.start()

        self.rabbitMQConsumer.received.connect(self.onReceivedCallback)
        self.rabbitMQConsumerStart.connect(self.rabbitMQConsumer.start)

        self.rabbitMQConsumerStart.emit()





    @Slot(int)
    @Slot(str)
    def setFrequency(self, frequency):
        frequencyInt = int()
        if isinstance(frequency, int):
            frequencyInt = frequency
        elif isinstance(frequency, str):
            frequencyInt = int(frequency)

        if frequencyInt == self.frequency:
            return

        self.frequency = frequencyInt

        self.addToFrequencyHistory(frequencyInt)

        self.publishFrequency.emit(str(frequencyInt))

        self.syncUI()





    @Slot(int)
    def setFrequencyStep(self, step):
        self.frequencyStep = step

        self.syncUI()



    @Slot(IteratorMode)
    def setIteratorMode(self, radioButton):
        iteratorMode = radioButton.text()
        self.iteratorMode = iteratorMode

        if self.isFrequencyIteratorActive:
            self.restartIterator()

        self.syncUI()




    @Slot(int)
    def setIteratorDelay(self, delay):
        self.iteratorDelay = delay

        if self.isFrequencyIteratorActive:
            self.restartIterator()

        self.syncUI()



    @Slot(int)
    def addToFrequencyHistory(self, frequency):
        self.frequencyHistory.insert(0, str(frequency))
        if len(self.frequencyHistory) > self.maxHistoryLength:
            self.frequencyHistory.pop()

        self.syncUI()



    @Slot()
    def onFrequencyHistoryItemDoubleClicked(self, item):
        self.setFrequency(item.text())


    @Slot()
    def onFrequencyPresetIndexChanged(self, index):
        self.currentPreset = self.presets[index];

        self.syncUI()


    @Slot()
    def onFrequencyStepIndexChanged(self, index):
        self.frequencyStep = int(self.frequencyStepOptions[index])

        if self.iteratorMode == IteratorMode.ByStep:
            if self.isFrequencyIteratorActive:
                self.restartIterator()

        self.syncUI()


    @Slot()
    def onFrequencyIteratorToggled(self):
        if not self.isFrequencyIteratorActive:
            self.startIterator(True)
        else:
            self.terminateIterator()

        self.syncUI()




    @Slot()
    def showPresetFrequenciesDialog(self):
        dialog = FrequencyPresetListDialog(self.currentPreset)
        dialog.exec_()


    @Slot(str)
    def publishStationFrequency(self, frequency):
        self.rabbitMQPublisher.publish(frequency)


    def startIterator(self, implicitTrigger):
        self.isFrequencyIteratorActive = True
        self.syncUI()
        self.iterator = FrequencyIterator()
        self.iterator.frequencyRequested.connect(self.setFrequency)

        if self.iteratorMode == IteratorMode.WithinPreset:
            self.iterator.start(self.currentPreset['presetFrequencies'], self.frequency, self.iteratorDelay, implicitTrigger)

        elif self.iteratorMode == IteratorMode.ByStep:
            list = []
            for value in range(
                self.currentPreset["minFrequency"],
                self.currentPreset["maxFrequency"],
                self.frequencyStep
            ):
                list.append(str(value))

            self.iterator.start(list, self.frequency, self.iteratorDelay, implicitTrigger)


    def terminateIterator(self):
        self.iterator.stop()
        self.isFrequencyIteratorActive = False


    def restartIterator(self):
        self.terminateIterator()
        QTimer.singleShot(100, self, lambda: self.startIterator(False))





class FrequencyPresetListDialog(QDialog):
    def __init__(self, preset):
        super().__init__()

        self.setWindowTitle(f'Preset frequencies for {preset["name"]}')

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet('font-size: 16pt; min-height: 300px;')
        self.list_widget.addItems(preset['presetFrequencies'])

        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)

        self.setLayout(layout)




# if __name__ == "__main__":
#     pass
