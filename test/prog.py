from syrpp import SyrPump
import json

p = SyrPump('COM7')
with open('./prog/man_ex4.json', 'r') as f:
    prog = json.load(f)
p.set_program(prog)