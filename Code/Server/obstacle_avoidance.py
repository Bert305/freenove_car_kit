"""
Obstacle Avoidance Script - Freenove 4WD Smart Car
===================================================
Drives the car forward and automatically avoids obstacles using
the ultrasonic sensor. When an obstacle is detected:
  1. The car stops and reverses briefly.
  2. The servo scans left and right to find the clearer path.
  3. The car turns toward the clearer side, then resumes forward.

Run from the Code/Server/ directory:
    python obstacle_avoidance.py

Press Ctrl+C to stop.
"""

import time
import sys
from ultrasonic import Ultrasonic
from motor import Ordinary_Car
from servo import Servo

# ── Tunable constants ──────────────────────────────────────────────────────────
STOP_DISTANCE     = 30   # cm – stop and react when obstacle is closer than this
SAFE_DISTANCE     = 40   # cm – resume forward only when path is this clear
DRIVE_SPEED       = 1500 # motor duty for normal forward driving  (0-4095)
BACKUP_SPEED      = 1200 # motor duty when reversing
TURN_SPEED        = 1500 # motor duty when turning
BACKUP_TIME       = 0.5  # seconds to reverse before scanning
TURN_TIME         = 0.6  # seconds to turn before re-checking
SCAN_SETTLE_TIME  = 0.3  # seconds to wait after moving servo before reading
LOOP_DELAY        = 0.05 # seconds between main loop iterations
# ──────────────────────────────────────────────────────────────────────────────

# Servo angle positions (channel '0' is the pan/horizontal servo)
SERVO_CENTER = 90   # degrees – facing forward
SERVO_LEFT   = 150  # degrees – facing left
SERVO_RIGHT  = 30   # degrees – facing right


def scan_distances(sonic: Ultrasonic, servo: Servo) -> dict:
    """
    Point the servo left, centre, and right, take a distance reading at each
    position, then return the servo to centre.

    Returns a dict with keys 'left', 'centre', 'right' (values in cm).
    """
    readings = {}
    positions = [
        ('left',   SERVO_LEFT),
        ('centre', SERVO_CENTER),
        ('right',  SERVO_RIGHT),
    ]
    for label, angle in positions:
        servo.set_servo_pwm('0', angle)
        time.sleep(SCAN_SETTLE_TIME)
        dist = sonic.get_distance()
        readings[label] = dist if dist is not None else 0.0
        print(f"  Scan {label:6s} ({angle:3d}°): {readings[label]:.1f} cm")

    # Return servo to centre
    servo.set_servo_pwm('0', SERVO_CENTER)
    time.sleep(SCAN_SETTLE_TIME)
    return readings


def drive_forward(motor: Ordinary_Car, speed: int = DRIVE_SPEED):
    """All four wheels forward."""
    motor.set_motor_model(speed, speed, speed, speed)


def drive_backward(motor: Ordinary_Car, speed: int = BACKUP_SPEED):
    """All four wheels backward."""
    motor.set_motor_model(-speed, -speed, -speed, -speed)


def turn_left(motor: Ordinary_Car, speed: int = TURN_SPEED):
    """Left wheels backward, right wheels forward → turns left."""
    motor.set_motor_model(-speed, -speed, speed, speed)


def turn_right(motor: Ordinary_Car, speed: int = TURN_SPEED):
    """Left wheels forward, right wheels backward → turns right."""
    motor.set_motor_model(speed, speed, -speed, -speed)


def stop(motor: Ordinary_Car):
    motor.set_motor_model(0, 0, 0, 0)


def avoid_obstacle(motor: Ordinary_Car, sonic: Ultrasonic, servo: Servo):
    """
    Full obstacle-avoidance manoeuvre:
      1. Stop immediately.
      2. Reverse for BACKUP_TIME seconds.
      3. Scan left, centre, and right.
      4. Turn toward whichever side has more space.
      5. Keep turning until the forward path is clear.
    """
    print("Obstacle detected! Stopping...")
    stop(motor)
    time.sleep(0.1)

    print("Reversing...")
    drive_backward(motor)
    time.sleep(BACKUP_TIME)
    stop(motor)
    time.sleep(0.1)

    print("Scanning for clear path...")
    distances = scan_distances(sonic, servo)

    # Decide which way to turn
    if distances['left'] >= distances['right']:
        print(f"Turning LEFT  (left={distances['left']:.1f} cm  right={distances['right']:.1f} cm)")
        turn_action = turn_left
    else:
        print(f"Turning RIGHT (left={distances['left']:.1f} cm  right={distances['right']:.1f} cm)")
        turn_action = turn_right

    # Keep turning until the centre is clear
    while True:
        turn_action(motor)
        time.sleep(TURN_TIME)
        stop(motor)
        time.sleep(0.1)

        servo.set_servo_pwm('0', SERVO_CENTER)
        time.sleep(SCAN_SETTLE_TIME)
        front_dist = sonic.get_distance() or 0.0
        print(f"  Front distance after turn: {front_dist:.1f} cm")

        if front_dist >= SAFE_DISTANCE:
            print("Path clear – resuming forward drive.\n")
            break


def run():
    """Main entry point."""
    print("Initialising hardware...")
    motor = Ordinary_Car()
    sonic = Ultrasonic()
    servo = Servo()

    # Point the sensor straight ahead at startup
    servo.set_servo_pwm('0', SERVO_CENTER)
    time.sleep(0.5)

    print("Obstacle avoidance running. Press Ctrl+C to stop.\n")
    try:
        while True:
            # Read the distance straight ahead
            distance = sonic.get_distance()
            if distance is None:
                # Sensor glitch – keep moving cautiously
                time.sleep(LOOP_DELAY)
                continue

            print(f"Distance: {distance:.1f} cm", end='\r')

            if distance < STOP_DISTANCE:
                avoid_obstacle(motor, sonic, servo)
            else:
                drive_forward(motor)

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\n\nStopping – KeyboardInterrupt received.")
    finally:
        stop(motor)
        sonic.close()
        motor.close()
        print("Hardware released. Goodbye.")


if __name__ == '__main__':
    run()
