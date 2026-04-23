"""
Light Tracking Script - Freenove 4WD Smart Car
===============================================
The car uses two photoresistors (left ADC ch0, right ADC ch1) to track a
light source (torch, lamp, etc.).

  SEEKING  – one sensor sees significantly more light: turn toward it.
  FORWARD  – both sensors see bright light and are balanced: drive forward.
  CENTERED – balanced AND bright: stop (car is pointing directly at the source).
  SEARCH   – neither sensor detects enough light: spin slowly to find it.

Run from the Code/Server/ directory:
    python light_tracking.py

Press Ctrl+C to stop.
"""

import time
from adc import ADC
from motor import Ordinary_Car

# ── Tunable constants ──────────────────────────────────────────────────────────
BRIGHT_THRESHOLD  = 2.99  # V – below this voltage the sensor sees "bright" light
BALANCE_TOLERANCE = 0.15  # V – L/R difference below this means "centred"
SEEK_TOLERANCE    = 0.30  # V – L/R difference above this triggers a hard turn

FORWARD_SPEED     = 700   # wheel speed when driving toward the light (0-4095)
TURN_OUTER        = 1400  # outer-wheel speed during a gentle curve
TURN_INNER        = -300  # inner-wheel speed during a gentle curve
HARD_TURN_OUTER   = 1800  # outer-wheel speed during a hard turn
HARD_TURN_INNER   = -800  # inner-wheel speed during a hard turn
SEARCH_SPEED      = 1000  # speed used during search spin

LOOP_DELAY        = 0.05  # seconds between sensor reads
# ──────────────────────────────────────────────────────────────────────────────


# ── Motor helpers ──────────────────────────────────────────────────────────────

def stop(motor: Ordinary_Car):
    motor.set_motor_model(0, 0, 0, 0)

def forward(motor: Ordinary_Car):
    motor.set_motor_model(FORWARD_SPEED, FORWARD_SPEED, FORWARD_SPEED, FORWARD_SPEED)

def curve_left(motor: Ordinary_Car, hard: bool = False):
    """Left wheels brake/reverse, right wheels drive – car arcs left."""
    inner = HARD_TURN_INNER if hard else TURN_INNER
    outer = HARD_TURN_OUTER if hard else TURN_OUTER
    motor.set_motor_model(inner, inner, outer, outer)

def curve_right(motor: Ordinary_Car, hard: bool = False):
    """Right wheels brake/reverse, left wheels drive – car arcs right."""
    inner = HARD_TURN_INNER if hard else TURN_INNER
    outer = HARD_TURN_OUTER if hard else TURN_OUTER
    motor.set_motor_model(outer, outer, inner, inner)

def spin_search(motor: Ordinary_Car):
    """Spin slowly in place to sweep for a light source."""
    motor.set_motor_model(-SEARCH_SPEED, -SEARCH_SPEED, SEARCH_SPEED, SEARCH_SPEED)


# ── Main loop ──────────────────────────────────────────────────────────────────

def run():
    print("Initialising hardware...")
    motor = Ordinary_Car()
    adc   = ADC()

    print("\nLight tracking running.  Point a torch at the car to start.")
    print("Press Ctrl+C to stop.\n")
    print(f"  Bright threshold : < {BRIGHT_THRESHOLD} V")
    print(f"  Balance tolerance: ± {BALANCE_TOLERANCE} V")
    print(f"  Hard-turn trigger: > {SEEK_TOLERANCE} V difference\n")

    try:
        while True:
            L = adc.read_adc(0)  # left photoresistor voltage
            R = adc.read_adc(1)  # right photoresistor voltage
            diff = L - R         # positive → left darker, right brighter

            left_bright  = L < BRIGHT_THRESHOLD
            right_bright = R < BRIGHT_THRESHOLD
            balanced     = abs(diff) < BALANCE_TOLERANCE

            if not left_bright and not right_bright:
                # Neither sensor sees light – spin to search
                print(f"SEARCH   L={L:.2f}V  R={R:.2f}V  diff={diff:+.2f}V", end='\r')
                spin_search(motor)

            elif balanced and left_bright and right_bright:
                # Both bright and equal – stop, we're pointing at the source
                print(f"CENTERED L={L:.2f}V  R={R:.2f}V  diff={diff:+.2f}V", end='\r')
                stop(motor)

            elif balanced:
                # Roughly equal, at least one side is lit – creep forward
                print(f"FORWARD  L={L:.2f}V  R={R:.2f}V  diff={diff:+.2f}V", end='\r')
                forward(motor)

            else:
                # One side brighter – turn toward the brighter side
                hard = abs(diff) > SEEK_TOLERANCE
                if diff > 0:
                    # L > R  →  right side is brighter → turn right
                    label = "SEEK-R(hard)" if hard else "SEEK-R      "
                    print(f"{label} L={L:.2f}V  R={R:.2f}V  diff={diff:+.2f}V", end='\r')
                    curve_right(motor, hard=hard)
                else:
                    # R > L  →  left side is brighter → turn left
                    label = "SEEK-L(hard)" if hard else "SEEK-L      "
                    print(f"{label} L={L:.2f}V  R={R:.2f}V  diff={diff:+.2f}V", end='\r')
                    curve_left(motor, hard=hard)

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\n\nStopping – KeyboardInterrupt received.")
    finally:
        stop(motor)
        adc.close_i2c()
        motor.close()
        print("Hardware released. Goodbye.")


if __name__ == '__main__':
    run()
