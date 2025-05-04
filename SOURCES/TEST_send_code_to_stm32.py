from UTILS.send_code_to_stm32 import send_encoded_directions



# Sample directions (MAX 14)
directions = [7,1,6,2,5,3,4,4]

# Optional mode (default is -1 to skip mode command)
result = send_encoded_directions(directions, mode=7)

# Output the result like a proud parent
if result['success']:
    print("✅ Success:", result['message'])
else:
    print("❌ Failure:", result['message'])