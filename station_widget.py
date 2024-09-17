# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import (
QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox, QListWidget, QCheckBox,
QGroupBox, QButtonGroup, QGridLayout, QRadioButton, QToolButton, QDialog
)
from PySide6.QtCore import Signal, Slot, Qt, QMetaEnum, QThread, QTimer
from PySide6.QtGui import QPixmap, QIcon
from iterator import FrequencyIterator
from utility import findPresetByName

import logging

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

# TODO: history track frequency/RSSI
# TODO: 1.2/5.8 iterator restart?
# TODO: station status label (write text in each method)

class IteratorMode(QMetaEnum):
    WithinPreset = 'Within Preset'
    ByStep = 'By Step'

class StationWidget(QWidget):
    iteratorDelayMinimum = 1
    iteratorDelayMaximum = 10
    defaultIteratorDelay = 3
    defaultIteratorMode = IteratorMode.WithinPreset


    stopStation = Signal()
    syncWithCurrentStation = Signal(str, str)
    localModeActivated = Signal(bool)
    onFrequencySet = Signal(str)
    rabbitMQPublisherStart = Signal()
    rabbitMQConsumerStart = Signal()

    def __init__(self, config, presets, isStationMode, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

        self.presets = presets
        self.config = config
        self.isStationMode = isStationMode
        self.currentPreset = findPresetByName(config["defaultPresetName"], config, presets)

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
        self.maxHistoryLength = 50

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


    def setupUiElements(self):
        self.stationTitle = QLabel(
            f'{self.config["location"]} [{self.config["stationName"]}]',
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

        self.frequencyHistoryList = QListWidget(toolTip='History of recent set frequencies')

        self.iteratorFrequencyWithinPresetModeRadio = QRadioButton(IteratorMode.WithinPreset)
        self.iteratorFrequencyByStepModeRadio = QRadioButton(IteratorMode.ByStep)

        self.iteratorFrequencyRadioGroup = QButtonGroup(self, exclusive=True)
        self.iteratorFrequencyRadioGroup.addButton(self.iteratorFrequencyWithinPresetModeRadio)
        self.iteratorFrequencyRadioGroup.addButton(self.iteratorFrequencyByStepModeRadio)

        self.iteratorFrequencyPresetList = QComboBox(toolTip='Selected frequencies preset')
        self.iteratorFrequencyPresetList.addItems(map(lambda preset:preset["name"], self.presets))

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

        mainColumnWrapper.addWidget(self.stationStatus)



    def setupHandlers(self):
        self.cloudSyncToggle.clicked.connect(self.toggleCloudSync)

        self.frequencySyncButton.clicked.connect(
            lambda:
                self.syncWithCurrentStation.emit(self.frequency, self.currentPreset['name'])
        )

        self.frequencySpinner.valueChanged.connect(self.setFrequency)

        self.frequencyHistoryList.itemDoubleClicked.connect(self.onFrequencyHistoryItemDoubleClicked)

        self.iteratorFrequencyPresetList.currentIndexChanged.connect(self.onFrequencyPresetIndexChanged)
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

        disabled = not self.isLocalModeActive

        self.iteratorFrequencyStepList.setDisabled(disabled)
        self.frequencySpinner.setDisabled(disabled)
        self.frequencySpinnerStepList.setDisabled(disabled)
        self.frequencyHistoryList.setDisabled(disabled)

        self.iteratorFrequencyWithinPresetModeRadio.setDisabled(disabled)
        self.iteratorFrequencyByStepModeRadio.setDisabled(disabled)
        self.iteratorFrequencyPresetHelp.setDisabled(disabled)

        self.iteratorFrequencyPresetList.setDisabled(disabled)
        self.iteratorFrequencyStepList.setDisabled(disabled)
        self.iteratorToggle.setDisabled(disabled)
        self.iteratorDelaySpinner.setDisabled(disabled)


    @Slot(int)
    @Slot(str)
    def setFrequency(self, frequency):
        print(type(frequency))
        print(f'SET: {frequency}')
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
    def addToFrequencyHistory(self, frequency):
        print(f'HISTORY add: {frequency}, {type(frequency)}')
        self.frequencyHistory.insert(0, int(frequency))
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
