# apoclypsebm - The ApoCLypse Bitcoin Miner
## Background
This hobby project maintained by [Justin T. Arthur](https://github.com/JustinTArthur) undertakes the quixotic task of maintaining a modern Bitcoin miner for programmable compute
devices like GPUs. It was forked from the PyOpenCL Bitcoin Miner (poclbm), a project authored by 
[m0mchil](https://github.com/m0mchil) and contributors.

It features an OpenCL Kernel that has incorporated ideas or code from:
* [diapolo](https://github.com/diapolo)
* [m0mchil](https://github.com/m0mchil)
* [neurobox](https://bitcointalk.org/index.php?action=profile;u=106397)
* [phataeus](https://sourceforge.net/u/phateus/)
* [rethaw](https://bitcointalk.org/index.php?action=profile;u=18618)

If your work is represented herein and I didn't give you credit, please let me know. At the moment, I reserve no rights
to the mining driver or the OpenCL kernel. They were derived from public domain works.

## New in Version 1.0.0
* First release following the fork from [m0mchil/poclbm](https://github.com/m0mchil/poclbm). ([diff](https://github.com/m0mchil/poclbm/compare/master...JustinTArthur:v1.0.0))
* Migrated code to Python 3. Requires Python 3.5+
* Fix kernel compilation error in clang-based OpenCL compilers like macOS OpenCL and
AMD ROCm.
* Fix for not submitting shares to stratum servers reporting pdifficulty when server-side pdifficulty is below 1. By [luke-jr](https://github.com/luke-jr).
* Minor performance improvements

## Economy
At the time of writing, on-chip implementations of the Bitcoin mining algorithm will outperform this
software in both time and joules expended. Under most conditions, mining blocks on a Bitcoin chain where
on-chip implementations are competing would be at a tremendous waste of expended resources.

## Installation
Python 3.5+ must be installed first. To install latest from master branch on GitHub:

    pip3 install git+git://github.com/JustinTArthur/apoclypsebm.git

## Usage
    apoclypse [OPTION]... SERVER[#tag]...

`SERVER` is one or more [http[s]|stratum://]user:pass@host:port          (required)  
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