class SyrPumpException(Exception):
    pass


class CommandNotRecognized(SyrPumpException):
    def __init__(self):
        super().__init__("command is not recognized (‘?’ only)")


class CommandNotAvailable(SyrPumpException):
    def __init__(self):
        super().__init__("command is not currently applicable")


class DataOutOfRange(SyrPumpException):
    def __init__(self):
        super().__init__("command data is out of range")


class InvalidComPacket(SyrPumpException):
    def __init__(self):
        super().__init__("invalid communications packet received")


class CommandIgnored(SyrPumpException):
    def __init__(self):
        super().__init__("command ignored due to a simultaneous new phase start")
