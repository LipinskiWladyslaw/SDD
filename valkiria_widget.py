# This Python file uses the following encoding: utf-8

import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from PySide6.QtCore import QThread, Slot
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

        self.stationConfig = None
        self.stationWidgets = None
        self.presets = None
        self.isStationMode = True
        self.isLocalModeActive = False

        with open('frequency_presets.json') as presets_file:
            self.presets = json.load(presets_file)

        with open('valkiria_config.json') as stationConfigFile:
            self.stationConfig = json.load(stationConfigFile)

            station = StationWidget(self.stationConfig, self.presets, self.isStationMode)
            self.stationWidget = station

            station.localModeActivated.connect(self.onLocalModeSet)

            self.layout().addWidget(station)

            self.setupRabbitMQ(station)


    def setupRabbitMQ(self, station):

        publisherQueue = f'RSSI{station.stationName}'
        publisherExchange = f'RSSI{station.stationName}'
        station.rabbitMQPublisher = RabbitMQPublisher(publisherQueue, publisherExchange)

        station.publisherThread = QThread()
        station.rabbitMQPublisher.moveToThread(station.publisherThread)
        station.publisherThread.start()

        # station.onFrequencySet.connect(station.rabbitMQPublisher.publish)
        station.rabbitMQPublisher.published.connect(lambda value: self.afterPublished(station, value))
        station.rabbitMQPublisherStart.connect(station.rabbitMQPublisher.start)

        station.rabbitMQPublisherStart.emit()


        consumerQueue = f'frequency{station.stationName}'
        station.rabbitMQConsumer = RabbitMQConsumer(consumerQueue)

        station.consumerThread = QThread()
        station.rabbitMQConsumer.moveToThread(station.consumerThread)
        station.consumerThread.start()

        station.rabbitMQConsumer.received.connect(lambda value: self.onReceive(station, value))
        station.rabbitMQConsumerStart.connect(station.rabbitMQConsumer.start)

        station.rabbitMQConsumerStart.emit()


    @Slot()
    def onReceive(self, station, message):
        print(f'isLocalModeActive: {self.isLocalModeActive}, {message}')
        if not self.isLocalModeActive:
            station.setFrequency(message)
            station.setStationStatus(f'Received {message}')
            print(f'RECEIVED: {message}')


    @Slot()
    def afterPublished(station, message):
        station.setStationStatus(f'Published {message}')
        print(f'PUBLISHED: {message}')


    @Slot()
    def onLocalModeSet(self, isLocalModeActive):
        self.isLocalModeActive = isLocalModeActive
        print(f'isLocalModeActive: {isLocalModeActive}')


def main():
    app = QApplication(sys.argv)

    mainWidget = MainWidget()
    mainWidget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
