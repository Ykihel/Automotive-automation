"""
Generic Cruise‑Control Test Script
=================================

This Python script demonstrates a *pattern* for automating ECU / CAN‑bus
integration tests without exposing any proprietary information.

All project‑specific libraries, signal names, and identifiers from the
original (confidential) script have been replaced by:
    • Plain‑Python wrappers (see `write_signal`, `read_signal`, etc.)
    • Generic constant strings like "CruiseControlActive"
    • Simple timing helpers using `time.sleep`

The structure preserves the intent of the original test:
    1. Power‑up and verify that cruise control is *inactive* at stand‑still.
    2. Bring the vehicle above the activation threshold, press *SET*, and
       verify that cruise control becomes *active*.

Feel free to fork and extend this template with your own bus interface
and domain‑specific logic.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Dict

###############################################################################
#                             Abstraction Layer                               #
###############################################################################

# In a real environment, the following helpers would talk to your middleware
# (e.g. CANoe, CANalyzer, dSPACE, ETAS, custom Python APIs, etc.).
# Here they just log what would normally happen.


@dataclass
class _MockBus:
    """A *very* small in‑memory stand‑in for an ECU bus."""

    signals: Dict[str, Any] = None

    def __post_init__(self):
        if self.signals is None:
            self.signals = {
                "CruiseControlActive": 0,
                "CruiseControlEnabledSwitch": 0,
                "CruiseControlStates": 0,
                "CruiseControlSetSpeed": 0,
                "VehicleSpeed": 0,
            }

    # --------------------------------------------------------------------- #
    #  Simple read / write API – replace with real bus access in production  #
    # --------------------------------------------------------------------- #

    def write(self, name: str, value: Any) -> None:
        logging.debug("WRITE %s <- %s", name, value)
        self.signals[name] = value

    def read(self, name: str) -> Any:
        value = self.signals.get(name)
        logging.debug("READ  %s -> %s", name, value)
        return value


# Singleton instance used by helper functions below
_BUS = _MockBus()


def write_signal(name: str, value: Any) -> None:  # noqa: D401
    """Write `value` to an ECU/CAN signal called *name*."""

    _BUS.write(name, value)


def read_signal(name: str) -> Any:  # noqa: D401
    """Read and return the current value of ECU/CAN signal *name*."""

    return _BUS.read(name)


def sleep_seconds(seconds: float) -> None:  # noqa: D401
    """Pause execution while logging the wait (wrapper around ``time.sleep``)."""

    logging.debug("SLEEP %.1f s", seconds)
    time.sleep(seconds)


###############################################################################
#                             High‑Level Actions                              #
###############################################################################

# Delay constants (seconds)
DELAY_SHORT = 2
DELAY_MEDIUM = 4


def power_on() -> None:
    write_signal("PowerSupply", 1)
    sleep_seconds(DELAY_SHORT)


def engine_start() -> None:
    write_signal("EngineStart", 1)
    sleep_seconds(DELAY_SHORT)


def increase_gear() -> None:
    write_signal("GearIncreaseOne", 1)
    sleep_seconds(DELAY_SHORT)


def press_acc_pedal(percent: int) -> None:
    write_signal("AccPedal", percent)
    sleep_seconds(DELAY_MEDIUM)


def press_cc_set_button() -> None:
    write_signal("CruiseControlSetButton", 1)
    sleep_seconds(DELAY_SHORT)


###############################################################################
#                                   Tests                                     #
###############################################################################


def verify_cruise_control_inactive() -> bool:
    """Return *True* if all cruise‑control signals indicate *inactive*."""

    return (
        read_signal("CruiseControlActive") == 0
        and read_signal("CruiseControlEnabledSwitch") == 0
        and read_signal("CruiseControlStates") == 0
        and read_signal("CruiseControlSetSpeed") == 0
    )


def verify_cruise_control_active(target_speed_max: int = 35) -> bool:
    """Check that cruise control is *active* and a set‑speed has been stored."""

    return (
        read_signal("CruiseControlActive") == 1
        and read_signal("CruiseControlEnabledSwitch") == 1
        and read_signal("CruiseControlStates") == 6  # typical *Active* state
        and read_signal("CruiseControlSetSpeed") <= target_speed_max
    )


###############################################################################
#                               Test Scenario                                 #
###############################################################################


def run_test() -> None:  # noqa: D401 – CLI entry‑point
    """Execute the two‑step cruise‑control test."""

    logging.info("========== Cruise‑Control Test ==========")

    # STEP 1 – Startup and baseline checks
    logging.info("STEP 1 — Power‑up and baseline")
    power_on()
    engine_start()

    if verify_cruise_control_inactive():
        logging.info("Step 1 PASSED: cruise control correctly inactive at startup.")
    else:
        logging.error("Step 1 FAILED: unexpected cruise‑control status at startup.")
        return  # Stop on failure – or continue depending on policy

    # STEP 2 – Reach activation speed and press *SET*
    logging.info("STEP 2 — Activate cruise control")

    # Bring speed into the activation window (30–35 km/h in this demo)
    target_speed = random.randint(30, 35)
    write_signal("VehicleSpeed", target_speed)
    press_acc_pedal(40)  # hold 40 % accelerator to stabilise speed
    increase_gear()
    press_cc_set_button()

    if verify_cruise_control_active():
        logging.info("Step 2 PASSED: cruise control activated as expected.")
    else:
        logging.error("Step 2 FAILED: cruise control did not activate correctly.")


###############################################################################
#                              Main guard                                      #
###############################################################################

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_test()
