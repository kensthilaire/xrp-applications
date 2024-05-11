import bluetooth
import io
import os
import micropython
from micropython import const
import machine
import time

from ble.ble_uart_peripheral import BLEUART

_MP_STREAM_POLL = const(3)
_MP_STREAM_POLL_RD = const(0x0001)

_timer = machine.Timer(-1)

waitingForTimer = False

# Batch writes into 50ms intervals.
def schedule_in(handler, delay_ms):
    def _wrap(_arg):
        handler()
    #using PERIODIC vs ONE_SHOT because sometimes ONE_SHOT didn't fire when IMU timer was going
    #We deinit() once the timer goes off. So for all means a ONE_SHOT.
    _timer.init(mode=machine.Timer.PERIODIC, period=delay_ms, callback=_wrap)

# Simple buffering stream to support the dupterm requirements.
class BLEUARTStream(io.IOBase):
    def __init__(self, name=None):
        ble = bluetooth.BLE()
        if name == None:
            x = (''.join(['{:02x}'.format(b) for b in machine.unique_id()]))
            name = 'XRP-' + x[11:]
        self._uart = BLEUART(ble, name=name, rxbuf = 250)
        self._tx_buf = bytearray()
        self._uart.irq(self._indicate_handler)

    def _indicate_handler(self):
        if waitingForTimer:
            return
        if self._tx_buf:
            self._flush()
            
    def _timer_handler(self):
        waitingForTimer = False
        _timer.deinit()
        if self._tx_buf:
            self._flush()

    def read(self, sz=None):
        return self._uart.read(sz)

    def readinto(self, buf):
        avail = self._uart.read(len(buf))
        if not avail:
            return None
        for i in range(len(avail)):
            buf[i] = avail[i]
        return len(avail)

    def ioctl(self, op, arg):
        if op == _MP_STREAM_POLL:
            if self._uart.any():
                return _MP_STREAM_POLL_RD
        return 0

    def _flush(self):
        data = self._tx_buf[0:200]
        self._tx_buf = self._tx_buf[200:]
        self._uart.write(data)
        #if self._tx_buf:
            #schedule_in(self._flush, 50)

    def write(self, buf):
        #machine.Pin("LED",Pin.OUT).on()
        empty = not self._tx_buf
        self._tx_buf += buf
        if empty:
            waitingForTimer = True
            schedule_in(self._timer_handler, 50)

            self._flush()
        '''
            if len(self._tx_buf) == 1:
                schedule_in(self._indicate_handler, 80)
            else:
                self._flush()
        '''

