# Emergency Ambulance Route Finder Using Dijkstra's Algorithm

An interactive graphical application designed to find the shortest and fastest emergency route using **Dijkstra’s Shortest Path Algorithm**. Built with map-editing tools, step-by-step visual traversal, and priority queue analytics.

---

## Application Screenshot

![Emergency Ambulance Route Finder GUI](gui-main.png)

---

## Key Features

* **Interactive Map Editor:** Add/delete junctions and hospitals, create or block roads, and modify transit times dynamically.
* **Smart Dispatch Panel:** Choose custom ambulance start locations and destination hospitals or find the nearest hospital automatically.
* **Step-by-Step Traversal Visualizer:** Watch Dijkstra's algorithm explore nodes using a priority queue with adjustable animation speed.
* **Live Distance & Path Table:** Real-time logging of visited nodes, shortest time metrics, and predecessor pointers.
* **Built-in Test Suite:** Automated test cases to verify algorithm correctness under various traffic and roadblock conditions.

---

## Complexity Analysis

* **Time Complexity:** $O((V + E) \log V)$ 
  * *Where $V$ is the number of road junctions/hospitals (vertices) and $E$ is the connecting roads (edges).* Utilizing a min-priority queue ensures efficient edge relaxation.
* **Space Complexity:** $O(V + E)$ 
  * *Required for storing the graph adjacency list, distance/cost tracking tables, priority queue, and parent pointers for final path reconstruction.*

---

## How to Run Locally

1. Clone or download this repository to your local machine.
2. Run the application script in your Python environment (or open the relevant execution file).
3. Interact with the GUI to dispatch ambulances and test routes!

