import serial
import serial.tools.list_ports


class SyrPump:

    PROMPT = {
        'I': "infusing",
        'W': "withdrawing",
        'S': "pumping program stopped",
        'P': "pumping program paused",
        'T': "pause phase",
        'U': "operational trigger wait (user wait)"
    }

    ALARM = {
        'R': "pump was reset (power was interrupted)",
        'S': "pump motor stalled",
        'T': "safe mode communications time out",
        'E': "pumping program error",
        'O': "pumping program phase is out of range"
    }

    ERROR = {
        '': "command is not recognized (‘?’ only)",
        'NA': "command is not currently applicable",
        'OOR': "command data is out of range",
        'COM': "invalid communications packet received",
        'IGN': "command ignored due to a simultaneous new phase start"
    }

    PUMP_DIRECTION = {
        'INF': 'infuse',
        'WDR': 'withdraw',
        'REV': 'reverse'
    }

    def __init__(
            self,
            port,
            baudrate=19200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=None
    ):
        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout
        )

    def __del__(self):
        self.serial.close()

    def get_diameter(self, address: int) -> float:
        r = self._cmd(address, 'DIA')
        return float(r['data'])

    def set_diameter(self, address: int, diameter: float):
        r = self._cmd(address, 'DIA', self._float(diameter))

    def get_pump_direction(self, address: int) -> str:
        r = self._cmd(address, 'DIR')
        assert r['data'] in self.PUMP_DIRECTION.keys(),\
            f"unknown direction {r['data']}"
        return self.PUMP_DIRECTION[r['data']]

    def set_pump_direction(self, address: int, direction: str):
        assert direction in self.PUMP_DIRECTION.values(), \
            f"unknown direction {direction}"
        dir = [k for k, v in self.PUMP_DIRECTION.items() if v == direction]
        r = self._cmd(address, 'DIR', dir[0])

    def _raw_cmd(self, cmd: str):
        send = cmd + '\r\n'
        send = send.encode('utf-8')
        num = self.serial.write(send)
        assert num == len(send), \
            f"only {num} of {len(send)} bytes sent to syringe pump via serial"
        receive = self.serial.read_until(b'\x03')
        assert receive[0] == 2 and receive[-1] == 3, \
            f"received bytes structure invalid"
        receive = receive[1:-1].decode('utf-8')
        return receive

    def _cmd(self, addr: int, cmd: str, *args: list[str]):
        assert 0 <= addr <= 99, "address out of range"
        fields = [str(addr), cmd, *args]
        response = self._raw_cmd(''.join(fields))
        res = dict(
            address=int(response[:2])
        )
        status = response[2]
        if status in self.PROMPT.keys():
            res['prompt'] = status
            data = response[3:]
        elif status == 'A':
            assert response[3] == '?', "'?' missing for alarm response"
            alarm_type = response[4]
            assert alarm_type in self.ALARM.keys(), \
                f"unknown alarm type: {alarm_type}"
            res['alarm'] = alarm_type
            data = response[5:]
        else:
            raise ValueError(f"unknown status: {status}")
        if data:
            if data[0] == '?':
                error = data[1:]
                assert error in self.ERROR.keys(), f"unknown error: {error}"
                raise ValueError(f"command error: {self.ERROR[error]}")
            else:
                res['data'] = data
        return res

    @staticmethod
    def _float(f: float) -> str:
        """
        Maximum of 4 digits plus 1 decimal point.
        Maximum of 3 digits to the right of the decimal point.
        """
        f = str(round(f, 3))
        if '.' in f:
            if len(f) >= 5:
                f = f[-5:]
        else:
            if len(f) >= 4:
                f = f[-4:]
        return f


if __name__ == '__main__':
    ports = serial.tools.list_ports.comports()
    p = SyrPump('COM7')
    p.set_pump_direction(0, 'infuse')
    print(r)
