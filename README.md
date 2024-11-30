# syrpp

The purpose of syrpp is to provide an open-sourced solution to control syringe pumps via RS232 serial communication. It supports all basic features provided in SyringePumpProV1. More high-level features will be supported in the future.

## Installation

```bash
git clone https://github.com/Feng-Lab-MIT/syrpp.git
cd syrpp
pip install -e .
```

## Quick Start

### Basic Features

To connect to a pump network, just instatiate an object of class `SyrPump`:

```python
p = SyrPump('COM7')
```

Then we can get/set any parameters of the pumps:

```python
p.get_firmware_version(0)
```

which returns

```
NE1000V3.934
```

### Bulk Setup

`syrpp` allows users to setup pumps with a `.json` configuration file. It's demonstrated in [this example script](./test/config.py).

```python
p.set_config('./prog/man_ex4.json')
```

The given `.json` file contains the pump program provided as example 4 in [manufacture's manual](https://www.newerainstruments.com/user-manuals/pdfs/SYRINGEONE_MANUAL.pdf).

## Compatibility

Code is tested on New Era SyringeONE NE-1000 (distributed by Braintree as BS-9000), which makes it support only pumps that use the same set of commands. Information about their command definition can be found on [their manual](https://www.newerainstruments.com/user-manuals/pdfs/SYRINGEONE_MANUAL.pdf). 

