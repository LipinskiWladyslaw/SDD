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

        self.setStyleSheet(loadQssFile('widget_styles.qss'))
        self.setLayout(QHBoxLayout())

        with open('frequency_presets.json') as presets_file:
            self.presets = json.load(presets_file)

        with open('valkiria_config.json') as stationConfigFile:
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
