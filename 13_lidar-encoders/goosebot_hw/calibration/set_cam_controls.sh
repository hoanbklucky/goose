#!/usr/bin/env bash
# Lock the "auto" features on both stereo webcams so left and right behave identically.
# usage: ./set_cam_controls.sh [exposure=100] [gain=<unset>] [wb_kelvin=4600]
#   exposure is in V4L2 units of 100 us (100 = 10 ms). Shorter = less motion blur, darker image.
# Only touches controls the camera actually lists, and prints what it set.
# Run it while bringup is streaming (UVC controls can be set live), or before; then verify (see end).
EXP=${1:-100}; GAIN=${2:-}; WB=${3:-4600}
DEVS=${DEVS:-"/dev/cam_left /dev/cam_right"}

for dev in $DEVS; do
  [ -e "$dev" ] || { echo "$dev: not found"; continue; }
  names=$(v4l2-ctl -d "$dev" --list-ctrls 2>/dev/null | awk '{print $1}')
  has() { grep -qx "$1" <<<"$names"; }
  # set_first VALUE NAME1 [NAME2 ...] : set the first of these control names the camera has
  set_first() {
    local val=$1; shift
    for n in "$@"; do
      if has "$n"; then
        if v4l2-ctl -d "$dev" -c "$n=$val" 2>/dev/null; then echo "$dev: $n=$val"; else echo "$dev: FAILED $n=$val"; fi
        return
      fi
    done
  }
  echo "== $dev =="
  set_first 1      auto_exposure exposure_auto                     # 1 = manual mode
  set_first 0      exposure_dynamic_framerate                       # stop fps dropping in dim light
  set_first 0      white_balance_automatic white_balance_temperature_auto
  set_first 0      focus_automatic_continuous focus_auto            # only present if the cam has autofocus
  set_first "$EXP" exposure_time_absolute exposure_absolute
  [ -n "$GAIN" ] && set_first "$GAIN" gain
  set_first "$WB"  white_balance_temperature
  set_first 0      backlight_compensation
  set_first 2      power_line_frequency                              # 2 = 60 Hz mains (use 1 for 50 Hz)
  echo "-- current values --"
  v4l2-ctl -d "$dev" --list-ctrls 2>/dev/null | grep -E "exposure|white_balance|focus|gain|backlight|power_line" | sed 's/^ */  /'
done
