from WEB.robot_api_client import RobotAPIClient, fetch_tasks_module, check_container_module


client = RobotAPIClient()
tasks = client.fetch_tasks()
print(tasks)


first= client.fetch_first_task()

print(first)
container_info = client.check_container('SGsYp36')
print(container_info)
# Și alte metode disponibile...


