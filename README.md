# apoclypsebm - The ApoCLypse Bitcoin Miner
## Background
This hobby project undertakes the quixotic task of maintaining a modern Bitcoin miner for programmable compute
devices like GPUs. It was forked from the PyOpenCL Bitcoin Miner (poclbm), a project authored by 
[m0mchil](https://github.com/m0mchil/) and contributors.

It features an OpenCL Kernel that has incorporated ideas or code from:
* [diapolo](https://github.com/diapolo/)
* [m0mchil](https://github.com/m0mchil/)
* [neurobox](https://bitcointalk.org/index.php?action=profile;u=106397)
* [phataeus](https://sourceforge.net/u/phateus/)
* [rethaw](https://bitcointalk.org/index.php?action=profile;u=18618)

If your work is represented herein and I didn't give you credit, please let me know. At the moment, I reserve no rights
to the mining driver or the OpenCL kernel. They were derived from public domain works.

## Economy
At the time of this writing, on-chip implementations of the Bitcoin mining solution algorithm will outperform this
software in time and joules expended. Under most economic conditions, mining blocks on a Bitcoin chain where
on-chip implementations are competing would be at tremendous waste of expended resources.

## Installation
    pip3 install git+git://github.com/JustinTArthur/apoclypsebm.git[OpenCL]

## Usage
    apoclypse [OPTION]... SERVER[#tag]...

`SERVER` is one or more [http[s]|stratum://]user:pass@host:port          (required)
[#tag] is an optional per server user friendly name displayed in stats (optional)

### Options
```
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  --verbose             verbose output, suitable for redirection to log file
  -q, --quiet           suppress all output except hash rate display
  --proxy=PROXY         specify as
                        [[socks4|socks5|http://]user:pass@]host:port (default
                        proto is socks5)

  Miner Options:
    -r RATE, --rate=RATE
                        hash rate display interval in seconds, default=1 (60
                        with --verbose)
    -e ESTIMATE, --estimate=ESTIMATE
                        estimated rate time window in seconds, default 900 (15
                        minutes)
    -a ASKRATE, --askrate=ASKRATE
                        how many seconds between getwork requests, default 5,
                        max 10
    -t TOLERANCE, --tolerance=TOLERANCE
                        use fallback pool only after N consecutive connection
                        errors, default 2
    -b FAILBACK, --failback=FAILBACK
                        attempt to fail back to the primary pool after N
                        seconds, default 60
    --cutoff_temp=CUTOFF_TEMP
                        (requires github.com/mjmvisser/adl3) temperature at
                        which to skip kernel execution, in C, default=95
    --cutoff_interval=CUTOFF_INTERVAL
                        (requires adl3) how long to not execute calculations
                        if CUTOFF_TEMP is reached, in seconds, default=0.01
    --no-server-failbacks
                        disable using failback hosts provided by server

  Kernel Options:
    -p PLATFORM, --platform=PLATFORM
                        use OpenCL platform by id
    -d DEVICE, --device=DEVICE
                        use device by id, by default asks for device
    -w WORKSIZE, --worksize=WORKSIZE
                        work group size, default is maximum returned by opencl
    -f FRAMES, --frames=FRAMES
                        will try to bring single kernel execution to 1/frames
                        seconds, default=30, increase this for less desktop
                        lag
    -s FRAMESLEEP, --sleep=FRAMESLEEP
                        sleep per frame in seconds, default 0
    -v, --vectors       use 2-attempts-wide vectors on all devices
```