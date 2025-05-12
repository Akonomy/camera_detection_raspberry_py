import csv
import matplotlib.pyplot as plt

LOG_FILENAME = "log.csv"

# Define a mapping from command direction to colors.
direction_colors = {
    "9": "blue",    # e.g., left
    "10": "red",    # e.g., right
    "1": "green",   # e.g., forward
    "2": "orange",  # e.g., back
    "0": "black"    # stop or undefined
}

# Lists to store log data.
timestamps = []
x_positions = []
y_positions = []
cmd_directions = []

# Read the CSV log.
with open(LOG_FILENAME, mode="r") as logfile:
    reader = csv.DictReader(logfile)
    for row in reader:
        timestamps.append(float(row["timestamp"]))
        x_positions.append(float(row["x_before"]))
        y_positions.append(float(row["y_before"]))
        # Convert direction to string for mapping
        cmd_directions.append(str(row["direction"]))

# Create the plot.
plt.figure(figsize=(10, 6))

# Plot each logged point with a color based on the command.
for t, x, y, d in zip(timestamps, x_positions, y_positions, cmd_directions):
    color = direction_colors.get(d, "black")
    plt.scatter(x, y, color=color, label=d)

plt.xlabel("X position (cm)")
plt.ylabel("Y position (cm)")
plt.title("Car Position and Command Response")
plt.grid(True)

# Create a custom legend.
import matplotlib.patches as mpatches
legend_handles = []
for d, col in direction_colors.items():
    patch = mpatches.Patch(color=col, label=f"Cmd {d}")
    legend_handles.append(patch)
plt.legend(handles=legend_handles)

plt.show()
