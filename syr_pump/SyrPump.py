import serial
import serial.tools.list_ports


class SyrPump:
    PROMPT = dict(
        I="infusing",
        W="withdrawing",
        S="pumping program stopped",
        P="pumping program paused",
        T="pause phase",
        U="operational trigger wait (user wait)"
    )

    ALARM = dict(
        R="pump was reset (power was interrupted)",
        S="pump motor stalled",
        T="safe mode communications time out",
        E="pumping program error",
        O="pumping program phase is out of range"
    )

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

    def _cmd(self, addr: int, cmd: str):
        assert 0 <= addr <= 99, "address out of range"
        response = self._raw_cmd(str(addr) + cmd)
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
            res['data'] = data
        return res


if __name__ == '__main__':
    ports = serial.tools.list_ports.comports()
    p = SyrPump('COM7')
    r = p._cmd(0, 'DIA')
    print(r)
