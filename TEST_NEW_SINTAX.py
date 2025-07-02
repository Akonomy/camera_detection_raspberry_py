
import random
import time
# State tracker
current_state = 0




# === Dummy Random Case Test ===
def generate_random_number():
    return random.randint(0, 5)

def handle_random_case():
    while True:
        num = generate_random_number()
        match num:
            case 0:
                print("Case 0: Robot just blinked at you.")
            case 1:
                print("Case 1: Servo did a little wiggle.")
            case 2:
                print("Case 2: Box adjusted itself mysteriously.")
            case 3:
                print("Case 3: The robot whispered goodbye.")
                break
            case 4:
                print("Case 4: Camera thinks it's a toaster.")
            case 5:
                print("Case 5: Voltage readings from another dimension.")
            case _:
                print("Unexpected case. System panic?")
        time.sleep(1)

# Run the dummy test
if __name__ == "__main__":
    handle_random_case()
