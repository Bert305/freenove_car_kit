"""
Obstacle Avoidance Script - Freenove 4WD Smart Car
===================================================
Three-zone detection system:

  GREEN  zone (>= WARNING_DISTANCE):  Drive forward at full speed.
  YELLOW zone (WARNING_DISTANCE > d >= STOP_DISTANCE):
      Obstacle spotted early – STOP immediately, scan left/right,
      then curve around before ever getting close.
  RED    zone (< STOP_DISTANCE):
      Too close to steer – full emergency stop, reverse, then turn
      until the path is clear.

Run from the Code/Server/ directory:
    python obstacle_avoidance.py

Press Ctrl+C to stop.
"""

import time
from ultrasonic import Ultrasonic
from motor import Ordinary_Car
from servo import Servo

# ── Tunable constants ──────────────────────────────────────────────────────────
WARNING_DISTANCE  = 100  # cm – stop & scan when obstacle is this far away
STOP_DISTANCE     = 35   # cm – emergency fallback if still approaching
SAFE_DISTANCE     = 50   # cm – resume forward only when path is this clear

DRIVE_SPEED       = 1500 # full forward speed (0-4095)
BACKUP_SPEED      = 1200 # reverse speed during emergency manoeuvre
TURN_SPEED        = 1500 # speed used for on-the-spot turns
STEER_INNER       = 300  # inner-wheel duty when smoothly curving
STEER_OUTER       = 1800 # outer-wheel duty when smoothly curving

BACKUP_TIME       = 0.5  # seconds to reverse before scanning (emergency only)
TURN_TIME         = 0.6  # seconds per turn step (emergency only)
SCAN_SETTLE_TIME  = 0.15 # seconds to let servo settle before reading (was 0.25)
LOOP_DELAY        = 0.01 # seconds between main-loop iterations (was 0.05)
# ──────────────────────────────────────────────────────────────────────────────

SERVO_CENTER = 90
SERVO_LEFT   = 150
SERVO_RIGHT  = 30


# ── Motor helpers ──────────────────────────────────────────────────────────────

def stop(motor: Ordinary_Car):
    motor.set_motor_model(0, 0, 0, 0)

def drive_forward(motor: Ordinary_Car, speed: int = DRIVE_SPEED):
    motor.set_motor_model(speed, speed, speed, speed)

def drive_backward(motor: Ordinary_Car, speed: int = BACKUP_SPEED):
    motor.set_motor_model(-speed, -speed, -speed, -speed)

def turn_left(motor: Ordinary_Car, speed: int = TURN_SPEED):
    """Spin left in place."""
    motor.set_motor_model(-speed, -speed, speed, speed)

def turn_right(motor: Ordinary_Car, speed: int = TURN_SPEED):
    """Spin right in place."""
    motor.set_motor_model(speed, speed, -speed, -speed)

def curve_left(motor: Ordinary_Car):
    """Gentle curve left – left wheels slower, right wheels faster."""
    motor.set_motor_model(STEER_INNER, STEER_INNER, STEER_OUTER, STEER_OUTER)

def curve_right(motor: Ordinary_Car):
    """Gentle curve right – right wheels slower, left wheels faster."""
    motor.set_motor_model(STEER_OUTER, STEER_OUTER, STEER_INNER, STEER_INNER)


# ── Sensor helpers ─────────────────────────────────────────────────────────────

def read_distance(sonic: Ultrasonic, servo: Servo, angle: int) -> float:
    """Point servo to angle, wait for it to settle, return distance in cm."""
    servo.set_servo_pwm('0', angle)
    time.sleep(SCAN_SETTLE_TIME)
    d = sonic.get_distance()
    return d if d is not None else 0.0

def quick_scan(sonic: Ultrasonic, servo: Servo) -> tuple[float, float]:
    """
    Quick left/right scan while the car can still move.
    Returns (left_cm, right_cm). Restores servo to centre when done.
    """
    left  = read_distance(sonic, servo, SERVO_LEFT)
    right = read_distance(sonic, servo, SERVO_RIGHT)
    servo.set_servo_pwm('0', SERVO_CENTER)
    time.sleep(SCAN_SETTLE_TIME)
    print(f"  Quick scan → left={left:.1f} cm  right={right:.1f} cm")
    return left, right

def full_scan(sonic: Ultrasonic, servo: Servo) -> dict:
    """
    Full three-point scan (left / centre / right).
    Used during the emergency manoeuvre when the car is stationary.
    Returns dict with keys 'left', 'centre', 'right'.
    """
    readings = {}
    for label, angle in [('left', SERVO_LEFT), ('centre', SERVO_CENTER), ('right', SERVO_RIGHT)]:
        readings[label] = read_distance(sonic, servo, angle)
        print(f"  Full scan {label:6s} ({angle:3d}°): {readings[label]:.1f} cm")
    servo.set_servo_pwm('0', SERVO_CENTER)
    time.sleep(SCAN_SETTLE_TIME)
    return readings


# ── Avoidance behaviours ───────────────────────────────────────────────────────

def steer_around(motor: Ordinary_Car, sonic: Ultrasonic, servo: Servo) -> bool:
    """
    YELLOW zone: obstacle spotted early enough to steer around it.
    Slows the car, scans left/right, and curves toward the clearer side
    while still moving forward.

    Returns True if the car successfully steered clear (front now open),
    or False if the obstacle is still too close and needs emergency handling.
    """
    print("[YELLOW] Obstacle ahead – stopping to scan...")
    stop(motor)
    time.sleep(0.1)

    left, right = quick_scan(sonic, servo)

    if left >= right:
        print(f"  Curving LEFT (more space: {left:.1f} cm vs {right:.1f} cm)")
        curve_left(motor)
    else:
        print(f"  Curving RIGHT (more space: {right:.1f} cm vs {left:.1f} cm)")
        curve_right(motor)

    # Curve for a short burst then re-check the front
    time.sleep(0.4)

    servo.set_servo_pwm('0', SERVO_CENTER)
    time.sleep(SCAN_SETTLE_TIME)
    front = sonic.get_distance() or 0.0
    print(f"  Front after steering: {front:.1f} cm")
    return front >= SAFE_DISTANCE


def emergency_avoid(motor: Ordinary_Car, sonic: Ultrasonic, servo: Servo):
    """
    RED zone: too close to steer. Full stop → reverse → scan → turn until clear.
    """
    print("[RED] Too close! Emergency stop.")
    stop(motor)
    time.sleep(0.1)

    print("  Reversing...")
    drive_backward(motor)
    time.sleep(BACKUP_TIME)
    stop(motor)
    time.sleep(0.1)

    print("  Full scan for clear path...")
    distances = full_scan(sonic, servo)

    if distances['left'] >= distances['right']:
        print(f"  Turning LEFT (left={distances['left']:.1f}  right={distances['right']:.1f})")
        turn_action = turn_left
    else:
        print(f"  Turning RIGHT (right={distances['right']:.1f}  left={distances['left']:.1f})")
        turn_action = turn_right

    # Keep turning until the front is clear
    while True:
        turn_action(motor)
        time.sleep(TURN_TIME)
        stop(motor)
        time.sleep(0.1)

        front = read_distance(sonic, servo, SERVO_CENTER)
        print(f"  Front after turn step: {front:.1f} cm")
        if front >= SAFE_DISTANCE:
            print("  Path clear – resuming.\n")
            break


# ── Main loop ──────────────────────────────────────────────────────────────────

def run():
    print("Initialising hardware...")
    motor = Ordinary_Car()
    sonic = Ultrasonic()
    servo = Servo()

    servo.set_servo_pwm('0', SERVO_CENTER)
    time.sleep(0.5)

    print("Obstacle avoidance running.  Press Ctrl+C to stop.\n")
    print(f"  GREEN  zone : >= {WARNING_DISTANCE} cm  → full speed ahead")
    print(f"  YELLOW zone : {STOP_DISTANCE}–{WARNING_DISTANCE} cm → slow & steer")
    print(f"  RED    zone : <  {STOP_DISTANCE} cm  → emergency stop\n")

    try:
        while True:
            distance = sonic.get_distance()
            if distance is None:
                time.sleep(LOOP_DELAY)
                continue

            print(f"Distance: {distance:5.1f} cm", end='\r')

            if distance < STOP_DISTANCE:
                # RED zone – emergency manoeuvre
                emergency_avoid(motor, sonic, servo)

            elif distance < WARNING_DISTANCE:
                # YELLOW zone – try to steer around while still moving
                cleared = steer_around(motor, sonic, servo)
                if not cleared:
                    # Steering wasn't enough – hand off to emergency handler
                    emergency_avoid(motor, sonic, servo)

            else:
                # GREEN zone – open road, full speed
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
