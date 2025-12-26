import board
import busio
import time  # Often useful for delays or debugging

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC
from kmk.scanners import DiodeOrientation
from kmk.modules.macros import Macros, Press, Release, Sequence
from kmk.extensions.display import Display, TextEntry
from kmk.extensions.LED import LED, AnimationModes
from kmk.extensions.display.ssd1306 import SSD1306

# --- Pin Definitions ---
# Keyboard Matrix
COL0 = board.GP0
COL1 = board.GP1
COL2 = board.GP2
ROW0 = board.GP7
ROW1 = board.GP8
ROW2 = board.GP9

# LED
# IMPORTANT: Ensure this is the correct pin for your status LED
LED_PIN = board.GP10

# I2C Pins for Display
# User specified D4 (SDA) and D5 (SCL)
# On Pico/many boards: D4 = GP4, D5 = GP5
I2C_SCL_PIN = board.GP5  # D5 is usually GP5 (SCL)
I2C_SDA_PIN = board.GP4  # D4 is usually GP4 (SDA)

# --- I2C Setup ---
# Ensure the bus corresponds to the SCL/SDA pins chosen
bus = None
try:
    # Attempt to use board.I2C() if available (preferred, uses board defaults)
    # Check if the default pins match your configuration
    if hasattr(board, 'I2C') and board.SCL == I2C_SCL_PIN and board.SDA == I2C_SDA_PIN:
         print("Using board.I2C()")
         bus = board.I2C()
    else:
        # Fallback to busio.I2C specifying pins manually
        print(f"Using busio.I2C(scl={I2C_SCL_PIN}, sda={I2C_SDA_PIN})")
        bus = busio.I2C(scl=I2C_SCL_PIN, sda=I2C_SDA_PIN)
except ValueError as e:
    print(f"Error initializing I2C: Pins {I2C_SCL_PIN} or {I2C_SDA_PIN} might already be in use.")
    print(f"Error: {e}")
except RuntimeError as e:
    print(f"Error initializing I2C. Check pins ({I2C_SCL_PIN}, {I2C_SDA_PIN}) and connections.")
    print(f"Ensure display is powered and correctly wired.")
    print(f"Error: {e}")
except Exception as e:
    print(f"An unexpected error occurred during I2C setup: {e}")


# --- SSD1306 Driver Setup ---
driver = None
if bus:
    # Attempt to scan for the device first (optional but good for debugging)
    # while not bus.try_lock():
    #     pass
    # try:
    #     print("Scanning I2C bus...")
    #     addresses = bus.scan()
    #     print("Found I2C devices at:", [hex(address) for address in addresses])
    # finally:
    #     bus.unlock()

    # Now initialize the driver
    try:
        # Common address for SSD1306 is 0x3C, but can sometimes be 0x3D
        DEVICE_ADDRESS = 0x3C
        driver = SSD1306(i2c=bus, device_address=DEVICE_ADDRESS)
        print(f"SSD1306 Driver initialized successfully at address {hex(DEVICE_ADDRESS)}")
    except (ValueError, OSError) as e:
        print(f"Error initializing SSD1306 display. Check address ({hex(DEVICE_ADDRESS)}) and connection.")
        print(f"Ensure display is powered and correctly wired to SCL={I2C_SCL_PIN}, SDA={I2C_SDA_PIN}.")
        print(f"Error: {e}")
        driver = None # Ensure driver is None if init fails
    except Exception as e:
        print(f"An unexpected error occurred during SSD1306 setup: {e}")
        driver = None
else:
    print("I2C bus not available. Skipping display setup.")


# --- Display Extension Setup ---
display_ext = None # Use a different variable name to avoid potential conflicts
if driver:
    try:
        display_ext = Display(
            display=driver,
            width=128,
            height=64,
            flip_x=False, # Adjust if display is mirrored horizontally
            flip_y=False, # Adjust if display is mirrored vertically
            dim_time=10,  # Seconds before dimming
            dim_target=0.2, # Dim brightness level (20%)
            off_time=60,  # Seconds before turning off (1 minute)
            brightness=0.8, # Initial brightness (80%)
            brightness_step=0.1, # Step for brightness adjustment keys (if added)
            fade_time=1, # Seconds for fade effect
        )
        # Use anchor_point="TL" (Top Left) which is often the default
        # Or use "MC" (Middle Center) with x=64 for horizontal centering
        display_ext.entries = [
                TextEntry(text='KMK Macropad!', x=0, y=0, scale=1, anchor_point="TL"), # Top Left anchor
                TextEntry(text='Ready!',       x=0, y=12, scale=1, anchor_point="TL"), # Top Left anchor below first line
                # Example centered: TextEntry(text='Centered', x=64, y=32, anchor_point="MC"),
        ]
        print("Display Extension configured.")
    except Exception as e:
        print(f"Error configuring Display Extension: {e}")
        display_ext = None
else:
    print("Display driver not initialized. Skipping Display Extension setup.")

# --- Keyboard Base ---
keyboard = KMKKeyboard()
print("KMKKeyboard object created.")

# --- Modules ---
macros = Macros()
keyboard.modules.append(macros)
print("Macros module added.")

# --- Extensions ---
# Append display only if it was initialized successfully
if display_ext:
    keyboard.extensions.append(display_ext)
    print("Display Extension added to keyboard.")

# Append LED extension
try:
    led = LED(
        led_pins=[LED_PIN], # Use a list or tuple: (LED_PIN,)
        brightness=50, # 0-100
        animation_mode=AnimationModes.BREATHING, # Or STATIC, BREATHING_RAINBOW, RAINBOW_CYCLE, etc.
        # animation_speed=1, # Adjust speed if needed
        # val=100 # For STATIC mode brightness (alternative to brightness)
    )
    keyboard.extensions.append(led)
    print("LED Extension added to keyboard.")
except NameError:
    print(f"LED_PIN ({LED_PIN}) not defined correctly, skipping LED extension.")
except ValueError as e:
    print(f"Error initializing LED Extension: Pin {LED_PIN} might not be valid or usable for PWM.")
    print(f"Error: {e}")
except Exception as e:
    print(f"Error initializing LED extension: {e}")

# --- Keyboard Matrix Configuration ---
keyboard.col_pins = (COL0, COL1, COL2)
keyboard.row_pins = (ROW0, ROW1, ROW2)
# Double check this based on your PCB traces or handwiring:
# COL2ROW means diodes are placed in series with columns, pointing towards rows.
# ROW2COL means diodes are placed in series with rows, pointing towards columns.
keyboard.diode_orientation = DiodeOrientation.COL2ROW
print("Keyboard matrix pins and diode orientation configured.")

# --- Macro Definitions ---
# Use sequence of KC codes for macros
# Assumes standard US QWERTY layout for symbols like ':'
# If : is not Shift+Semicolon on your OS layout, adjust accordingly.
SAVE = KC.MACRO(
    KC.LSHIFT(KC.SCOLON), # Press Shift + Semicolon for Colon (:)
    KC.W,
    KC.ENTER,
    description=":w<Enter>" # Optional description for display/debug
)
QUIT = KC.MACRO(
    KC.LSHIFT(KC.SCOLON), # Press Shift + Semicolon for Colon (:)
    KC.W,
    KC.Q,
    KC.ENTER,
    description=":wq<Enter>" # Optional description
)
print("Macros defined: SAVE, QUIT")

# --- Keymap Definition ---
# Layer 0
keyboard.keymap = [
    [ KC.N1,   KC.N2,   KC.N3   ], # Example: Numbers 1, 2, 3
    [ KC.N4,   KC.N5,   KC.N6   ], # Example: Numbers 4, 5, 6
    [ SAVE,    KC.N0,   QUIT    ], # Example: Macro, Number 0, Macro
]
print("Keymap defined.")

# --- Main Loop ---
if __name__ == '__main__':
    print("Starting KMK keyboard main loop...")
    try:
        keyboard.go()
    except Exception as e:
        print("-------------------------------------")
        print("FATAL ERROR in keyboard.go():")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")
        print("-------------------------------------")
        # Optional: Add code for safe mode or reset if desired
        # import supervisor
        # import microcontroller
        # print("Attempting to reload...")
        # time.sleep(5)
        # supervisor.reload()
        # Or:
        # microcontroller.reset()
