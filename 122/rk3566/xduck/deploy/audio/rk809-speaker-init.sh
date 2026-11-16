#!/bin/sh
# K11C RK809 speaker route. Run after alsa-restore and before robotd startup audio.
# Re-entering SPK restores the device-tree board gain; do not write DAC volume via
# the vendor mixer. User volume belongs to the independent Xduck softvol control.
set -eu
card=rockchiprk809
attempt=0
until amixer -c "$card" sget 'Playback Path' >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    [ "$attempt" -lt 10 ] || exit 1
    sleep 0.2
done
amixer -c "$card" sset 'Playback Path' OFF >/dev/null
amixer -c "$card" sset 'Playback Path' SPK >/dev/null
amixer -c "$card" sset Speaker on >/dev/null
amixer -c "$card" sset 'spk switch' on >/dev/null
amixer -c "$card" sget 'Playback Path'
amixer -c "$card" sget 'spk switch'
amixer -c "$card" sget DAC
