from syrpp import SyrPump

p = SyrPump('COM7')
addr = 0
p.set_trigger(addr, trigger='foot switch')
print(p.get_trigger(addr, ret_type='name'))
p.set_trigger(addr, start='rising', stop='falling')
print(p.get_trigger(addr, ret_type='start stop'))
print(p.get_trigger(addr, ret_type='start stop code'))
