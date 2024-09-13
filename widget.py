# This Python file uses the following encoding: utf-8

import sys
import json
import widget_images
from utility import loadQssFile
from station import StationWidget
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout

class MainWidget(QWidget):

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

        self.setStyleSheet(loadQssFile('widget_styles.qss'))
        self.setLayout(QHBoxLayout())

        self.stationConfigs = list(range(4))
        self.stationsWidgets = list(range(4))
        self.presets = list(range(4))

        with open('presets.json') as presets_file:
            self.presets = json.load(presets_file)

        with open('stations.json') as stationConfigsFile:
            self.stationConfigs = json.load(stationConfigsFile)

            for i in range(len(self.stationConfigs)):
                self.stationsWidgets[i] = StationWidget(self.stationConfigs[i], self.presets)
                self.layout().addWidget(self.stationsWidgets[i])


def main():
    app = QApplication(sys.argv)

    mainWidget = MainWidget()
    mainWidget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
