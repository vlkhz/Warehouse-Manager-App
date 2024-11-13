import pandas as pd
import random
import time
import redis
import json
import math


csv_file = 'data.csv'

# Set up Redis connection
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Storage movement goals
goal_points = {}

# Function to generate random initial coordinates
def generate_initial_coordinates(num_points):
    data = {
        'name': [f'BOT_{i+1}' for i in range(num_points)],
        'x': [random.uniform(1, 5) for _ in range(num_points)],
        'y': [random.uniform(1, 5) for _ in range(num_points)],
        'charge': [random.uniform(80, 100) for _ in range(num_points)]
    }
    return pd.DataFrame(data)

# Function to update all point positions towards their goals
def update_positions(df, speed=0.2):
    points_to_remove = []
    for point_name, goal in list(goal_points.items()):
        goal_x, goal_y = goal['goal_x'], goal['goal_y']
        
        # Find the index of the point to update
        idx = df[df['name'] == point_name].index
        if not idx.empty:
            idx = idx[0]

            # Get current coordinates
            current_x = df.at[idx, 'x']
            current_y = df.at[idx, 'y']

            # Calculate the distance to the goal
            distance = math.sqrt((goal_x - current_x) ** 2 + (goal_y - current_y) ** 2)

            # If at the goal, mark the point for removal
            if distance <= speed:
                df.at[idx, 'x'] = goal_x
                df.at[idx, 'y'] = goal_y
                print(f"{point_name} reached the goal at ({goal_x:.2f}, {goal_y:.2f})")
                points_to_remove.append(point_name)  # Mark for removal
            else:
                # Calculate the direction
                direction_x = (goal_x - current_x) / distance
                direction_y = (goal_y - current_y) / distance

                # Update the coordinates based on the speed
                df.at[idx, 'x'] += direction_x * speed
                df.at[idx, 'y'] += direction_y * speed

    # Remove points that have reached their goal
    for point_name in points_to_remove:
        del goal_points[point_name]
        # Remove the point from moving_points in Redis
        redis_client.hdel('moving_points', point_name)

    return df

# Number of points
num_points = 25

# Generate initial coordinates and save to CSV
coordinates_df = generate_initial_coordinates(num_points)
coordinates_df.to_csv(csv_file, index=False)

# Loop to update the coordinates periodically
while True:
    try:
        # Read current data from CSV
        coordinates_df = pd.read_csv(csv_file)

        # Process tasks from Redis queue
        while redis_client.llen('task_queue') > 0:
            task_data = redis_client.lpop('task_queue')
            task = json.loads(task_data)

            point_name = task['name']
            goal_x = task['goal_x']
            goal_y = task['goal_y']

            # Add or update the goal for the point
            goal_points[point_name] = {'goal_x': goal_x, 'goal_y': goal_y}
            print(f"New task assigned: Move {point_name} to ({goal_x}, {goal_y})")

            # Mark the point as moving in Redis
            redis_client.hset('moving_points', point_name, 1)

        # Update positions for all points towards their goals
        coordinates_df = update_positions(coordinates_df, speed=0.1)

        # Save updated coordinates back to CSV
        coordinates_df.to_csv(csv_file, index=False)

    except Exception as e:
        print(f"Error updating coordinates: {e}")

    time.sleep(0.1)
