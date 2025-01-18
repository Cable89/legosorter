import argparse
import logging
import threading
import queue
import time
from queue_rows import *


# tasks_queue contains tasks/commands to be executed by the MachineController
# events_queue contains events/messages/responses from the MachineController
class MachineController(threading.Thread):
    def __init__(self, tasks_queue, events_queue):
        #super(MachineController, self).__init__()
        threading.Thread.__init__(self)
        logging.basicConfig(format='(%(threadName)-10s) %(message)s')

        self.tasks_queue  = tasks_queue
        self.events_queue = events_queue

        self.running = True

    def run(self):
        logging.info("Starting")
        while self.running:
            for task in queue_rows(self.tasks_queue):
                self.handle_task(task)

    def handle_task(self, task):
        logging.debug("Task: {}".format(task))
        if task == "stop":
            self.stop()
        if task == "ping":
            self.events_queue.put("pong")

    def stop(self):
        if self.running:
            logging.info("Machine Controller Stopping")
        self.running = False

    def __del__(self):
        self.stop()
