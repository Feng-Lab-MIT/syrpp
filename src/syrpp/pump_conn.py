import serial
import serial.tools.list_ports

from typing import Any, Optional, Dict, Union, List
import warnings
from pathlib import Path
import json

from src.syrpp.exception import *


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
        '': CommandNotRecognized,
        'NA': CommandNotAvailable,
        'OOR': DataOutOfRange,
        'COM': InvalidComPacket,
        'IGN': CommandIgnored
    }

    PUMP_DIRECTION = {
        'INF': 'infuse',
        'WDR': 'withdraw',
        'REV': 'reverse'
    }

    TRIGGER_SETUP = {
        # falling edge starts or stops the pumping program
        'FT': ['foot switch', 'foot'],
        # falling edge stops the pumping program
        # rising edge starts the pumping program
        'LE': ['level control', 'level'],
        # falling edge starts the pumping program
        'ST': ['start only', 'start']
    }

    RATE_FUNCTION = ['RAT', 'INC', 'DEC']

    PHASE_FUNCTION = {
        # rate data functions
        'RAT': 'rate',
        'INC': 'increment',
        'DEC': 'decrement',
        # non-rate data functions
        'STP': 'stop',
        'JMP': 'jump',          # jump to program phase n
        'LOP': 'loop for',      # loop to previous loop start n times
        'LPS': 'loop start',    # loop start phase
        'LPE': 'loop end',      # loop end phase
        'PAS': 'pause',         # pause pumping for n seconds
        'IF': 'if',             # if program input TTL pin low, jump to phase n
        'EVN': 'event trap',    # set event trigger trap to phase n
        'EVR': 'event reset',   # event trigger reset
        'BEP': 'beep',
        'OUT': 'output'         # set programmable output pin (5) 0/1
    }

    PHASE_FUN_DATA = {
        'JMP': 'phase',
        'LOP': 'count',
        'PAS': 'number',
        'IF': 'phase',
        'EVN': 'phase',
        'OUT': 'ttl'
    }

    VOLUME_UNITS = {
        'U': ['\u03bcl', 'ul', 'microliter'],
        'M': ['ml', 'mL', 'milliliter', 'cc']
    }

    TIME_UNITS = {
        'M': ['min', 'mn', 'minute'],
        'H': ['h', 'hr', 'hour']
    }

    DATA_RANGE = {
        'address': (0, 99),
        'phase': (1, 41),
        'number': (0, 99),
        'count': (1, 99),
        'ttl': (0, 1),
        'timeout': (0, 255)
    }

    def __init__(
            self,
            port,
            baudrate=19200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=.05
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

    def get_avail_address(self) -> list[int]:
        if self.serial.timeout is None:
            self.set_timeout()
        rng = self.DATA_RANGE['address']
        address = list()
        for a in range(rng[0], rng[1] + 1):
            try:
                self._cmd(a)
            except TimeoutError:
                continue
            address.append(a)
        return address

    def set_config(self, config):
        if isinstance(config, str):
            config = Path(config)
        if isinstance(config, Path):
            assert config.suffix == '.json', f"{config.suffix} is not supported"
            with open(config, 'r') as f:
                config = json.load(f)
        assert isinstance(config, list), \
            f"config's top level must be a list, not {type(config)}"
        for item in config:
            addr = item['address']
            if isinstance(addr, int):
                addr = [addr]
            elif isinstance(addr, str) and addr == 'all':
                addr = self.get_avail_address()
            elif isinstance(addr, list):
                pass
            else:
                raise ValueError(f'invalid address: {addr}')
            for a in addr:
                for k, v in item.items():
                    if k == 'address':
                        continue
                    # other configs
                    # TODO: use getattr here
                    elif k == 'diameter':
                        self.set_diameter(address=a, diameter=v)
                    elif k == 'clear':
                        if isinstance(v, str):
                            v = [v]
                        for d in v:
                            self.clear_dispensed_volume(address=a, direction=d)
                    elif k == 'com_mode':
                        self.set_com_mode(address=a, mode=v)
                    elif k == 'alarm':
                        self.set_alarm(address=a, buzzer=v)
                    elif k == 'power_fail':
                        self.set_power_fail(address=a, power_fail=v)
                    elif k == 'trigger':
                        self.set_trigger(address=a, trigger=v)
                    elif k == 'key_beep':
                        self.set_key_beep(address=a, key_beep=v)
                    elif k == 'ttl_output':
                        for pin, level in v.items():
                            self.set_ttl_output(address=a, pin=int(pin), level=level)
                    elif k == 'buzzer':
                        self.set_buzzer(address=a, buzzer=v)
                    # program
                    elif k == 'program':
                        prog = item['program']
                        for i, func in enumerate(prog):
                            phase = i + 1
                            self.set_phase(address=a, phase=phase)
                            kwargs = dict()
                            f = func['function']
                            f_code = self._from_dict_value(self.PHASE_FUNCTION, f)
                            if f_code not in self.RATE_FUNCTION:
                                data = {k: v for k, v in func.items() if k != 'function'}
                                if len(data) >= 1:
                                    assert len(data) == 1, "only one data is allowed"
                                    kwargs['data'] = list(data.values())[0]
                            self.set_function(address=a, function=f, **kwargs)
                            if f_code in self.RATE_FUNCTION:
                                if 'rate' in func:
                                    self.set_rate(address=a, **func['rate'])
                                if 'volume' in func:
                                    self.set_volume(address=a, **func['volume'])
                                if 'direction' in func:
                                    self.set_direction(address=a, direction=func['direction'])
                    else:
                        raise ValueError(f'invalid attribute: {k}')

    def get_diameter(self, address: int) -> float:
        r = self._cmd(address, 'DIA')
        return float(r['data'])

    def set_diameter(self, address: int, diameter: float):
        self._cmd(address, 'DIA', self._float(diameter))

    def get_volume(self, address: int) -> float:
        r = self._cmd(address, 'VOL')
        vol = r['data'][:-2]
        unit = r['data'][-2:]
        assert unit[-1] == 'L', f"invalid volume unit {unit}"
        return dict(
            volume=float(vol),
            unit=self._from_dict_key(self.VOLUME_UNITS, unit[0]),
        )

    def set_volume(self, address: int, value: Optional[float] = None, unit: Optional[str] = None):
        assert not (value is None and unit is None), "must specify either volume or volume unit"
        if value is not None:
            self._cmd(address, 'VOL', self._float(value))
        if unit is not None:
            self._cmd(address, 'VOL', self._from_dict_value(self.VOLUME_UNITS, unit) + 'L')

    def get_phase(self, address: int) -> int:
        r = self._cmd(address, 'PHN')
        return int(r['data'])

    def set_phase(self, address: int, phase: int):
        self._check_range(phase, 'phase')
        self._cmd(address, 'PHN', phase)

    def get_function(self, address: int) -> Dict[str, Any]:
        """
        return True if buzzer is on continuously or beeping
        """
        r = self._cmd(address, 'FUN')
        ret = dict()
        d = r['data'][-2:]
        if d.isdigit():
            f = r['data'][:-2]
            assert f in self.PHASE_FUN_DATA.keys(), f"function {f} should not have data"
            ret['data'] = int(d)
        else:
            f = r['data']
        assert f in self.PHASE_FUNCTION, f"unknown function {f}"
        ret['function'] = self._from_dict_key(self.PHASE_FUNCTION, f)
        return ret

    def set_function(self, address: int, function: str, data: Optional[Union[int, str, float]] = None):
        f = self._from_dict_value(self.PHASE_FUNCTION, function)
        args = list()
        args.append(f)
        if data is not None:
            assert f in self.PHASE_FUN_DATA.keys(), f"function {f} should not have data"
            if f == 'PAS':
                # pause and wait for trigger
                if data == 'trigger':
                    data = 0
                elif isinstance(data, (float, int)):
                    data = self._float(data, 2, 1)
            args.append(data)
        self._cmd(address, 'FUN', *args)

    def get_rate(self, address: int) -> Dict[str, Any]:
        r = self._cmd(address, 'RAT')
        return dict(
            value=float(r['data'][:-2]),
            volume_unit=self._from_dict_key(self.VOLUME_UNITS, r['data'][-2]),
            time_unit=self._from_dict_key(self.TIME_UNITS, r['data'][-1])
        )

    def set_rate(self, address: int, value: float,
                 volume_unit: Optional[str] = None, time_unit: Optional[str] = None):
        args = list()
        args.append(self._float(value))
        assert (volume_unit is None) == (time_unit is None), \
            "must specify both or neither volume and time unit"
        if volume_unit is not None and time_unit is not None:
            args.append(self._from_dict_value(self.VOLUME_UNITS, volume_unit))
            args.append(self._from_dict_value(self.TIME_UNITS, time_unit))
        self._cmd(address, 'RAT', *args)

    def get_direction(self, address: int) -> str:
        r = self._cmd(address, 'DIR')
        return self._from_dict_key(self.PUMP_DIRECTION, r['data'])

    def set_direction(self, address: int, direction: str):
        d = self._from_dict_value(self.PUMP_DIRECTION, direction)
        self._cmd(address, 'DIR', d)

    def get_com_mode(self, address: int) -> Dict[str, Any]:
        r = self._cmd(address, 'SAF')
        timeout = int(r['data'])
        if timeout == 0:
            return dict(mode='basic')
        else:
            return dict(mode='safe', timeout=timeout)

    def set_com_mode(self, address: int, mode: str, timeout: int = None):
        args = list()
        if mode == 'basic':
            assert timeout is None, f"no timeout for basic communication mode"
            args.append(0)
        elif mode == 'safe':
            assert timeout is not None, f"timeout should be provided for safe communication mode"
            args.append(timeout)
        self._cmd(address, 'SAF', *args)

    def get_alarm(self, address: int) -> bool:
        """
        return True if alarm buzzer mode is enabled
        when alarms are enabled, the buzzer will be sounded as follows:
        condition                                   | buzzer action
        ----------------------------------------------------------------
        pumping program ended                       | continuous beeping
        pumping program paused for start trigger    | continuous beeping
        alarm condition, such as pump motor stalled | steady alarm
        """
        r = self._cmd(address, 'AL')
        return bool(int(r['data']))

    def set_alarm(self, address: int, buzzer: bool):
        self._cmd(address, 'AL', int(buzzer))

    def get_power_fail(self, address: int) -> bool:
        r = self._cmd(address, 'PF')
        return bool(int(r['data']))

    def set_power_fail(self, address: int, power_fail: bool):
        self._cmd(address, 'PF', int(power_fail))

    def get_trigger(self, address: int) -> str:
        """
        return True if buzzer is on continuously or beeping
        """
        r = self._cmd(address, 'TRG')
        return self._from_dict_key(self.TRIGGER_SETUP, r['data'])

    def set_trigger(self, address: int, trigger: str):
        self._cmd(address, 'TRG', self._from_dict_value(self.TRIGGER_SETUP, trigger))

    def get_key_beep(self, address: int) -> bool:
        r = self._cmd(address, 'BP')
        return bool(int(r['data']))

    def set_key_beep(self, address: int, key_beep: bool):
        self._cmd(address, 'BP', int(key_beep))

    def set_ttl_output(self, address: int, level: int, pin: int = 5):
        """
        sets TTL level on user definable output pin on the TTL I/O connector
        """
        assert pin == 5, f"only pin 5 is supported"
        self._check_range(level, 'ttl')
        self._cmd(address, 'OUT', pin, level)

    def get_ttl_input(self, address: int, level: int, pin: int):
        """
        queries TTL level of pin on TTL I/O connector
        """
        assert pin in [2, 3, 4, 6], f"pin {pin} not supported"
        r = self._cmd(address, 'IN', pin)
        return r['data']

    def get_buzzer(self, address: int) -> bool:
        """
        return True if buzzer is on continuously or beeping
        """
        r = self._cmd(address, 'BUZ')
        return bool(int(r['data']))

    def set_buzzer(self, address: int, buzzer: bool, n_time: int = 0):
        """
        if n_time == 0, buzzer beeps continuously
        """
        # TODO: check why buzzer cannot be set true
        args = list()
        if buzzer:
            args.append(n_time)
        self._cmd(address, 'BUZ', int(buzzer), *args)

    def start_program(self, address: int):
        self._cmd(address, 'RUN')

    def stop_program(self, address: int):
        self._cmd(address, 'STP')

    def get_volume_dispensed(self, address: int) -> Dict[str, Any]:
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

    def get_status(self, address: int, code: bool = False) -> str:
        r = self._cmd(address)
        ret = r['prompt']
        if not code:
            ret = self.PROMPT[ret]
        return ret

    def set_timeout(
            self,
            address: Optional[Union[int, list[int]]] = None,
            n_times: int = 10,
            multiple: int = 4
    ):
        if address is None:
            address = 0
        if isinstance(address, int):
            address = [address]
        from time import time_ns
        start = time_ns()
        for a in address:
            for _ in range(n_times):
                self._cmd(a)
        t = time_ns() - start
        t_sec = t * 1e-9 / (n_times * len(address))
        self.serial.timeout = multiple * t_sec
        return self.serial.timeout

    def _raw_cmd(self, cmd: str):
        send = cmd + '\r\n'
        send = send.encode('utf-8')
        num = self.serial.write(send)
        assert num == len(send), \
            f"only {num} of {len(send)} bytes sent to syringe pump via serial"
        receive = self.serial.read_until(b'\x03')
        if self.serial.timeout is not None and receive == b"":
            raise TimeoutError
        assert receive[0] == 2 and receive[-1] == 3, \
            f"received bytes structure invalid"
        receive = receive[1:-1].decode('utf-8')
        return receive

    def _cmd(self, addr: int, cmd: str = '', *args):
        """
        return the code only because this is a private method
        """
        self._check_range(addr, 'address')
        args = [str(a) if not isinstance(a, str) else a for a in args]
        fields = [str(addr), cmd, *args]
        try:
            response = self._raw_cmd(''.join(fields))
        except TimeoutError:
            raise TimeoutError(f"no response from address {addr}")
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
            msg = self._from_dict_key(self.ALARM, alarm_type)
            warnings.warn(msg)
            res['alarm'] = alarm_type
            data = response[5:]
        else:
            raise ValueError(f"unknown status: {status}")
        if data:
            if data[0] == '?':
                error = data[1:]
                e = self._from_dict_key(self.ERROR, error)
                raise e
            else:
                res['data'] = data
        return res

    @staticmethod
    def _float(f: float, max_digits: int = 4, max_decimal: int = 3) -> str:
        """
        returns the truncated float number that the pump accepts
        :param f: the orignal float number
        :param max_digits: maximum of total digits (1 decimal point not included)
        :param max_decimal: maximum of digits to the right of the decimal point
        :return: the truncated float number
        """
        assert 0 <= f <= int('9' * max_digits), f"float {f} out of range"
        _f = f
        f = str(round(f, max_decimal))
        if '.' in f:
            if len(f) >= max_digits + 1:
                f = f[-(max_digits + 1):]
        else:
            if len(f) >= max_digits:
                f = f[-max_digits:]
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
        k = [k for k, _v in d.items() if isinstance(_v, list) and v in _v or _v == v]
        assert len(k) == 1, f"unknown value {v}"
        return k[0]

    @staticmethod
    def _check_range(v: int, type: str):
        assert type in SyrPump.DATA_RANGE.keys(), f"unknown data type {type}"
        r = SyrPump.DATA_RANGE[type]
        assert r[0] <= v <= r[1], f"{v} out of range for {type} data"
