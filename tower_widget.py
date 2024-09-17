# This Python file uses the following encoding: utf-8

import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QToolButton, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, Slot, QThread
import json
import widget_images
from utility import loadQssFile
from station_widget import StationWidget
from rabbit_utils import RabbitMQPublisher, RabbitMQConsumer



class MainWidget(QWidget):

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

        self.setStyleSheet(loadQssFile('widget_styles.qss'))
        self.setLayout(QHBoxLayout())

        self.stationConfigs = list(range(4))
        self.stationsWidgets = list(range(4))
        self.presets = list(range(4))

        with open('frequency_presets.json') as presets_file:
            self.presets = json.load(presets_file)

        with open('tower_stations_config.json') as stationConfigsFile:
            self.stationConfigs = json.load(stationConfigsFile)
            isStationMode = False

            for i in range(len(self.stationConfigs)):
                station = StationWidget(self.stationConfigs[i], self.presets, isStationMode)
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

        station.onFrequencySet.connect(station.rabbitMQPublisher.publish)
        station.rabbitMQPublisher.published.connect(lambda value: self.onPublishedCallback(station, value))
        station.rabbitMQPublisherStart.connect(station.rabbitMQPublisher.start)

        station.rabbitMQPublisherStart.emit()


        consumerQueue = f'RSSI{station.stationName}'
        station.rabbitMQConsumer = RabbitMQConsumer(consumerQueue)

        station.consumerThread = QThread()
        station.rabbitMQConsumer.moveToThread(station.consumerThread)
        station.consumerThread.start()

        station.rabbitMQConsumer.received.connect(lambda value: self.onReceivedCallback(station, value))
        station.rabbitMQConsumerStart.connect(station.rabbitMQConsumer.start)

        station.rabbitMQConsumerStart.emit()


    @Slot()
    def stopAllStations(self):
        for station in self.stationsWidgets:
            station.stopStation.emit()


    @Slot(str, str)
    def setFrequencyForAllStationsOfSameType(self, frequency, presetName):
        self.stopAllStations()
        for station in self.stationsWidgets:
            print(station.currentPreset['name'])
            if station.currentPreset['name'] == presetName:
                station.insertFrequency.emit(frequency)


    @Slot()
    def onPublishedCallback(self, station, value):
        station.setStationStatus(f'Published {value}')
        print(f'PUBLISHED: {value}')

    @Slot()
    def onReceivedCallback(self, station, value):
        station.setStationStatus(f'Received {value}')
        print(f'RECEIVED: {value}')


def main():
    app = QApplication(sys.argv)

    mainWidget = MainWidget()
    mainWidget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
