# This Python file uses the following encoding: utf-8

import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QToolButton, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, Slot
import json
import widget_images
from utility import loadQssFile
from station_widget import StationWidget


class MainWidget(QWidget):

    isStationMode = False # Always False for Tower widget

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

        dirPath = f'{sys.path[0]}\..\\'
        stylesPath = f'{sys.path[0]}\\widget_styles.qss'

        self.setStyleSheet(loadQssFile(stylesPath))
        self.setLayout(QHBoxLayout())

        with open(dirPath + 'frequency_presets.json') as presets_file:
            self.presets = json.load(presets_file)

        with open(dirPath + 'tower_stations_config.json') as stationConfigsFile:
            self.stationConfigs = json.load(stationConfigsFile)

            stationsCount = len(self.stationConfigs)
            self.stationsWidgets = list(range(stationsCount))

            for i in range(stationsCount):
                station = StationWidget(self.stationConfigs[i], self.presets, self.isStationMode)
                self.stationsWidgets[i] = station

                station.syncWithCurrentStation.connect(self.setFrequencyForAllStationsOfSameType)
                self.layout().addWidget(station)

        stopAllLayout = QVBoxLayout(spacing=10, alignment=Qt.AlignVCenter)

        self.stopAllButton = QToolButton(self, objectName='stopAllButton', toolTip='Stop all station iterators')
        self.stopAllButton.setIcon(QIcon(QPixmap(':/img/stop.png')))
        self.stopAllButton.clicked.connect(self.stopAllStations)

        stopAllLayout.addWidget(self.stopAllButton)
        stopAllLayout.addWidget(QLabel('Stop All'))

        self.layout().addLayout(stopAllLayout)


    @Slot()
    def stopAllStations(self):
        for station in self.stationsWidgets:
            station.stopStation.emit()


    @Slot(str, str)
    def setFrequencyForAllStationsOfSameType(self, frequency, presetName):
        self.stopAllStations()
        for station in self.stationsWidgets:
            if station.currentPreset['name'] == presetName:
                station.setFrequency(frequency)


def main():
    app = QApplication(sys.argv)

    mainWidget = MainWidget()
    mainWidget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
