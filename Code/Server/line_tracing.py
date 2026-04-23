"""
Line Tracing Script - Freenove 4WD Smart Car
=============================================
AUTO mode  – line detected:  car follows the line automatically.
MANUAL mode – line lost:     use keyboard to nudge back onto the line.

  Manual controls (when line is lost):
      A  –  nudge left
      D  –  nudge right
      W  –  creep forward
      S  –  stop / hold still

  The car switches back to AUTO the moment any sensor sees the line again.

Run from the Code/Server/ directory:
    python line_tracing.py

Press Ctrl+C to stop.
"""

import sys
import tty
import termios
import select
import time
from infrared import Infrared
from motor import Ordinary_Car

# ── Tunable constants ──────────────────────────────────────────────────────────
BASE_SPEED      = 700   # forward speed on a straight (0-4095)
TURN_OUTER      = 1800  # outer wheel speed during a hard turn
TURN_INNER      = -300  # inner wheel speed during a hard turn
CURVE_OUTER     = 1400  # outer wheel speed during a gentle curve
CURVE_INNER     = 300   # inner wheel speed during a gentle curve
MANUAL_SPEED    = 1500  # wheel speed used for manual nudges
LOOP_DELAY      = 0.01  # seconds between sensor reads
# ──────────────────────────────────────────────────────────────────────────────

LEFT  = 'left'
RIGHT = 'right'


def get_key() -> str | None:
    """Non-blocking single-character read. Returns None if no key is waiting."""
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1).lower()
    return None


def run():
    print("Initialising hardware...")
    motor = Ordinary_Car()
    infrared = Infrared()

    last_turn = LEFT
    mode      = 'AUTO'   # 'AUTO' or 'MANUAL'

    # Put terminal in cbreak mode so keys register instantly without Enter
    fd           = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    print("\nLine tracing running. Press Ctrl+C to stop.")
    print("──────────────────────────────────────────")
    print("AUTO   – following line automatically")
    print("MANUAL – A=left  D=right  W=forward  S=stop")
    print("──────────────────────────────────────────\n")

    try:
        tty.setcbreak(fd)

        while True:
            value = infrared.read_all_infrared()
            key   = get_key()

            # ── Switch to AUTO the moment the line reappears ──────────────────
            if mode == 'MANUAL' and value != 0:
                mode = 'AUTO'
                print("\n[AUTO]   Line detected – resuming auto follow.        ")

            # ── Switch to MANUAL when line is completely lost ─────────────────
            if mode == 'AUTO' and value == 0:
                mode = 'MANUAL'
                motor.set_motor_model(0, 0, 0, 0)
                print("\n[MANUAL] Line lost – use A/D/W/S to steer back.      ")

            # ═══════════════════════════════════════════════════════════════════
            if mode == 'AUTO':
                # ── Automatic line following ──────────────────────────────────

                if value == 2:
                    print("AUTO  Forward         ", end='\r')
                    motor.set_motor_model(BASE_SPEED, BASE_SPEED, BASE_SPEED, BASE_SPEED)

                elif value == 1:
                    print("AUTO  Hard RIGHT      ", end='\r')
                    last_turn = RIGHT
                    motor.set_motor_model(TURN_OUTER, TURN_OUTER, TURN_INNER, TURN_INNER)

                elif value == 3:
                    print("AUTO  Curve RIGHT     ", end='\r')
                    last_turn = RIGHT
                    motor.set_motor_model(CURVE_OUTER, CURVE_OUTER, CURVE_INNER, CURVE_INNER)

                elif value == 4:
                    print("AUTO  Hard LEFT       ", end='\r')
                    last_turn = LEFT
                    motor.set_motor_model(TURN_INNER, TURN_INNER, TURN_OUTER, TURN_OUTER)

                elif value == 6:
                    print("AUTO  Curve LEFT      ", end='\r')
                    last_turn = LEFT
                    motor.set_motor_model(CURVE_INNER, CURVE_INNER, CURVE_OUTER, CURVE_OUTER)

                elif value == 5:
                    print("AUTO  Junction        ", end='\r')
                    motor.set_motor_model(BASE_SPEED, BASE_SPEED, BASE_SPEED, BASE_SPEED)

                elif value == 7:
                    print("AUTO  T-junction/End  ", end='\r')
                    motor.set_motor_model(0, 0, 0, 0)

            else:
                # ── Manual control ────────────────────────────────────────────
                if key == 'a':
                    print("MANUAL Nudge LEFT     ", end='\r')
                    motor.set_motor_model(-MANUAL_SPEED, -MANUAL_SPEED, MANUAL_SPEED, MANUAL_SPEED)

                elif key == 'd':
                    print("MANUAL Nudge RIGHT    ", end='\r')
                    motor.set_motor_model(MANUAL_SPEED, MANUAL_SPEED, -MANUAL_SPEED, -MANUAL_SPEED)

                elif key == 'w':
                    print("MANUAL Creep forward  ", end='\r')
                    motor.set_motor_model(MANUAL_SPEED, MANUAL_SPEED, MANUAL_SPEED, MANUAL_SPEED)

                elif key == 's':
                    print("MANUAL Stopped        ", end='\r')
                    motor.set_motor_model(0, 0, 0, 0)

                elif key is None:
                    # No key held — stop drifting
                    motor.set_motor_model(0, 0, 0, 0)

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\n\nStopping – KeyboardInterrupt received.")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        motor.set_motor_model(0, 0, 0, 0)
        infrared.close()
        motor.close()
        print("Hardware released. Goodbye.")


if __name__ == '__main__':
    run()
