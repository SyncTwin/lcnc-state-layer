#!/bin/bash
# after LinuxCNC is up: timedelta first in servo-thread, sampler last
halcmd loadrt timedelta count=1
halcmd addf timedelta.0 servo-thread 1
halcmd loadrt sampler depth=8192 cfg=ss
halcmd addf sampler.0 servo-thread
halcmd net bench-period timedelta.0.out sampler.0.pin.0
halcmd net bench-time servo-thread.time sampler.0.pin.1
halcmd show pin timedelta.0 | head -12
