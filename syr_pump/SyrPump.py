import serial
import serial.tools.list_ports
from typing import Any


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

    VOLUME_UNITS = {
        'U': ['\u03bcl', 'ul', 'microliter'],
        'M': ['ml', 'milliliter']
    }

    TIME_UNITS = {
        'M': ['min', 'mn', 'minute'],
        'H': ['h', 'hr', 'hour']
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
        self._cmd(address, 'DIA', self._float(diameter))

    def get_phase(self, address: int) -> int:
        r = self._cmd(address, 'PHN')
        return int(r['data'])

    def set_phase(self, address: int, phase: int):
        assert 1 <= phase <= 41, f"invalid phase number {phase}"
        self._cmd(address, 'PHN', phase)

    def get_pump_rate(self, address: int) -> dict[str, Any]:
        r = self._cmd(address, 'RAT')
        return dict(
            value=float(r['data'][:-2]),
            volume_unit=self._from_dict_key(self.VOLUME_UNITS, r['data'][-2]),
            time_unit=self._from_dict_key(self.TIME_UNITS, r['data'][-1])
        )

    def set_pump_rate(self, address: int, rate: float, volume_unit: str, time_unit: str):
        vu = self._from_dict_value(self.VOLUME_UNITS, volume_unit)
        tu = self._from_dict_value(self.TIME_UNITS, time_unit)
        self._cmd(address, 'RAT', self._float(rate), vu, tu)

    def get_pump_direction(self, address: int) -> str:
        r = self._cmd(address, 'DIR')
        return self._from_dict_key(self.PUMP_DIRECTION, r['data'])

    def set_pump_direction(self, address: int, direction: str):
        d = self._from_dict_value(self.PUMP_DIRECTION, direction)
        self._cmd(address, 'DIR', d)

    def get_buzzer(self, address: int) -> bool:
        """
        return True if buzzer is on continuously or beeping
        """
        r = self._cmd(address, 'BUZ')
        return bool(int(r['data']))

    def set_buzzer(self, address: int, buzzer: bool, ntime=0):
        """
        if ntime == 0, buzzer beeps continuously
        """
        self._cmd(address, 'BUZ', int(buzzer), ntime)

    def start_program(self, address: int):
        self._cmd(address, 'RUN')

    def stop_program(self, address: int):
        self._cmd(address, 'STP')

    def get_volume_dispensed(self, address: int) -> dict[str, Any]:
        r = self._cmd(address, 'DIS')
        assert r['data'][0] == 'I' and 'W' in r['data'], "infusion/withdrawn keyword not found"
        unit = r['data'][-2:]
        assert len(unit) == 2 and unit[-1] == 'L', f"unknown volume unit: {unit}"
        u = self._from_dict_key(self.VOLUME_UNITS, unit[0])
        s = r['data'][1:-2].split('W')
        assert len(s) == 2
        return dict(
            infusion=float(s[0]),
            withdraw=float(s[1]),
            unit=u
        )

    def clear_dispensed_volume(self, address: int, direction: str):
        d = self._from_dict_value(self.PUMP_DIRECTION, direction)
        self._cmd(address, 'CLD', d)

    def get_firmware_version(self, address: int) -> str:
        r = self._cmd(address, 'VER')
        return r['data']

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

    def _cmd(self, addr: int, cmd: str, *args):
        assert 0 <= addr <= 99, "address out of range"
        args = [str(a) if not isinstance(a, str) else a for a in args]
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
            res['alarm'] = self._from_dict_key(self.ALARM, alarm_type)
            data = response[5:]
        else:
            raise ValueError(f"unknown status: {status}")
        if data:
            if data[0] == '?':
                error = data[1:]
                msg = self._from_dict_key(self.ERROR, error)
                raise ValueError(f"command error: {msg}")
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

    @staticmethod
    def _from_dict_key(d: dict, k: str) -> str:
        assert k in d.keys(), f"unknown key {k}"
        v = d[k]
        if isinstance(v, list):
            v = v[0]
        return v

    @staticmethod
    def _from_dict_value(d: dict, v: str) -> str:
        assert v in d.values(), f"unknown value {v}"
        k = [k for k, _v in d.items() if isinstance(_v, list) and v in _v or _v == v]
        assert len(k) == 1
        return k[0]


if __name__ == '__main__':
    ports = serial.tools.list_ports.comports()
    p = SyrPump('COM7')
    #p.set_buzzer(0, True)
    r = p.get_pump_rate(0)
    print(r)
