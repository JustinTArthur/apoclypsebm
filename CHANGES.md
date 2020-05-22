## New in Version 1.1.4
* Added `-k`/`--kernel` option for specifying which of available kernels to
use. Only `apoclypse-0` and `apoclypse-loopy` are available at the moment.
* New "apoclypse-loopy" kernel is an alternative implementation of the
poclbm/phoenix/phatk kernel that uses for-loops. On some older platforms, this
provides better performance. On modern AMD and nVidia software+hardware
stacks, the basic apoclypse-0 kernel is fine.
* The `-w`/`--worksize` option now uses kernel code to configure the work
group size when the OpenCL stack tries to enforce a smaller maximum size. This
allows for up to 1024-sized work groups on recent AMD and nVidia
drivers+devices.
* Fix for discrete cards doing wasted work because output buffer wasn't being
copied back to host correctly.
* Fix for when stratum servers supply a floating point difficulty number
[#7](JustinTArthur/apoclypsebm#7). In this case, we floor the result of any
arithmetic performed against it.
* Use monotonic timers for rate calculations so that system time changes
don't impact them.
* Upgrade to latest PyOpenCL now that pybind11 is fixing the header
situation.

## New in Version 1.1.3
Bug fix release. Installation from PyPI (e.g. with pip) had some
glaring issues. Additionally, PyOpenCL removed deprecated APIs we were using.
I've pinned us to PyOpenCL releases prior to their pybind11 integration so that
this project remains installable from pip (see
[inducer/pyopencl#278](https://github.com/inducer/pyopencl/issues/278)).

## New in Version 1.1.0
This release focused on supporting the `getblocktemplate` call proposed in
BIP 22 and BIP 23 and implemented by Bitcoin Core and btcd. This finally allows
mining without a pool if you supply an address to mine coins to at the command
line.

HTTP work sources now default to using `getblocktemplate` instead of `getwork`.
This feature is new and might have bugs that could lead to loss of potential
mining rewards.
