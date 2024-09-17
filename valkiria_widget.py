# This Python file uses the following encoding: utf-8

import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from PySide6.QtCore import QThread
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

        with open('frequency_presets.json') as presets_file:
            self.presets = json.load(presets_file)

        with open('valkiria_config.json') as stationConfigFile:
            self.stationConfig = json.load(stationConfigFile)

            station = StationWidget(self.stationConfig, self.presets)
            self.stationWidget = station

            self.layout().addWidget(station)

            self.setupRabbitMQ(station)


    def setupRabbitMQ(self, station):

        publisherQueue = f'RSSI{station.stationName}'
        publisherExchange = f'RSSI{station.stationName}'
        station.rabbitMQPublisher = RabbitMQPublisher(publisherQueue, publisherExchange)

        station.publisherThread = QThread()
        station.rabbitMQPublisher.moveToThread(station.publisherThread)
        station.publisherThread.start()

        # station.publishFrequency.connect(station.rabbitMQPublisher.publish)
        station.rabbitMQPublisher.published.connect(station.onPublishedCallback)
        station.rabbitMQPublisherStart.connect(station.rabbitMQPublisher.start)

        station.rabbitMQPublisherStart.emit()


        consumerQueue = f'frequency{station.stationName}'
        station.rabbitMQConsumer = RabbitMQConsumer(consumerQueue)

        station.consumerThread = QThread()
        station.rabbitMQConsumer.moveToThread(station.consumerThread)
        station.consumerThread.start()

        station.rabbitMQConsumer.received.connect(station.setFrequency)
        station.rabbitMQConsumer.received.connect(station.onReceivedCallback)
        station.rabbitMQConsumerStart.connect(station.rabbitMQConsumer.start)

        station.rabbitMQConsumerStart.emit()


def main():
    app = QApplication(sys.argv)

    mainWidget = MainWidget()
    mainWidget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
