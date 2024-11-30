from syrpp import SyrPump
from time import time

p = SyrPump('COM7')
t = p.set_timeout()
print('timeout:', t)
start = time()
address = p.get_avail_address()
t = time() - start
print('address:', address)
print('time:', t)
