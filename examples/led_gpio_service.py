#!/usr/bin/env python3
"""Controls the LEDs connected via GPIO."""
import argparse
import asyncio
import logging
import time
from functools import partial
from math import ceil
from typing import Tuple

import gpiozero
import spidev
from wyoming.asr import Transcript
from wyoming.event import Event
from wyoming.satellite import (
    RunSatellite,
    SatelliteConnected,
    SatelliteDisconnected,
    StreamingStarted,
    StreamingStopped,
)
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.vad import VoiceStarted, VoiceStopped
from wyoming.wake import Detect, Detection

_LOGGER = logging.getLogger()

LED_RED_GPIO = 22
LED_GREEN_GPIO = 23
LED_BLUE_GPIO = 27
LED_YELLOW_GPIO = None
_RED = "red"
_GREEN = "green"
_BLUE = "blue"
_YELLOW = "yellow"
LED_MAP = {
  _RED: None,
  _GREEN: None,
  _BLUE: None,
  _YELLOW: None
}

async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", required=True, help="unix:// or tcp://")
    parser.add_argument("--debug", action="store_true", help="Log DEBUG messages")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    _LOGGER.debug(args)

    _LOGGER.info("Ready")

    LED_MAP[_RED] = createLedDevice(LED_RED_GPIO)
    LED_MAP[_GREEN] = createLedDevice(LED_GREEN_GPIO)
    LED_MAP[_BLUE] = createLedDevice(LED_BLUE_GPIO)
    LED_MAP[_YELLOW] = createLedDevice(LED_YELLOW_GPIO)

    # Start server
    server = AsyncServer.from_uri(args.uri)

    try:
        await server.run(partial(LEDsEventHandler, args, LED_MAP))
    except KeyboardInterrupt:
        pass
    finally:
        for key in LED_MAP:
            led = LED_MAP[key]
            if led is not None:
                led.off()

def createLedDevice(self, gpio) -> gpiozero.LED:
    ledDevice = None
    if gpio is not None:
        ledDevice= gpiozero.LED(gpio, active_high=True)

    return ledDevice
# -----------------------------------------------------------------------------

class LEDsEventHandler(AsyncEventHandler):
    """Event handler for clients."""

    def __init__(
        self,
        cli_args: argparse.Namespace,
        leds,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.cli_args = cli_args
        self.client_id = str(time.monotonic_ns())
        self.leds = leds

        _LOGGER.debug("Client connected: %s", self.client_id)

    async def handle_event(self, event: Event) -> bool:
        _LOGGER.debug(event)

        if StreamingStarted.is_type(event.type):
            self.colorOn(_YELLOW)
        elif Detect.is_type(event.type):
            self.colorOn(_BLUE)
        elif Detection.is_type(event.type):
            self.colorOn(_BLUE)
        elif VoiceStarted.is_type(event.type):
            self.colorOn(_YELLOW)
        elif VoiceStopped.is_type(event.type):
            self.colorOff(_YELLOW)
        elif Transcript.is_type(event.type):
            self.colorOn(_GREEN)
        elif StreamingStopped.is_type(event.type):
            self.allOff()
        elif RunSatellite.is_type(event.type):
            self.allOff()
        elif SatelliteConnected.is_type(event.type):
            self.colorBlink(_GREEN)
        elif SatelliteDisconnected.is_type(event.type):
            self.colorOn(_RED)

        return True

    def colorOn(self, key: str) -> None:
        led = self.leds[key]
        if led is not None:
            led.on()

    def colorOff(self, key: str) -> None:
        led = self.leds[key]
        if led is not None:
            led.off()
    
    def colorBlink(self, key: str) -> None:
        led = self.leds[key]
        if led is not None:
            led.blink(on_time=0.3, off_time=0.3, n=3, background=False)

    def allOff(self) -> None:
        for key in self.leds:
            self.colorOff(key)

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
