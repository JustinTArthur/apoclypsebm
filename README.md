# apoclypsebm - The ApoCLypse Bitcoin Miner
## Background
This hobby project maintained by
[Justin T. Arthur](https://github.com/JustinTArthur) undertakes the quixotic
task of maintaining a modern Bitcoin miner for programmable compute devices like
GPUs. It was forked from the PyOpenCL Bitcoin Miner (poclbm), a project authored
by [m0mchil](https://github.com/m0mchil) and contributors.

It features an OpenCL Kernel that has incorporated ideas or code from:
* [diapolo](https://github.com/diapolo)
* [m0mchil](https://github.com/m0mchil)
* [neurobox](https://bitcointalk.org/index.php?action=profile;u=106397)
* [phataeus](https://sourceforge.net/u/phateus/)
* [rethaw](https://bitcointalk.org/index.php?action=profile;u=18618)

If your work is represented herein and I didn't give you credit, please let me
know. At the moment, I reserve no rights to the mining driver or the OpenCL
kernel. They were derived from public domain works.

## Economy
At the time of writing, on-chip implementations of the Bitcoin mining algorithm
will outperform this software in both time and joules expended. Under most
conditions, mining blocks on a Bitcoin chain where on-chip implementations are
competing would be at a tremendous waste of expended resources.

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

It looks like the work sourcing threads run into i/o issues occasionally due to
using the not-thread-safe Python http lib. I don't aim to address this as most
of the threaded communication ought to be completely replaced by an event runner
like asyncio or trio at some point.

Thanks to @momchil for the original `getwork` code, @luke-jr @sipa and @vsergeev
for helping me understand getblocktemplate. 

## Installation
In an environment with Python 3.5+:

    pip3 install apoclypsebm

## Usage
    apoclypse [OPTION]... SERVER[#tag]...

`SERVER` is one or more [http[s]|stratum://]user:pass@host:port (required)  
[#tag] is an optional per server user-friendly name displayed in stats.

### Options
```
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  --verbose             verbose output, suitable for redirection to log file
  -q, --quiet           suppress all output except hash rate display
  --proxy=PROXY         specify as
                        [[socks4|socks5|http://]user:pass@]host:port (default
                        proto is socks5)
  --no-ocl              don't use OpenCL
  --no-bfl              don't use Butterfly Labs
  --stratum-proxies     search for and use stratum proxies in subnet
  -d DEVICE, --device=DEVICE
                        comma separated device IDs, by default will use all
                        (for OpenCL - only GPU devices)
  -a ADDRESS, --address=ADDRESS
                        Bitcoin address to spend the block reward to if
                        allowed. Required for solo mining, ignored with
                        stratum or getwork sources.
  --coinbase-msg=COINBASE_MSG
                        Custom text to include in the coinbase of the
                        generation tx if allowed, encoded as UTF-8.
                        default=ApoCLypse


  Miner Options:
    -r RATE, --rate=RATE
                        hash rate display interval in seconds, default=1 (60
                        with --verbose)
    -e ESTIMATE, --estimate=ESTIMATE
                        estimated rate time window in seconds, default 900 (15
                        minutes)
    -t TOLERANCE, --tolerance=TOLERANCE
                        use fallback pool only after N consecutive connection
                        errors, default 2
    -b FAILBACK, --failback=FAILBACK
                        attempt to fail back to the primary pool after N
                        seconds, default 60
    --cutoff-temp=CUTOFF_TEMP
                        AMD GPUs, BFL only. For GPUs requires
                        github.com/mjmvisser/adl3. Comma separated
                        temperatures at which to skip kernel execution, in C,
                        default=95
    --cutoff-interval=CUTOFF_INTERVAL
                        how long to not execute calculations if CUTOFF_TEMP is
                        reached, in seconds, default=0.01
    --no-server-failbacks
                        disable using failback hosts provided by server

  OpenCL Options:
    Every option except '-p' and '-v' can be specified as a
    comma separated list. If there aren't enough entries specified, the
    last available is used. Use --vv to specify per-device vectors usage.

    -p PLATFORM, --platform=PLATFORM
                        use platform by id
    -w WORKSIZE, --worksize=WORKSIZE
                        work group size, default is maximum returned by OpenCL
    -f FRAMES, --frames=FRAMES
                        will try to bring single kernel execution to 1/frames
                        seconds, default=30, increase this for less desktop
                        lag
    -s FRAMESLEEP, --sleep=FRAMESLEEP
                        sleep per frame in seconds, default 0
    --vv=VECTORS        Specifies size of SIMD vectors per selected device.
                        Only size 0 (no vectors) and 2 supported for now.
                        Comma separated for each device. e.g. 0,2,2
    -v, --vectors       Use 2-item vectors for all devices.
```