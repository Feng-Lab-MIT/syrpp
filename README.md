# syrpp

The purpose of syrpp is to provide an open-sourced solution to control syringe pumps via RS232 serial communication. More high-level features will be supported in the future.

## Installation

```bash
git clone https://github.com/Feng-Lab-MIT/syrpp.git
cd syrpp
pip install -e .
```

## Compatibility

Code is tested on New Era SyringeONE NE-1000 (distributed by Braintree as BS-9000), which make it support only pumps that use the same set of commands. Information about their command definition can be found on [their manual](https://www.newerainstruments.com/user-manuals/pdfs/SYRINGEONE_MANUAL.pdf). 

