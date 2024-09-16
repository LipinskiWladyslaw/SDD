# This Python file uses the following encoding: utf-8

import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QToolButton, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, Slot, QThread
import json
import widget_images
from utility import loadQssFile
from station import StationWidget
from rabbitMQ_utils import RabbitMQPublisher, RabbitMQConsumer



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
                station = StationWidget(self.stationConfigs[i], self.presets)
                self.stationsWidgets[i] = station

                self.setupRabbitMQ(station)

                station.syncWithCurrentStation.connect(self.setFrequencyForAllStationsOfSameType)
                self.layout().addWidget(station)


        stopAllLayout = QVBoxLayout(spacing=10, alignment=Qt.AlignVCenter)

        self.stopAllButton = QToolButton(self, objectName='stopAllButton', toolTip='Stop all station iterators')
        self.stopAllButton.setIcon(QIcon(QPixmap(':/img/stop.png')))
        self.stopAllButton.clicked.connect(self.stopAllStations)

        stopAllLayout.addWidget(self.stopAllButton)
        stopAllLayout.addWidget(QLabel('Stop All'))

        self.layout().addLayout(stopAllLayout)


    def setupRabbitMQ(self, station):

        publisherQueue = f'frequency{station.stationName}'
        publisherExchange = f'frequency{station.stationName}'
        station.rabbitMQPublisher = RabbitMQPublisher(publisherQueue, publisherExchange)

        station.publisherThread = QThread()
        station.rabbitMQPublisher.moveToThread(station.publisherThread)
        station.publisherThread.start()

        station.publishFrequency.connect(station.rabbitMQPublisher.publish)
        station.rabbitMQPublisher.published.connect(station.onPublishedCallback)
        station.rabbitMQPublisherStart.connect(station.rabbitMQPublisher.start)

        station.rabbitMQPublisherStart.emit()


        consumerQueue = f'RSSI{station.stationName}'
        station.rabbitMQConsumer = RabbitMQConsumer(consumerQueue)

        station.consumerThread = QThread()
        station.rabbitMQConsumer.moveToThread(station.consumerThread)
        station.consumerThread.start()

        station.rabbitMQConsumer.received.connect(station.onReceivedCallback)
        station.rabbitMQConsumerStart.connect(station.rabbitMQConsumer.start)

        station.rabbitMQConsumerStart.emit()


    @Slot()
    def stopAllStations(self):
        for station in self.stationsWidgets:
            station.stopStation.emit()


    @Slot(str, str)
    def setFrequencyForAllStationsOfSameType(self, frequency, presetName):
        print(f'frequency: {frequency} {type(frequency)}')
        print(f'presetName: {presetName} {type(presetName)}')
        self.stopAllStations()
        for station in self.stationsWidgets:
            print(station.currentPreset['name'])
            if station.currentPreset['name'] == presetName:
                station.insertFrequency.emit(frequency)


def main():
    app = QApplication(sys.argv)

    mainWidget = MainWidget()
    mainWidget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
