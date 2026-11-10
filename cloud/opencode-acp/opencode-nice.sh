#!/bin/sh
exec /usr/bin/nice -n 10 /home/qatro/.local/bin/opencode-2.2.5 "$@"
