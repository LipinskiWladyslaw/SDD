# This Python file uses the following encoding: utf-8

import asyncio
import queue
import threading
from PySide6.QtCore import QObject, Signal

class FrequencyIterator(QObject):
    frequencyRequested = Signal(str)

    def __init__(self):
        super().__init__()

        self.queue = None
        self.isStopped = True
        self.currentTask = None
        self.loop = None


    def start(self, list, current, delay, implicitTrigger):
        self.queue = queue.Queue()
        self.list = list
        self.delay = delay
        self.implicitTrigger = implicitTrigger

        isExactIndex = True

        try:
            currentIndex = list.index(current)
        except ValueError:
            isExactIndex = False

            currentIndex = self.findFrequencyIndexInList(list, current)

        nextIndex = currentIndex if not isExactIndex else currentIndex + 1

        if self.implicitTrigger:
            self.frequencyRequested.emit(list[nextIndex])
            nextIndex += 1

        for item in list[nextIndex:]:
            self.queue.put(item)

        if self.isStopped:
            self.isStopped = False
            threading.Thread(target=self.processQueue).start()

    def stop(self):
        self.isStopped = True
        if self.currentTask:
            self.currentTask.cancel()

        if self.loop and self.loop.is_running():
            self.loop.stop()


    async def process_item(self, frequency):
        self.currentTask = asyncio.create_task(self.createTask(frequency, self.delay))
        try:
            await self.currentTask

        except asyncio.exceptions.CancelledError:
            pass  # Ignore cancelled tasks on shutdown


    async def createTask(self, frequency, delay):
        await asyncio.sleep(self.delay)
        self.frequencyRequested.emit(frequency)

    def processQueue(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        while not self.isStopped:
            if self.queue.qsize() > 0:
                try:
                    self.loop.run_until_complete(self.process_item(self.queue.get()))
                except RuntimeError:
                    pass # ignore Event loop stopped before Future completed

            else:
                for item in self.list:
                    self.queue.put(item)

        self.loop.close()


    def findFrequencyIndexInList(self, list, frequency):
        i = 0

        while int(list[i]) < int(frequency):
            i += 1
            if i >= len(list):
                return 0

        return i
