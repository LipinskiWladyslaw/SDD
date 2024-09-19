# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
QGroupBox, QButtonGroup, QGridLayout, QRadioButton, QToolButton, QDialog
)
from PySide6.QtCore import Signal, Slot, Qt, QMetaEnum, QThread, QTimer
from PySide6.QtGui import QPixmap, QIcon, QStandardItemModel, QStandardItem
from iterator import FrequencyIterator
from anthena_1_2 import Anthena_1_2
from utility import findPresetByName

import logging

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

class IteratorMode(QMetaEnum):
    WithinPreset = 'Within Preset'
    ByStep = 'By Step'

class StationWidget(QWidget):
    maxHistoryLength = 5
    iteratorDelayMinimum = 1
    iteratorDelayMaximum = 10
    defaultIteratorDelay = 3
    defaultIteratorMode = IteratorMode.WithinPreset
    anthena = None

    stopStation = Signal()
    syncWithCurrentStation = Signal(str, str)
    localModeActivated = Signal(bool)
    onFrequencySet = Signal(str)
    anthenaRssiReceived = Signal(str)
    rabbitMQPublisherStart = Signal()
    rabbitMQConsumerStart = Signal()

    def __init__(self, config, presets, isStationMode, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

        self.presets = presets
        self.config = config
        self.isStationMode = isStationMode
        self.currentPreset = findPresetByName(config["frequencyRange"], config, presets)

        self.stationName = self.config["stationName"]

        self.isLocalModeActive = not isStationMode
        self.frequency = self.currentPreset["minFrequency"]
        self.frequencyHistory = []
        self.frequencyStep = 10
        self.isFrequencyIteratorActive = False
        self.iteratorMode = self.defaultIteratorMode
        self.iterator = None
        self.iteratorDelay = self.defaultIteratorDelay

        self.frequencyStepOptions = ['1', '5', '10', '20']

        self.frequencySpinnerMinimum = int(self.currentPreset["minFrequency"])
        self.frequencySpinnerMaximum = int(self.currentPreset["maxFrequency"])
        self.frequencySpinnerDefaultStep = 10

        # Setup UI elements
        self.setupUiElements()

        # Setup UI layout
        self.setupUiLayout()

        # Setup handlers
        self.setupHandlers()

        # Sync UI with data
        self.syncUI()

        if self.isStationMode:
            self.setupAnthena(self.config["frequencyRange"])


    def setupUiElements(self):
        self.stationTitle = QLabel(
            f'{self.config["location"]} [{self.config["stationName"]}] {self.currentPreset["name"]}GHz',
            alignment=Qt.AlignHCenter,
            objectName='stationTitle'
        )

        self.cloudSyncToggle = QToolButton(
            objectName='cloudSyncToggle',
            toolTip='Toggle cloud sync'
        )
        self.cloudSyncToggle.setIcon(QIcon(QPixmap(':/img/cloud-sync.webp')))

        self.frequencySyncButton = QToolButton(
            objectName='frequencySyncButton',
            toolTip='Sync all station to current frequency'
        )
        self.frequencySyncButton.setIcon(QIcon(QPixmap(':/img/sync.png')))

        self.frequencySpinner = QSpinBox(
            minimum=self.frequencySpinnerMinimum,
            maximum=self.frequencySpinnerMaximum,
            singleStep=self.frequencySpinnerDefaultStep,
            objectName='frequencySpinner',
            toolTip='Current frequency'
        )

        self.frequencySpinnerStepList = QComboBox(
            objectName='frequencySpinnerStepList',
            toolTip='Frequency spinner step'
        )
        self.frequencySpinnerStepList.addItems(self.frequencyStepOptions)

        self.historyTable = QTableWidget(0, 2)
        self.historyTable.setHorizontalHeaderLabels(['Frequency (MHz)', 'RSSI (dBm)'])
        self.historyTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.historyTable.verticalHeader().hide()
        self.historyTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.iteratorFrequencyWithinPresetModeRadio = QRadioButton(IteratorMode.WithinPreset)
        self.iteratorFrequencyByStepModeRadio = QRadioButton(IteratorMode.ByStep)

        self.iteratorFrequencyRadioGroup = QButtonGroup(self, exclusive=True)
        self.iteratorFrequencyRadioGroup.addButton(self.iteratorFrequencyWithinPresetModeRadio)
        self.iteratorFrequencyRadioGroup.addButton(self.iteratorFrequencyByStepModeRadio)

        self.iteratorFrequencyPresetHelp = QToolButton(
            objectName='iteratorFrequencyPresetHelp',
            toolTip='Browse preset frequencies list'
        )
        self.questionMarkIcon = QIcon(QPixmap(':/img/question_mark.png'))
        self.iteratorFrequencyPresetHelp.setIcon(self.questionMarkIcon)

        self.iteratorFrequencyStepList = QComboBox( toolTip='Frequency spinner step')
        self.iteratorFrequencyStepList.addItems(self.frequencyStepOptions)

        self.iteratorToggle = QToolButton(objectName='iteratorToggle', toolTip='Frequency iterator toggle')
        self.playIcon = QIcon(QPixmap(':/img/play.png'))
        self.stopIcon = QIcon(QPixmap(':/img/stop.png'))


        self.iteratorToggle.setIcon(self.playIcon)

        self.iteratorDelaySpinner = QSpinBox(
            self,
            minimum=self.iteratorDelayMinimum,
            maximum=self.iteratorDelayMaximum,
            objectName='iteratorDelaySpinner',
            toolTip='Frequency iterator delay'
        )

        self.stationStatus = QLabel('.', objectName='stationStatus')


    def setupUiLayout(self):
        mainColumnWrapper = QVBoxLayout(self)
        mainColumnWrapper.setSpacing(20)

        mainColumnWrapper.addWidget(self.stationTitle)

        frequencySpinnerRow = QHBoxLayout()
        frequencySpinnerRow.addWidget(self.cloudSyncToggle if self.isStationMode else self.frequencySyncButton)
        frequencySpinnerRow.addWidget(self.frequencySpinner)
        frequencySpinnerRow.addWidget(self.frequencySpinnerStepList)

        mainColumnWrapper.addLayout(frequencySpinnerRow)
        mainColumnWrapper.addWidget(self.historyTable)

        iteratorRadioGroupBox = QGroupBox('Iterator', self)
        iteratorRadioGroupBox.setAlignment(Qt.AlignHCenter)
        mainColumnWrapper.addWidget(iteratorRadioGroupBox)

        iteratorRadioGroupGrid = QGridLayout(iteratorRadioGroupBox)
        iteratorRadioGroupGrid.setVerticalSpacing(15)
        iteratorRadioGroupGrid.setContentsMargins(20,10,20,20)
        iteratorRadioGroupGrid.addWidget(self.iteratorFrequencyWithinPresetModeRadio, 0, 0)
        iteratorRadioGroupGrid.addWidget(self.iteratorFrequencyPresetHelp, 0, 1)
        iteratorRadioGroupGrid.addWidget(self.iteratorFrequencyByStepModeRadio, 1, 0)
        iteratorRadioGroupGrid.addWidget(self.iteratorFrequencyStepList, 1, 1)

        iteratorToggleRow = QHBoxLayout()
        iteratorToggleRow.addWidget(self.iteratorToggle)
        iteratorToggleRow.addWidget(self.iteratorDelaySpinner)
        mainColumnWrapper.addLayout(iteratorToggleRow)

        mainColumnWrapper.addWidget(self.stationStatus)



    def setupHandlers(self):
        self.cloudSyncToggle.clicked.connect(self.toggleCloudSync)

        self.frequencySyncButton.clicked.connect(
            lambda:
                self.syncWithCurrentStation.emit(self.frequency, self.currentPreset['name'])
        )

        self.frequencySpinner.valueChanged.connect(self.setFrequency)

        self.historyTable.itemDoubleClicked.connect(self.onFrequencyHistoryItemDoubleClicked)

        self.iteratorFrequencyPresetHelp.clicked.connect(self.showPresetFrequenciesDialog)

        self.frequencySpinnerStepList.currentIndexChanged.connect(self.onFrequencyStepIndexChanged)
        self.iteratorFrequencyStepList.currentIndexChanged.connect(self.onFrequencyStepIndexChanged)

        self.iteratorFrequencyRadioGroup.buttonClicked.connect(self.setIteratorMode)

        self.iteratorToggle.clicked.connect(self.onFrequencyIteratorToggled)

        self.iteratorDelaySpinner.valueChanged.connect(self.setIteratorDelay)

        self.stopStation.connect(self.terminateIterator)


    def syncUI(self):
        if self.isLocalModeActive:
            self.cloudSyncToggle.setStyleSheet('border: 5px solid #b8b8b8;')
        else:
            self.cloudSyncToggle.setStyleSheet('border: 5px solid #5eba74;')

        self.frequencySpinner.setValue(int(self.frequency))

        self.frequencySpinner.setSingleStep(self.frequencyStep)
        self.frequencySpinnerStepList.setCurrentIndex(self.frequencySpinnerStepList.findText(str(self.frequencyStep)))
        self.iteratorFrequencyStepList.setCurrentIndex(self.iteratorFrequencyStepList.findText(str(self.frequencyStep)))

        if self.iteratorMode == IteratorMode.WithinPreset:
            self.iteratorFrequencyWithinPresetModeRadio.setChecked(True)
        elif self.iteratorMode == IteratorMode.ByStep:
            self.iteratorFrequencyByStepModeRadio.setChecked(True)

        self.iteratorToggle.setIcon(self.stopIcon if self.isFrequencyIteratorActive else self.playIcon)

        self.iteratorDelaySpinner.setValue(self.iteratorDelay)

        disabled = not self.isLocalModeActive

        self.iteratorFrequencyStepList.setDisabled(disabled)
        self.frequencySpinner.setDisabled(disabled)
        self.frequencySpinnerStepList.setDisabled(disabled)
        self.historyTable.setDisabled(disabled)

        self.iteratorFrequencyWithinPresetModeRadio.setDisabled(disabled)
        self.iteratorFrequencyByStepModeRadio.setDisabled(disabled)
        self.iteratorFrequencyPresetHelp.setDisabled(disabled)

        self.iteratorFrequencyStepList.setDisabled(disabled)
        self.iteratorToggle.setDisabled(disabled)
        self.iteratorDelaySpinner.setDisabled(disabled)


    @Slot()
    def setupAnthena(self, frequencyRange):
        if frequencyRange == '1.2':
            self.anthena = Anthena_1_2()
            self.anthena.setupComPort()

            self.anthena.onRssiReceived.connect(self.onAnthenaRssiReceived)
            self.anthena.onRssiReadError.connect(self.onAnthenaRssiReadError)

            self.onFrequencySet.connect(self.anthena.setAnthenaFrequency)
        else:
            return


    @Slot(str)
    def setRssiForLatestFrequency(self, rssi):
        self.historyTable.setItem(0, 1, QTableWidgetItem(rssi))

    @Slot(str, str)
    def onAnthenaRssiReceived(self, frequency, rssi):
        if frequency != self.frequency:
            return
        self.setRssiForLatestFrequency(rssi)
        self.setStationStatus(f'RSSI received: {rssi}')
        if not self.isLocalModeActive:
            self.anthenaRssiReceived.emit(rssi)


    @Slot()
    def onAnthenaRssiReadError(self):
        self.setStationStatus('RSSI read error.')


    @Slot(str)
    def onAnthenaFrequencyReceived(self, frequency):
        print(f'RabbitMQ: received frequency {frequency}')
        if not self.isLocalModeActive:
            self.setFrequency(frequency)
            self.setStationStatus(f'Received {frequency}')
            self.anthena.setAnthenaFrequency()


    @Slot(int)
    @Slot(str)
    def setFrequency(self, frequency):
        frequencyStr = str()
        if isinstance(frequency, int):
            frequencyStr = str(frequency)
        elif isinstance(frequency, str):
            frequencyStr = frequency

        if frequencyStr == self.frequency:
            return

        self.frequency = frequencyStr

        self.addToFrequencyHistory(frequencyStr)

        self.onFrequencySet.emit(frequencyStr)

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


    @Slot(str)
    def addToFrequencyHistory(self, frequency=''):
        self.historyTable.insertRow(0)
        self.historyTable.setItem(0, 0, QTableWidgetItem(str(frequency)))
        self.historyTable.setItem(0, 1, QTableWidgetItem('...'))

        if self.historyTable.rowCount() > self.maxHistoryLength:
            self.historyTable.removeRow(self.maxHistoryLength)


    @Slot()
    def onFrequencyHistoryItemDoubleClicked(self, item):
        frequencyColumn = 0
        if item.column() == frequencyColumn:
            self.setFrequency(item.text())


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


    @Slot()
    def showPresetFrequenciesDialog(self):
        dialog = FrequencyPresetListDialog(self.currentPreset)
        dialog.exec_()


    @Slot()
    def setStationStatus(self, status):
        self.stationStatus.setText(status)


    @Slot(bool)
    def toggleCloudSync(self):
        self.isLocalModeActive = not self.isLocalModeActive

        self.terminateIterator()

        self.setStationStatus('Station is set to local mode' if self.isLocalModeActive else 'Station is listening to cloud')

        self.localModeActivated.emit(self.isLocalModeActive)

        self.syncUI()


    def startIterator(self, implicitTrigger):
        self.isFrequencyIteratorActive = True

        self.iterator = FrequencyIterator()
        self.iterator.emitFrequency.connect(self.setFrequency)

        if self.iteratorMode == IteratorMode.WithinPreset:
            self.iterator.start(self.currentPreset['presetFrequencies'], self.frequency, self.iteratorDelay, implicitTrigger)

        elif self.iteratorMode == IteratorMode.ByStep:
            list = []
            for value in range(
                int(self.currentPreset["minFrequency"]),
                int(self.currentPreset["maxFrequency"]),
                self.frequencyStep
            ):
                list.append(str(value))

            self.iterator.start(list, self.frequency, self.iteratorDelay, implicitTrigger)

        self.setStationStatus('Iterator started')

        self.syncUI()


    def terminateIterator(self):
        self.isFrequencyIteratorActive = False
        if self.iterator:
            self.iterator.stop()

        self.setStationStatus('Iterator terminated')

        self.syncUI()



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
