"""
Zendure P1 Fast Controller (pyscript)
------------------------------------
Requirements:
- Home Assistant integration "pyscript" installed
- Entities from Zendure MQTT setup are available:
  - P1 Entity (default sensor.power_actual, optional via input_text.zendure_power_meter_total_consumption)
  - sensor.solarflow_1_battery_level
  - sensor.solarflow_2_battery_level
- Scripts from zendure_v130.yaml:
  - script.zendure_dispatch_u1_output
  - script.zendure_dispatch_u2_output

What it does:
- Event-driven control based on P1 state changes
- Fast/Normal timing windows (TIMEFAST/TIMEZERO)
- Stddev based jump detection
- Command-first fallback when output telemetry lags
"""

from collections import deque
from math import sqrt
from time import time

TIMEFAST = 2.2
TIMEZERO = 4.0
P1_STDDEV_FACTOR = 3.5
P1_STDDEV_MIN = 15.0
MAX_PER_UNIT = 800

p1_history = deque([25.0, -25.0], maxlen=8)
zero_next = 0.0
zero_fast = 0.0


def _f(entity_id, default=0.0):
    """Safely convert HA state to float."""
    try:
        return float(state.get(entity_id))
    except Exception:
        return float(default)


def _p1_entity():
    """Return configured P1 entity id."""
    candidate = str(state.get("input_text.zendure_power_meter_total_consumption") or "").strip()
    if candidate.startswith("sensor."):
        return candidate
    return "sensor.power_actual"


def _p1_value():
    """Read current P1 value from configured entity."""
    return _f(_p1_entity(), 0.0)


def _i(entity_id, default=0):
    """Safely convert HA state to int."""
    try:
        return int(float(state.get(entity_id)))
    except Exception:
        return int(default)


def _publish_unit(unit: int, watts: int):
    """Dispatch output via existing v130 scripts (keeps !secret MQTT topics in YAML)."""
    watts = max(0, min(MAX_PER_UNIT, int(watts)))
    if unit == 1:
        service.call("script", "zendure_dispatch_u1_output", power=watts, ensure_output_mode=True)
    else:
        service.call("script", "zendure_dispatch_u2_output", power=watts, ensure_output_mode=True)


def _split_total(total: int):
    """SOC weighted split."""
    soc1 = max(0.0, _f("sensor.solarflow_1_battery_level", 50.0))
    soc2 = max(0.0, _f("sensor.solarflow_2_battery_level", 50.0))
    s = soc1 + soc2
    w1 = (soc1 / s) if s > 0 else 0.5
    p1 = int(total * w1)
    p2 = int(total - p1)
    return max(0, min(MAX_PER_UNIT, p1)), max(0, min(MAX_PER_UNIT, p2))


def _control_once(p1_value: float):
    """Main control step."""
    global zero_next, zero_fast

    now = time()

    # Fast gate
    if now < zero_fast:
        p1_history.append(p1_value)
        return

    # Stddev based fast detection
    avg = sum(p1_history) / len(p1_history) if len(p1_history) else p1_value
    variance = sum((x - avg) ** 2 for x in p1_history) / len(p1_history) if len(p1_history) else 0.0
    stddev = P1_STDDEV_FACTOR * max(P1_STDDEV_MIN, sqrt(variance))
    is_fast = abs(p1_value - avg) > stddev or (len(p1_history) > 0 and abs(p1_value - p1_history[0]) > stddev)
    if is_fast:
        p1_history.clear()
    p1_history.append(p1_value)

    if (not is_fast) and now <= zero_next:
        return

    cmd1 = _i("input_number.zendure_last_sent_1", 0)
    cmd2 = _i("input_number.zendure_last_sent_2", 0)
    cmd_total = cmd1 + cmd2

    out_pwr_total = _i("sensor.solarflow_1_output_power", 0) + _i("sensor.solarflow_2_output_power", 0)

    # command-first blend to avoid slow output_power lag
    control_total = int(cmd_total * 0.75 + out_pwr_total * 0.25)

    bias = _i("input_number.zendure_conf_grid_bias", 10)
    max_total = _i("input_number.zendure_conf_max_output", 1200)
    hysteresis = _i("input_number.zendure_conf_hysteresis", 8)

    target_raw = control_total + int(p1_value) - bias
    target_total = max(0, min(max_total, target_raw))

    delta = target_total - control_total
    if abs(delta) <= hysteresis and not is_fast:
        zero_next = now + TIMEZERO
        zero_fast = now + TIMEFAST
        return

    u1, u2 = _split_total(target_total)
    if abs(u1 - cmd1) >= 8:
        _publish_unit(1, u1)
    if abs(u2 - cmd2) >= 8:
        _publish_unit(2, u2)

    service.call("input_number", "set_value", entity_id="input_number.zendure_target_total", value=target_total)

    zero_next = now + TIMEZERO
    zero_fast = now + TIMEFAST


@state_trigger("sensor.power_actual")
@state_trigger("sensor.power_meter_total_consumption")
def zendure_p1_on_change(value=None, old_value=None):
    """Handle P1 state changes."""
    if state.get("input_boolean.zendure_auto_mode") != "on":
        return
    try:
        p1 = float(value)
    except Exception:
        p1 = _p1_value()
    _control_once(p1)


@time_trigger("period(2s)")
def zendure_p1_periodic():
    """Fallback periodic controller tick."""
    if state.get("input_boolean.zendure_auto_mode") != "on":
        return
    _control_once(_p1_value())
