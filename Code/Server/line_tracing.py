"""
Line Tracing Script - Freenove 4WD Smart Car
=============================================
Uses the three infrared sensors to follow a dark line on a light surface.

Sensor layout (front of car):
        [ LEFT ]  [ CENTER ]  [ RIGHT ]
         GPIO14     GPIO15      GPIO23

The sensors return 1 when they detect the dark line.
read_all_infrared() packs them into a 3-bit number:
    bit2=LEFT  bit1=CENTER  bit0=RIGHT

All possible sensor states:
    Value  L  C  R  Meaning                  Action
    -----  -  -  -  -----------------------  -------------------------
      0    0  0  0  No line – completely lost  Search using last direction
      1    0  0  1  Line far right             Hard right turn
      2    0  1  0  Line centred               Drive forward
      3    0  1  1  Line slightly right        Gentle right curve
      4    1  0  0  Line far left              Hard left turn
      5    1  0  1  Split / junction           Drive forward (rare)
      6    1  1  0  Line slightly left         Gentle left curve
      7    1  1  1  All sensors on (T-junction / end)  Stop

Run from the Code/Server/ directory:
    python line_tracing.py

Press Ctrl+C to stop.
"""

import time
from infrared import Infrared
from motor import Ordinary_Car

# ── Tunable constants ──────────────────────────────────────────────────────────
BASE_SPEED      = 700   # forward speed on a straight (0-4095)
TURN_OUTER      = 1800  # outer wheel speed during a hard turn
TURN_INNER      = -300  # inner wheel speed during a hard turn
CURVE_OUTER     = 1400  # outer wheel speed during a gentle curve
CURVE_INNER     = 300   # inner wheel speed during a gentle curve
SEARCH_SPEED    = 800   # speed used when sweeping to find a lost line
SEARCH_STEP     = 0.15  # seconds per search sweep step
LOOP_DELAY      = 0.01  # seconds between sensor reads
# ──────────────────────────────────────────────────────────────────────────────

LEFT  = 'left'
RIGHT = 'right'


def search_for_line(motor: Ordinary_Car, infrared: Infrared, last_dir: str) -> bool:
    """
    Sweep in the last known turn direction to try to re-find the line.
    Tries that side first, then the opposite side if still nothing.
    Returns True if the line was found, False if still lost.
    """
    directions = [last_dir, RIGHT if last_dir == LEFT else LEFT]

    for direction in directions:
        print(f"Searching {direction.upper()}...", end='\r')

        if direction == LEFT:
            motor.set_motor_model(-SEARCH_SPEED, -SEARCH_SPEED, SEARCH_SPEED, SEARCH_SPEED)
        else:
            motor.set_motor_model(SEARCH_SPEED, SEARCH_SPEED, -SEARCH_SPEED, -SEARCH_SPEED)

        time.sleep(SEARCH_STEP)
        motor.set_motor_model(0, 0, 0, 0)
        time.sleep(0.05)

        if infrared.read_all_infrared() != 0:
            return True

    return False


def run():
    print("Initialising hardware...")
    motor = Ordinary_Car()
    infrared = Infrared()

    last_turn = LEFT
    line_lost = False

    print("Line tracing running. Place the car on the line. Press Ctrl+C to stop.\n")

    try:
        while True:
            value = infrared.read_all_infrared()

            # Resume automatically when line reappears after a full stop
            if line_lost and value != 0:
                print("Line found – resuming  ", end='\r')
                line_lost = False

            if line_lost:
                time.sleep(LOOP_DELAY)
                continue

            if value == 2:
                print("Forward         ", end='\r')
                motor.set_motor_model(BASE_SPEED, BASE_SPEED, BASE_SPEED, BASE_SPEED)

            elif value == 1:
                print("Hard RIGHT      ", end='\r')
                last_turn = RIGHT
                motor.set_motor_model(TURN_OUTER, TURN_OUTER, TURN_INNER, TURN_INNER)

            elif value == 3:
                print("Curve RIGHT     ", end='\r')
                last_turn = RIGHT
                motor.set_motor_model(CURVE_OUTER, CURVE_OUTER, CURVE_INNER, CURVE_INNER)

            elif value == 4:
                print("Hard LEFT       ", end='\r')
                last_turn = LEFT
                motor.set_motor_model(TURN_INNER, TURN_INNER, TURN_OUTER, TURN_OUTER)

            elif value == 6:
                print("Curve LEFT      ", end='\r')
                last_turn = LEFT
                motor.set_motor_model(CURVE_INNER, CURVE_INNER, CURVE_OUTER, CURVE_OUTER)

            elif value == 5:
                print("Junction        ", end='\r')
                motor.set_motor_model(BASE_SPEED, BASE_SPEED, BASE_SPEED, BASE_SPEED)

            elif value == 7:
                print("T-junction/End  ", end='\r')
                motor.set_motor_model(0, 0, 0, 0)

            else:
                # value == 0 — line lost, do one sweep to try to recover
                motor.set_motor_model(0, 0, 0, 0)
                found = search_for_line(motor, infrared, last_turn)
                if not found:
                    line_lost = True
                    motor.set_motor_model(0, 0, 0, 0)
                    print("No line found – stopped. Place car on line to resume.", end='\r')

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\n\nStopping – KeyboardInterrupt received.")
    finally:
        motor.set_motor_model(0, 0, 0, 0)
        infrared.close()
        motor.close()
        print("Hardware released. Goodbye.")


if __name__ == '__main__':
    run()
