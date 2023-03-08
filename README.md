Implementation of convenience functions for https://github.com/xrootd/xrootd-python.

#########
# Setup #
#########
The source script is written for a CentOs7 machine with cvmfs available.
LCG_102 is checked out and provides all necessary software.
Eventually, the questionary module has to be installed separately (with pip).

#########
# Usage #
#########
Interactive:
  `$ XRD_LOGLEVEL='' python3 xrootd_interactive.py --user <username> [--basepath | --redirector | --loglevel]`
Note: The user name is only used as a small safeguard. It should be your directory name on the storage server.

CLI mode:
First, the according lines need to be commented in in "xrootd_utils.py".
Some examples are given at the end of xrootd_utils.py.
Then:
  `$ python3 xrootd_utils.py --user <user> [--loglevel | --redirector]`

###################
# General remarks #
###################
  - **WARNING**: The behaviour of some of the bindings unfortunately depend on the type of the redirector!
  - For GridKa, I only recommend using the dcache door (root://cmsxrootd-kit.gridka.de:1094/)
  - Be **careful** with deleting stuff. There is no "real" access management!
  - I dont take any responsibility.

#########
# Files #
#########
source_xrd.sh         : source script for CentOS7
xrootd_interactive.py : Interactive "questionary" for easy use
xrootd_utils.py       : All relevant functions that also can be used standalone

