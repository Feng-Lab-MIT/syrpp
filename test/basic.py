from syrpp import SyrPump

if __name__ == '__main__':
    p = SyrPump('COM7')
    r = p.get_firmware_version(0)
    print(r)
