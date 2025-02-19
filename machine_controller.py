import argparse
import logging
import threading
import queue
import time
import sys
from queue_rows import *
import usbrelay_py

# Timings in seconds
TIME_BIN1 = 0.5
TIME_BIN2 = 0.9
TIME_BIN3 = 1.5
TIME_BIN4 = 2
TIME_BIN5 = 2.5


# Pin mapping
PIN_OPTOELECTRIC = 24 # BCM
PIN_BUTTON = 27 # BCM

# USB relay boards

# usbrelay1-1.3 # Top right relay board
# usbrelay1-1.3_1 # Pneumatic 1
# usbrelay1-1.3_2 # Pneumatic 2
# usbrelay1-1.3_3 # Pneumatic 3
# usbrelay1-1.3_4 # Pneumatic 4

# usbrelay1-1.4 # Bottom right relay board
# usbrelay1-1.4_1 Pneumatic 5
# usbrelay1-1.4_2 Pneumatic 6
# usbrelay1-1.4_3 Pneumatic 7
# usbrelay1-1.4_4 Conveyor belt

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
        self.conveyor_running = False

        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO

            GPIO.setmode(GPIO.BCM) # Refer to pins by the pin number in the GPIO port
            #GPIO.setmode(GPIO.BOARD) Refer to pins by the pin numbner on the board header
            GPIO.setup(PIN_OPTOELECTRIC, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(PIN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            GPIO.add_event_detect(PIN_OPTOELECTRIC, GPIO.FALLING, callback=self.optoelectric_callback, bouncetime=500)
            GPIO.add_event_detect(PIN_BUTTON, GPIO.FALLING, callback=self.button_callback, bouncetime=200)

        except ModuleNotFoundError:
            logging.error("Module RPi.GPIO not found. Install via 'pip install RPi.GPIO'")
            if not desktopDebug:
                self.stop()
                #self.join()
                #sys.exit(1)
            else:
                logging.info("Continuing anyway")
        try:
            self.boards = self.init_usbrelay()
        except:
            self.stop()
        
        self.start_conveyor()
   
   # Relay boards are using same COM string, python library cannot take path?, edit library to take path? (c library works with path)
   # Relay objects are unique, keep track of them myself?
   # Expose path in python?
   # Path can be used with no modifications to driver
    def init_usbrelay(self):
        count = usbrelay_py.board_count()
        logging.info("Found {} usb relay boards".format(count))
        boards = usbrelay_py.board_details()
        logging.info("Boards: {}".format(boards))
        return boards

    # Duration in seconds (or partial seconds i.e. 0.5)
    def pulse_pneumatic(self, number, duration=0.2):
        result = usbrelay_py.board_control(self.boards[0][0], number, 1)
        #logging.debug(result)
        timer = threading.Timer(duration, self.pulse_pneumatic_callback, [number])
        timer.start()

    def pulse_pneumatic_callback(self, number):
        result = usbrelay_py.board_control(self.boards[0][0], number, 0)
        #logging.debug(result)

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
        if task == "wololo":
            self.pulse_pneumatic(1, 0.5)

    def optoelectric_callback(self, channel):
        if not self.GPIO.input(PIN_OPTOELECTRIC):
            #logging.debug("Optoelectrig triggered: Falling")
            timer = threading.Timer(TIME_BIN2, self.pulse_pneumatic, [1])
            timer.start()
        #else:
            #logging.debug("Optoelectrig triggered: Rising")

    def button_callback(self, channel):
        if not self.GPIO.input(PIN_BUTTON):
            logging.debug("Button pressed")
            if self.conveyor_running:
                self.stop_conveyor()
            else:
                self.start_conveyor()
        #else:
            #logging.debug("Button released")
    
    # Does a conveyor object make sense?
    # Not now but with encoder later?
    def start_conveyor(self):
        logging.info("Starting Conveyor")
        #result = usbrelay_py.board_control(self.boards[1][0], 4, 1)
        result = usbrelay_py.board_control("/dev/usbrelay1-1.4", 4, 1)
        logging.debug(result)
        self.conveyor_running = True

    def stop_conveyor(self):
        logging.info("Stopping Conveyor")
        result = usbrelay_py.board_control(self.boards[1][0], 4, 0)
        result = usbrelay_py.board_control("/dev/usbrelay1-1.4", 4, 0)
        logging.debug(result)
        self.conveyor_running = False

    def stop(self):
        self.stop_conveyor()
        if self.running:
            logging.info("Machine Controller Stopping")
        try:
            self.GPIO.cleanup()
        except NameError as e: # Don't care about cleanup of GPIO if we don't have the GPIO module
            logging.debug(e)
        self.running = False

    def __del__(self):
        self.stop()
