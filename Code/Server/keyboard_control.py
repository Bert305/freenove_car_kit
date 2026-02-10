#!/usr/bin/env python3

# cd /home/miamiedtech/Freenove_4WD_Smart_Car_Kit_for_Raspberry_Pi/Code/Server python3 keyboard_control.py   
"""
Keyboard Control for Freenove 4WD Smart Car
Controls:
  W or Up Arrow    - Forward
  S or Down Arrow  - Backward
  A or Left Arrow  - Turn Left
  D or Right Arrow - Turn Right
  Space            - Stop
  + or =           - Increase Speed
  - or _           - Decrease Speed
  Q or ESC         - Quit
"""

import curses
import time
from motor import Ordinary_Car

class KeyboardController:
    def __init__(self):
        self.motor = Ordinary_Car()
        self.speed = 2000  # Default speed
        self.min_speed = 500
        self.max_speed = 4095
        self.speed_step = 200

    def increase_speed(self):
        self.speed = min(self.speed + self.speed_step, self.max_speed)
        return self.speed

    def decrease_speed(self):
        self.speed = max(self.speed - self.speed_step, self.min_speed)
        return self.speed

    def forward(self):
        self.motor.set_motor_model(self.speed, self.speed, self.speed, self.speed)

    def backward(self):
        self.motor.set_motor_model(-self.speed, -self.speed, -self.speed, -self.speed)

    def turn_left(self):
        self.motor.set_motor_model(-self.speed, -self.speed, self.speed, self.speed)

    def turn_right(self):
        self.motor.set_motor_model(self.speed, self.speed, -self.speed, -self.speed)

    def stop(self):
        self.motor.set_motor_model(0, 0, 0, 0)

    def close(self):
        self.stop()
        self.motor.close()

def display_status(stdscr, controller, last_command):
    """Display current status on screen"""
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    # Title
    title = "=== Freenove 4WD Car - Keyboard Control ==="
    stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)

    # Instructions
    instructions = [
        "",
        "Controls:",
        "  W or ↑      - Forward",
        "  S or ↓      - Backward",
        "  A or ←      - Turn Left",
        "  D or →      - Turn Right",
        "  SPACE       - Stop",
        "  + or =      - Increase Speed",
        "  - or _      - Decrease Speed",
        "  Q or ESC    - Quit",
        "",
        f"Current Speed: {controller.speed}",
        f"Last Command:  {last_command}",
        "",
        "Press a key to control the car..."
    ]

    for i, line in enumerate(instructions, start=2):
        if i < height - 1:
            stdscr.addstr(i, 2, line)

    stdscr.refresh()

def main(stdscr):
    # Initialize curses
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Non-blocking input
    stdscr.timeout(100) # 100ms timeout for getch()

    controller = KeyboardController()
    last_command = "None"
    running = True

    try:
        while running:
            display_status(stdscr, controller, last_command)

            key = stdscr.getch()

            if key == -1:  # No key pressed
                continue

            # Handle different key inputs
            if key in [ord('w'), ord('W'), curses.KEY_UP]:
                controller.forward()
                last_command = "Forward"

            elif key in [ord('s'), ord('S'), curses.KEY_DOWN]:
                controller.backward()
                last_command = "Backward"

            elif key in [ord('a'), ord('A'), curses.KEY_LEFT]:
                controller.turn_left()
                last_command = "Turn Left"

            elif key in [ord('d'), ord('D'), curses.KEY_RIGHT]:
                controller.turn_right()
                last_command = "Turn Right"

            elif key == ord(' '):
                controller.stop()
                last_command = "Stop"

            elif key in [ord('+'), ord('=')]:
                speed = controller.increase_speed()
                last_command = f"Speed Increased to {speed}"

            elif key in [ord('-'), ord('_')]:
                speed = controller.decrease_speed()
                last_command = f"Speed Decreased to {speed}"

            elif key in [ord('q'), ord('Q'), 27]:  # 27 is ESC
                running = False
                last_command = "Quitting..."

            time.sleep(0.05)  # Small delay to prevent CPU spinning

    except KeyboardInterrupt:
        pass
    finally:
        controller.close()
        stdscr.clear()
        stdscr.addstr(0, 0, "Car stopped. Program ended.")
        stdscr.refresh()
        time.sleep(1)

if __name__ == '__main__':
    print("Starting Keyboard Control...")
    print("Initializing car motors...")
    time.sleep(1)

    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure you're running this on the Raspberry Pi with proper permissions.")
    finally:
        print("\nProgram ended. Car stopped.")
