from syrpp import SyrPump

p = SyrPump('COM7')
addr = 0
if p.get_status(addr, code=True) != 'S':
    p.stop_program(addr)
p.set_config('./prog/man_ex4.json')
p.get_config(save_to='./prog/from_pump.json')