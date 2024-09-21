# This Python file uses the following encoding: utf-8

import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
import json
import widget_images
from utility import loadQssFile
from station_widget import StationWidget


class MainWidget(QWidget):

    isStationMode = True

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

        dirPath = f'{sys.path[0]}\..\\'
        stylesPath = f'{sys.path[0]}\\widget_styles.qss'

        self.setStyleSheet(loadQssFile(stylesPath))
        self.setLayout(QHBoxLayout())


        print(dirPath + 'frequency_presets.json')

        with open(dirPath + 'frequency_presets.json') as presets_file:
            self.presets = json.load(presets_file)

        with open(dirPath + 'valkiria_config.json') as stationConfigFile:
            self.stationConfig = json.load(stationConfigFile)

            station = StationWidget(self.stationConfig, self.presets, self.isStationMode)
            self.stationWidget = station

            self.layout().addWidget(station)


def main():
    app = QApplication(sys.argv)

    mainWidget = MainWidget()
    mainWidget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
