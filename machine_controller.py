import argparse
import logging
import threading
import queue
import time
import sys
from queue_rows import *

# Pin mapping
PIN_OPTOELECTRIC = 18 # BCM

# tasks_queue contains tasks/commands to be executed by the MachineController
# events_queue contains events/messages/responses from the MachineController
# desktopDebug option can be used to debug this module on other systems than raspberry pi
class MachineController(threading.Thread):
    def __init__(self, tasks_queue, events_queue, desktopDebug=False):
        #super(MachineController, self).__init__()
        threading.Thread.__init__(self)
        logging.basicConfig(format='(%(threadName)-10s) %(message)s')

        self.tasks_queue  = tasks_queue
        self.events_queue = events_queue

        self.running = True

        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO

            GPIO.setmode(GPIO.BCM) # Refer to pins by the pin number in the GPIO port
            #GPIO.setmode(GPIO.BOARD) Refer to pins by the pin numbner on the board header
            GPIO.setup(PIN_OPTOELECTRIC, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            GPIO.add_event_detect(PIN_OPTOELECTRIC, GPIO.FALLING, callback=self.optoelectric_callback, bouncetime=50)

        except ModuleNotFoundError:
            logging.error("Module RPi.GPIO not found. Install via 'pip install RPi.GPIO'")
            if not desktopDebug:
                self.stop()
                #self.join()
                #sys.exit(1)
            else:
                logging.info("Continuing anyway")

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

    def optoelectric_callback(self, channel):
        if not self.GPIO.input(PIN_OPTOELECTRIC):
            logging.debug("Optoelectrig triggered: Falling")
            logging.debug("channel: {}".format(channel))
        else:
            logging.debug("Optoelectrig triggered: Rising")

    def stop(self):
        if self.running:
            logging.info("Machine Controller Stopping")
        try:
            GPIO.cleanup()
        except NameError as e: # Don't care about cleanup of GPIO if we don't have the GPIO module
            logging.debug(e)
        self.running = False

    def __del__(self):
        self.stop()
