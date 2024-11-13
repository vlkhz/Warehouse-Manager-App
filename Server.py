from flask import Flask, render_template_string, jsonify, request
import threading
import pandas as pd
import time
import redis
import json
import math

app = Flask(__name__)

# Set up Redis connection
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manager App</title>
    <style>
        body {
            background-color: #101010;
            color: white;
        }
        #canvas-container {
            display: flex;
            align-items: center;
        }
        #point-canvas {
            width: 1000px;
            height: 500px;
            border: 2px solid white;
        }
        #buttons-container {
            margin-left: 20px;
        }
    </style>
    <script>
        let selectedPoint = null;

        function drawPoints(points) {
            const canvas = document.getElementById('point-canvas');
            const ctx = canvas.getContext('2d');
            const width = canvas.width;
            const height = canvas.height;

            // Clear the canvas
            ctx.clearRect(0, 0, width, height);

            // Draw all points from the list
            points.forEach((point, index) => {
                const [x, y, name] = point;
                if (selectedPoint === index) {
                    ctx.fillStyle = 'green';  // Selected point color
                } else {
                    ctx.fillStyle = 'red';  // Default point color
                }
                ctx.fillRect(x * (width / 20), y * (height / 10), 10, 10);
                ctx.fillStyle = 'white';
                ctx.fillText(name, x * (width / 20) + 15, y * (height / 10) + 5); // Draw small rectangles as points
            });

            // Update selected point information in the sidebar
            if (selectedPoint !== null) {
                const selected = points[selectedPoint];
                document.getElementById('point-name').innerText = 'Name: ' + selected[2];
                document.getElementById('point-x').innerText = 'X: ' + selected[0].toFixed(2);
                document.getElementById('point-y').innerText = 'Y: ' + selected[1].toFixed(2);
                document.getElementById('point-charge').innerText = 'Charge: ' + selected[3].toFixed(2) + '%';
            } else {
                document.getElementById('point-name').innerText = 'Name: None';
                document.getElementById('point-x').innerText = 'X: None';
                document.getElementById('point-y').innerText = 'Y: None';
                document.getElementById('point-charge').innerText = 'Charge: None';
            }
        }

        function handlePointClick(event) {
            const canvas = document.getElementById('point-canvas');
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;

            const mouseX = (event.clientX - rect.left) * scaleX;
            const mouseY = (event.clientY - rect.top) * scaleY;

            const width = canvas.width;
            const height = canvas.height;

            // Determine which point was clicked
            currentPoints.forEach((point, index) => {
                const [x, y] = point;
                const pointX = x * (width / 20);
                const pointY = y * (height / 10);

                // Check if the mouse click is within the bounds of the point
                if (mouseX >= pointX && mouseX <= pointX + 10 &&
                    mouseY >= pointY && mouseY <= pointY + 10) {
                    // If the point is already selected, unselect it
                    if (selectedPoint === index) {
                        selectedPoint = null;
                    } else {
                        // Update the selected point index
                        selectedPoint = index;
                    }
                    drawPoints(currentPoints);
                }
            });
        }


        function handleClickOnCanvas(event) {
            if (selectedPoint !== null) {
                const canvas = document.getElementById('point-canvas');
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;

                const goalX = (event.clientX - rect.left) * scaleX;
                const goalY = (event.clientY - rect.top) * scaleY;

                const selectedPointData = currentPoints[selectedPoint];
                const pointName = selectedPointData[2];

                fetch('/assign_task', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        'name': pointName,
                        'goal_x': goalX / (canvas.width / 20),
                        'goal_y': goalY / (canvas.height / 10)
                    })
                })
                .catch(error => {
                    console.error('Error:', error);
                });
            } else {
                // If no point is selected, assign task to the nearest available point
                const canvas = document.getElementById('point-canvas');
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;

                const goalX = (event.clientX - rect.left) * scaleX;
                const goalY = (event.clientY - rect.top) * scaleY;

                fetch('/assign_nearest_task', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        'goal_x': goalX / (canvas.width / 20),
                        'goal_y': goalY / (canvas.height / 10)
                    })
                })
                .catch(error => {
                    console.error('Error:', error);
                });
            }
        }

        let currentPoints = [];

        function updateCanvas() {
            fetch('/get_coordinates')
            .then(response => response.json())
            .then(data => {
                currentPoints = data.points;
                drawPoints(currentPoints);
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }

        window.onload = function() {
            const canvas = document.getElementById('point-canvas');
            canvas.addEventListener('click', handlePointClick);  // Add event listener for selecting a point
            canvas.addEventListener('dblclick', handleClickOnCanvas); // Add event listener for double-click to set goal
            setInterval(updateCanvas, 100); // Update every 0.1 seconds
        }
        
        
    </script>
</head>
<body>
    <div id="canvas-container">
    <canvas id="point-canvas" width="1000" height="500"></canvas>
    <div id="point-info" style="margin-left: 20px; color: white;">
        <p id="point-name">Name: None</p>
        <p id="point-x">X: None</p>
        <p id="point-y">Y: None</p>
        <p id="point-charge">Charge: None</p>
        <button onclick="handleButtonClick(1)">Stop</button>
    </div>
</div>
</div>
</body>
</html>
"""

# Home route
@app.route('/')
def home():
    return render_template_string(html_template)

# Route for Button action
@app.route('/button1', methods=['POST'])
def button1():
    return '', 204


# Route to provide the current coordinates of all points
@app.route('/get_coordinates', methods=['GET'])
def get_coordinates():
    return jsonify({'points': current_points_data})

# Route to assign a task
@app.route('/assign_task', methods=['POST'])
def assign_task():
    data = request.get_json()
    task = json.dumps(data)
    redis_client.rpush('task_queue', task)  # Push the task to the Redis list
    return '', 204

# Route to assign the nearest idle point
@app.route('/assign_nearest_task', methods=['POST'])
def assign_nearest_task():
    data = request.get_json()
    goal_x = data['goal_x']
    goal_y = data['goal_y']

    # Find the nearest point that is not moving
    min_distance = float('inf')
    nearest_point = None

    for point in current_points_data:
        point_name, x, y = point[2], point[0], point[1]
        is_moving = redis_client.hget('moving_points', point_name)

        # Only consider points that are not moving
        if not is_moving:
            distance = math.sqrt((goal_x - x) ** 2 + (goal_y - y) ** 2)
            if distance < min_distance:
                min_distance = distance
                nearest_point = point_name

    # Assign task to the nearest point if one was found
    if nearest_point:
        task = {
            'name': nearest_point,
            'goal_x': goal_x,
            'goal_y': goal_y
        }
        redis_client.rpush('task_queue', json.dumps(task))  # Push the task to the Redis list
        return '', 204
    else:
        return "No available points to assign the task."

# Shared variable for coordinates
current_points_data = []

# Function to read from CSV periodically and update current_points_data
def read_csv_periodically():
    global current_points_data
    while True:
        try:
            # Read the CSV file
            df = pd.read_csv('data.csv')
            
            # Update the shared variable with the new data
            current_points_data = df[['x', 'y', 'name', 'charge']].values.tolist()
        
        except Exception as e:
            print(f"Error reading CSV: {e}")
        
        time.sleep(0.1)

# Start the CSV reader thread
csv_thread = threading.Thread(target=read_csv_periodically)
csv_thread.daemon = True
csv_thread.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
