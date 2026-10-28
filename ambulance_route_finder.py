"""
Emergency Ambulance Route Finder using Dijkstra's Algorithm
-----------------------------------------------------------
GUI application (Python + Tkinter, no extra libraries needed).

Model
  * Junctions and hospitals are graph vertices.
  * Roads are undirected edges; weight = travel time in minutes.
  * A road can be BLOCKED (accident / flood / traffic jam) and is then ignored.

Run:        python ambulance_route_finder.py
Run tests:  python ambulance_route_finder.py --test
"""
import heapq
import math
import random
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

INF = float("inf")


def fmt(x):
    return "∞" if x == INF else f"{x:g}"


# ----------------------------------------------------------------------------
# Graph model
# ----------------------------------------------------------------------------
class Graph:
    def __init__(self):
        self.nodes = {}   # name -> {"x": int, "y": int, "kind": "junction"|"hospital"}
        self.edges = {}   # (a, b) sorted -> {"w": float, "blocked": bool}

    @staticmethod
    def key(a, b):
        return tuple(sorted((a, b)))

    def add_node(self, name, x, y, kind="junction"):
        self.nodes[name] = {"x": x, "y": y, "kind": kind}

    def add_edge(self, a, b, w):
        if a not in self.nodes or b not in self.nodes:
            raise ValueError("Both endpoints must exist.")
        if a == b:
            raise ValueError("A road cannot connect a junction to itself.")
        if w < 0:
            raise ValueError("Travel time cannot be negative (Dijkstra requires w >= 0).")
        k = self.key(a, b)
        blocked = self.edges[k]["blocked"] if k in self.edges else False
        self.edges[k] = {"w": float(w), "blocked": blocked}

    def remove_node(self, name):
        self.nodes.pop(name, None)
        for k in [k for k in self.edges if name in k]:
            del self.edges[k]

    def next_name(self, prefix):
        i = 1
        while f"{prefix}{i}" in self.nodes:
            i += 1
        return f"{prefix}{i}"


def build_sample_map():
    g = Graph()
    pts = {"J1": (80, 90), "J2": (230, 60), "J3": (400, 80), "J4": (560, 70),
           "J5": (110, 250), "J6": (270, 230), "J7": (440, 250), "J8": (610, 240),
           "J9": (150, 400), "J10": (330, 390)}
    for n, (x, y) in pts.items():
        g.add_node(n, x, y)
    g.add_node("H1", 640, 400, "hospital")
    g.add_node("H2", 50, 440, "hospital")
    g.add_node("H3", 470, 450, "hospital")
    roads = [("J1", "J2", 4), ("J2", "J3", 5), ("J3", "J4", 4), ("J1", "J5", 6),
             ("J2", "J6", 5), ("J3", "J7", 6), ("J4", "J8", 5), ("J5", "J6", 4),
             ("J6", "J7", 5), ("J7", "J8", 3), ("J5", "J9", 5), ("J6", "J10", 6),
             ("J7", "H3", 7), ("J8", "H1", 6), ("J9", "H2", 3), ("J9", "J10", 5),
             ("J10", "H3", 4), ("H3", "H1", 6)]
    for a, b, w in roads:
        g.add_edge(a, b, w)
    return g


# ----------------------------------------------------------------------------
# Dijkstra's algorithm (binary-heap version) with step recording
# ----------------------------------------------------------------------------
def dijkstra(graph, src, goals=None, record=True):
    """
    Returns dict(dist, prev, reached, path, steps).
    goals  : set of vertices; the search stops when the first goal is
             extracted from the priority queue (its distance is then final).
             goals=None computes shortest paths to every vertex.
    record : keep a snapshot of every step (used for the visualisation).
    """
    adj = {n: [] for n in graph.nodes}
    for (a, b), e in graph.edges.items():
        if not e["blocked"]:
            adj[a].append((b, e["w"]))
            adj[b].append((a, e["w"]))

    dist = {n: INF for n in graph.nodes}
    prev = {n: None for n in graph.nodes}
    visited = set()
    steps = []

    def snap(msg, current=None, relax=None, final=False):
        if record:
            steps.append({"msg": msg, "current": current, "relax": relax,
                          "visited": set(visited), "dist": dict(dist),
                          "prev": dict(prev), "final": final})

    dist[src] = 0
    pq = [(0, src)]
    snap(f"Initialise: dist[{src}] = 0, every other vertex = ∞. "
         f"Push ({src}, 0) into the priority queue.")
    reached = None
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:          # stale queue entry
            continue
        visited.add(u)
        snap(f"Extract {u} (smallest distance {fmt(d)}). Its distance is now final.", u)
        if goals and u in goals:
            reached = u
            break
        for v, w in adj[u]:
            if v in visited:
                continue
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
                snap(f"Relax {u}→{v}: {fmt(d)} + {fmt(w)} = {fmt(nd)} is better. "
                     f"Update dist[{v}] = {fmt(nd)}.", u, (u, v))
            else:
                snap(f"Check {u}→{v}: {fmt(nd)} is not better than {fmt(dist[v])}. "
                     f"No change.", u, (u, v))

    path = path_to(prev, dist, src, reached) if reached is not None else None
    if reached is not None:
        snap(f"DONE: {reached} reached with travel time {fmt(dist[reached])} min.",
             reached, final=True)
    elif goals:
        snap("DONE: queue is empty and no target was reached - NO ROUTE available.",
             None, final=True)
    else:
        snap("DONE: every reachable vertex has its final distance.", None, final=True)
    return {"dist": dist, "prev": prev, "reached": reached, "path": path,
            "steps": steps, "src": src}


def path_to(prev, dist, src, target):
    if target is None or dist[target] == INF:
        return None
    path = [target]
    while path[-1] != src:
        path.append(prev[path[-1]])
    return path[::-1]


# ----------------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------------
COL_VISITED, COL_FRONT, COL_CUR, COL_PATH = "#aed6f1", "#f9e79f", "#f5b041", "#58d68d"
HINTS = {
    "select":   "Left-click a node = START (ambulance).  Right-click a node = DESTINATION.",
    "junction": "Click empty space to add a junction.",
    "hospital": "Click empty space to add a hospital.",
    "road":     "Click two nodes to build a road between them (you will be asked for the time).",
    "block":    "Click a road to block / unblock it (accident, flood, jam).",
    "weight":   "Click a road to change its travel time (traffic).",
    "delete":   "Click a node to delete it together with its roads.",
}


class App:
    def __init__(self, root):
        self.root = root
        root.title("Emergency Ambulance Route Finder - Dijkstra's Algorithm")
        root.geometry("1210x700")
        ttk.Style().theme_use("clam")
        self.g = build_sample_map()
        self.tool = tk.StringVar(value="select")
        self.mode = tk.StringVar(value="specific")
        self.start = tk.StringVar(value="J1")
        self.dest = tk.StringVar(value="H1")
        self.speed = tk.IntVar(value=5)
        self.status = tk.StringVar(value=HINTS["select"])
        self.run, self.idx, self.auto, self.pending = None, -1, None, None
        self.build_ui()
        self.refresh_combos()
        self.redraw()

    # ---------- layout ----------
    def build_ui(self):
        left = ttk.Frame(self.root)
        left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.canvas = tk.Canvas(left, width=730, height=560, bg="#fdfefe",
                                highlightthickness=1, highlightbackground="#999")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_left)
        self.canvas.bind("<Button-3>", self.on_right)
        ttk.Label(left, textvariable=self.status, foreground="#1b4f72").pack(anchor="w", pady=4)

        right = ttk.Frame(self.root)
        right.pack(side="right", fill="y", padx=8, pady=8)

        box = ttk.LabelFrame(right, text=" 1. Dispatch ")
        box.pack(fill="x", pady=3)
        ttk.Radiobutton(box, text="Route to a chosen hospital / node", variable=self.mode,
                        value="specific", command=self.refresh_combos).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(box, text="Find NEAREST hospital automatically", variable=self.mode,
                        value="nearest", command=self.refresh_combos).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Label(box, text="Ambulance at:").grid(row=2, column=0, sticky="w", pady=2)
        self.cb_start = ttk.Combobox(box, textvariable=self.start, state="readonly", width=12)
        self.cb_start.grid(row=2, column=1, pady=2)
        ttk.Label(box, text="Destination:").grid(row=3, column=0, sticky="w", pady=2)
        self.cb_dest = ttk.Combobox(box, textvariable=self.dest, state="readonly", width=12)
        self.cb_dest.grid(row=3, column=1, pady=2)
        for cb in (self.cb_start, self.cb_dest):
            cb.bind("<<ComboboxSelected>>", lambda e: (self.reset_run(), self.redraw()))

        box2 = ttk.LabelFrame(right, text=" 2. Run algorithm ")
        box2.pack(fill="x", pady=3)
        ttk.Button(box2, text="Find Route (instant)", command=self.find_route).grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(box2, text="Start step-by-step", command=self.begin_steps).grid(row=1, column=0, sticky="ew", pady=2)
        ttk.Button(box2, text="Next step ▶", command=self.next_step).grid(row=1, column=1, sticky="ew", pady=2)
        self.btn_auto = ttk.Button(box2, text="Auto-play", command=self.toggle_auto)
        self.btn_auto.grid(row=2, column=0, sticky="ew", pady=2)
        ttk.Button(box2, text="Clear", command=lambda: (self.reset_run(), self.redraw())).grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Label(box2, text="Speed:").grid(row=3, column=0, sticky="w")
        ttk.Scale(box2, from_=1, to=10, variable=self.speed, orient="horizontal").grid(row=3, column=1, sticky="ew")
        box2.columnconfigure((0, 1), weight=1)

        box3 = ttk.LabelFrame(right, text=" 3. Edit map / traffic ")
        box3.pack(fill="x", pady=3)
        tools = [("Select (set start/dest)", "select"), ("Add junction", "junction"),
                 ("Add hospital", "hospital"), ("Add road", "road"),
                 ("Block / unblock road", "block"), ("Change road time", "weight"),
                 ("Delete node", "delete")]
        for i, (txt, val) in enumerate(tools):
            ttk.Radiobutton(box3, text=txt, variable=self.tool, value=val,
                            command=self.tool_changed).grid(row=i // 2, column=i % 2, sticky="w", padx=2)
        ttk.Button(box3, text="Reset sample map", command=self.reset_map).grid(row=4, column=0, sticky="ew", pady=2)
        ttk.Button(box3, text="Run test cases", command=self.show_tests).grid(row=4, column=1, sticky="ew", pady=2)

        self.result = tk.StringVar(value="Result will appear here.")
        ttk.Label(right, textvariable=self.result, wraplength=400, font=("Segoe UI", 10, "bold"),
                  foreground="#145a32").pack(fill="x", pady=4)

        cols = ("node", "dist", "prev", "status")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=9)
        for c, w in zip(cols, (70, 70, 70, 120)):
            self.tree.heading(c, text={"node": "Node", "dist": "Time (min)", "prev": "Previous", "status": "Status"}[c])
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="x")

        ttk.Label(right, text="Step log:").pack(anchor="w", pady=(6, 0))
        lf = ttk.Frame(right)
        lf.pack(fill="both", expand=True)
        self.log = tk.Text(lf, width=52, height=9, wrap="word", font=("Consolas", 9))
        sb = ttk.Scrollbar(lf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ---------- helpers ----------
    def tool_changed(self):
        self.pending = None
        self.status.set(HINTS[self.tool.get()])
        self.redraw()

    def refresh_combos(self):
        names = sorted(self.g.nodes, key=lambda n: (n[0], int(n[1:]) if n[1:].isdigit() else 0))
        self.cb_start["values"] = names
        self.cb_dest["values"] = names
        if self.start.get() not in self.g.nodes:
            self.start.set(names[0] if names else "")
        if self.dest.get() not in self.g.nodes:
            hosp = [n for n in names if self.g.nodes[n]["kind"] == "hospital"]
            self.dest.set(hosp[0] if hosp else (names[-1] if names else ""))
        self.cb_dest.configure(state="disabled" if self.mode.get() == "nearest" else "readonly")
        self.reset_run()
        self.redraw()

    def node_at(self, x, y):
        for n, v in self.g.nodes.items():
            if (v["x"] - x) ** 2 + (v["y"] - y) ** 2 <= 20 ** 2:
                return n
        return None

    def edge_at(self, x, y):
        best, bd = None, 9
        for (a, b) in self.g.edges:
            x1, y1, x2, y2 = self.g.nodes[a]["x"], self.g.nodes[a]["y"], self.g.nodes[b]["x"], self.g.nodes[b]["y"]
            dx, dy = x2 - x1, y2 - y1
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy or 1)))
            d = math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
            if d < bd:
                best, bd = (a, b), d
        return best

    # ---------- mouse ----------
    def on_left(self, ev):
        t, n = self.tool.get(), self.node_at(ev.x, ev.y)
        if t == "select":
            if n:
                self.start.set(n)
                self.reset_run()
        elif t in ("junction", "hospital"):
            if n is None:
                name = self.g.next_name("J" if t == "junction" else "H")
                self.g.add_node(name, ev.x, ev.y, t)
                self.refresh_combos()
        elif t == "road":
            if n is None:
                self.pending = None
            elif self.pending is None:
                self.pending = n
                self.status.set(f"Road from {n}: now click the second node.")
            elif n != self.pending:
                w = simpledialog.askfloat("Travel time", f"Travel time {self.pending} ↔ {n} (minutes):",
                                          minvalue=0, parent=self.root)
                if w is not None:
                    self.g.add_edge(self.pending, n, w)
                self.pending = None
                self.status.set(HINTS["road"])
                self.reset_run()
        elif t == "block":
            e = self.edge_at(ev.x, ev.y)
            if e:
                self.g.edges[e]["blocked"] = not self.g.edges[e]["blocked"]
                self.reset_run()
        elif t == "weight":
            e = self.edge_at(ev.x, ev.y)
            if e:
                w = simpledialog.askfloat("Travel time", f"New travel time {e[0]} ↔ {e[1]} (minutes):",
                                          minvalue=0, initialvalue=self.g.edges[e]["w"], parent=self.root)
                if w is not None:
                    self.g.edges[e]["w"] = w
                    self.reset_run()
        elif t == "delete":
            if n:
                self.g.remove_node(n)
                self.refresh_combos()
        self.redraw()

    def on_right(self, ev):
        n = self.node_at(ev.x, ev.y)
        if n and self.tool.get() == "select":
            self.dest.set(n)
            self.reset_run()
            self.redraw()

    # ---------- running the algorithm ----------
    def reset_run(self):
        self.stop_auto()
        self.run, self.idx = None, -1
        self.result.set("Result will appear here.")
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())
            self.log.delete("1.0", "end")

    def prepare_run(self):
        self.stop_auto()
        s = self.start.get()
        if s not in self.g.nodes:
            messagebox.showwarning("Missing input", "Choose where the ambulance is.")
            return False
        if self.mode.get() == "nearest":
            goals = {n for n, v in self.g.nodes.items() if v["kind"] == "hospital"}
            if not goals:
                messagebox.showwarning("No hospital", "The map has no hospital. Add one first.")
                return False
        else:
            d = self.dest.get()
            if d not in self.g.nodes:
                messagebox.showwarning("Missing input", "Choose a destination.")
                return False
            goals = {d}
        self.run = dijkstra(self.g, s, goals)
        self.idx = -1
        return True

    def find_route(self):
        if self.prepare_run():
            self.idx = len(self.run["steps"]) - 1
            self.show()

    def begin_steps(self):
        if self.prepare_run():
            self.idx = 0
            self.show()

    def next_step(self):
        if self.run is None:
            self.begin_steps()
        elif self.idx < len(self.run["steps"]) - 1:
            self.idx += 1
            self.show()

    def toggle_auto(self):
        if self.auto:
            self.stop_auto()
            return
        if self.run is None or self.idx >= len(self.run["steps"]) - 1:
            if not self.prepare_run():
                return
            self.idx = 0
            self.show()
        self.btn_auto.configure(text="Pause")
        self.tick()

    def tick(self):
        if self.run and self.idx < len(self.run["steps"]) - 1:
            self.idx += 1
            self.show()
            self.auto = self.root.after(int(1300 / max(1, self.speed.get())), self.tick)
        else:
            self.stop_auto()

    def stop_auto(self):
        if self.auto:
            self.root.after_cancel(self.auto)
        self.auto = None
        if hasattr(self, "btn_auto"):
            self.btn_auto.configure(text="Auto-play")

    # ---------- display ----------
    def cur_state(self):
        return self.run["steps"][self.idx] if self.run and self.idx >= 0 else None

    def show(self):
        self.redraw()
        st = self.cur_state()
        self.tree.delete(*self.tree.get_children())
        for n in self.g.nodes:
            if n in st["visited"]:
                s = "▶ current" if n == st["current"] else "visited (final)"
            elif st["dist"][n] < INF:
                s = "in queue"
            else:
                s = "unvisited"
            self.tree.insert("", "end", values=(n, fmt(st["dist"][n]), st["prev"][n] or "-", s))
        self.log.delete("1.0", "end")
        for i in range(self.idx + 1):
            self.log.insert("end", f"{i}. {self.run['steps'][i]['msg']}\n")
        self.log.see("end")
        if st["final"]:
            r = self.run
            if r["path"]:
                self.result.set(f"ROUTE: {' → '.join(r['path'])}\n"
                                f"Travel time: {fmt(r['dist'][r['reached']])} min   |   "
                                f"Vertices finalised: {len(st['visited'])}")
            else:
                self.result.set("NO ROUTE AVAILABLE - destination unreachable "
                                "(roads blocked or map disconnected).")
        else:
            self.result.set(f"Step {self.idx} of {len(self.run['steps']) - 1}")

    def redraw(self):
        c, g = self.canvas, self.g
        c.delete("all")
        st = self.cur_state()
        path_nodes, path_edges = set(), set()
        if st and st["final"] and self.run["path"]:
            p = self.run["path"]
            path_nodes = set(p)
            path_edges = {Graph.key(p[i], p[i + 1]) for i in range(len(p) - 1)}
        for (a, b), e in g.edges.items():
            x1, y1, x2, y2 = g.nodes[a]["x"], g.nodes[a]["y"], g.nodes[b]["x"], g.nodes[b]["y"]
            if e["blocked"]:
                c.create_line(x1, y1, x2, y2, fill="#c0392b", width=3, dash=(6, 4))
                label = f"{e['w']:g} ✖"
            elif (a, b) in path_edges:
                c.create_line(x1, y1, x2, y2, fill="#1e8449", width=7)
                label = f"{e['w']:g}"
            elif st and st["relax"] and Graph.key(*st["relax"]) == (a, b):
                c.create_line(x1, y1, x2, y2, fill="#e67e22", width=5)
                label = f"{e['w']:g}"
            else:
                c.create_line(x1, y1, x2, y2, fill="#95a5a6", width=3)
                label = f"{e['w']:g}"
            t = c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=label, font=("Segoe UI", 9, "bold"))
            r = c.create_rectangle(c.bbox(t), fill="white", outline="")
            c.tag_raise(t, r)
        for n, v in g.nodes.items():
            x, y = v["x"], v["y"]
            fill = "#ecf0f1"
            if st:
                if n in path_nodes:
                    fill = COL_PATH
                elif n == st["current"]:
                    fill = COL_CUR
                elif n in st["visited"]:
                    fill = COL_VISITED
                elif st["dist"][n] < INF:
                    fill = COL_FRONT
            outline, ow = ("#c0392b", 3) if v["kind"] == "hospital" else ("#566573", 2)
            if n == self.start.get():
                outline, ow = "#1e8449", 5
            elif n == self.dest.get() and self.mode.get() == "specific":
                outline, ow = "#8e44ad", 5
            if n == self.pending:
                outline, ow = "#2980b9", 5
            if v["kind"] == "hospital":
                c.create_rectangle(x - 19, y - 19, x + 19, y + 19, fill=fill, outline=outline, width=ow)
            else:
                c.create_oval(x - 17, y - 17, x + 17, y + 17, fill=fill, outline=outline, width=ow)
            c.create_text(x, y, text=n, font=("Segoe UI", 9, "bold"))
            if st:
                c.create_text(x, y - 30, text=fmt(st["dist"][n]), fill="#7b241c", font=("Segoe UI", 10, "bold"))
            if n == self.start.get():
                c.create_text(x, y + 30, text="AMBULANCE", fill="#1e8449", font=("Segoe UI", 8, "bold"))
            elif n == self.dest.get() and self.mode.get() == "specific":
                c.create_text(x, y + 30, text="DESTINATION", fill="#8e44ad", font=("Segoe UI", 8, "bold"))
        # legend
        items = [(COL_CUR, "current"), (COL_VISITED, "visited"), (COL_FRONT, "in queue"), (COL_PATH, "final route")]
        x = 10
        for col, txt in items:
            c.create_rectangle(x, 538, x + 14, 552, fill=col, outline="#555")
            c.create_text(x + 20, 545, text=txt, anchor="w", font=("Segoe UI", 9))
            x += 105
        c.create_text(x + 10, 545, text="▭ hospital   ○ junction   number above node = shortest time so far (min)",
                      anchor="w", font=("Segoe UI", 9), fill="#555")

    def reset_map(self):
        self.g = build_sample_map()
        self.start.set("J1")
        self.dest.set("H1")
        self.pending = None
        self.refresh_combos()

    def show_tests(self):
        results = run_tests()
        w = tk.Toplevel(self.root)
        w.title("Test results")
        w.geometry("760x520")
        txt = tk.Text(w, font=("Consolas", 10), wrap="word")
        txt.pack(fill="both", expand=True)
        txt.tag_config("ok", foreground="#1e8449")
        txt.tag_config("bad", foreground="#c0392b")
        passed = sum(1 for r in results if r[1])
        for i, (name, ok, detail) in enumerate(results, 1):
            txt.insert("end", f"[{'PASS' if ok else 'FAIL'}] T{i:02d} {name}\n", "ok" if ok else "bad")
            if detail:
                txt.insert("end", f"        {detail}\n")
        txt.insert("end", f"\n{passed}/{len(results)} tests passed.\n", "ok" if passed == len(results) else "bad")


# ----------------------------------------------------------------------------
# Test suite (normal, boundary and randomised cross-check against Bellman-Ford)
# ----------------------------------------------------------------------------
def _mk(names, edges, hospitals=()):
    g = Graph()
    for i, n in enumerate(names):
        g.add_node(n, 50 + 40 * i, 50, "hospital" if n in hospitals else "junction")
    for a, b, w in edges:
        g.add_edge(a, b, w)
    return g


def _bellman_ford(g, s):
    d = {n: INF for n in g.nodes}
    d[s] = 0
    for _ in range(max(1, len(g.nodes) - 1)):
        for (a, b), e in g.edges.items():
            if e["blocked"]:
                continue
            if d[a] + e["w"] < d[b]:
                d[b] = d[a] + e["w"]
            if d[b] + e["w"] < d[a]:
                d[a] = d[b] + e["w"]
    return d


def run_tests():
    res = []

    def check(name, cond, detail=""):
        res.append((name, bool(cond), detail))

    g = build_sample_map()
    r = dijkstra(g, "J1", {"H1"})
    check("Sample map J1 -> H1", r["dist"]["H1"] == 23 and r["path"] == ["J1", "J2", "J6", "J7", "J8", "H1"],
          f"path={r['path']} time={r['dist']['H1']}")
    r = dijkstra(g, "J1", {"H1", "H2", "H3"})
    check("Nearest hospital from J1 is H2 (14 min)", r["reached"] == "H2" and r["dist"]["H2"] == 14,
          f"reached={r['reached']} time={r['dist']['H2']}")
    g.edges[Graph.key("J9", "H2")]["blocked"] = True
    r = dijkstra(g, "J1", {"H1", "H2", "H3"})
    check("Blocking J9-H2 changes nearest hospital to H3", r["reached"] == "H3",
          f"reached={r['reached']} time={fmt(r['dist'][r['reached']])}")

    g = _mk(["A"], [])
    r = dijkstra(g, "A", {"A"})
    check("Boundary: single-vertex graph", r["dist"]["A"] == 0 and r["path"] == ["A"])
    g = _mk(["A", "B"], [("A", "B", 4)])
    r = dijkstra(g, "A", {"A"})
    check("Boundary: source == destination", r["dist"]["A"] == 0 and r["path"] == ["A"])
    g = _mk(["A", "B"], [])
    r = dijkstra(g, "A", {"B"})
    check("Boundary: disconnected graph -> no route", r["path"] is None and r["dist"]["B"] == INF)
    g = _mk(["A", "B", "C"], [("A", "B", 1), ("B", "C", 1), ("A", "C", 5)])
    d1 = dijkstra(g, "A", {"C"})["dist"]["C"]
    g.edges[Graph.key("A", "B")]["blocked"] = True
    d2 = dijkstra(g, "A", {"C"})["dist"]["C"]
    check("Blocked road forces detour (2 -> 5 min)", d1 == 2 and d2 == 5, f"before={d1} after={d2}")
    g.edges[Graph.key("A", "C")]["blocked"] = True
    check("All roads from source blocked -> no route", dijkstra(g, "A", {"C"})["path"] is None)
    g = _mk(["A", "B", "C"], [("A", "B", 0), ("B", "C", 3)])
    check("Zero-weight road", dijkstra(g, "A", {"C"})["dist"]["C"] == 3)
    g = _mk(["A", "B", "C", "D"], [("A", "B", 1), ("B", "D", 1), ("A", "C", 1), ("C", "D", 1)])
    check("Equal-cost alternative routes (tie)", dijkstra(g, "A", {"D"})["dist"]["D"] == 2)
    g = _mk(["H1", "A", "B"], [("A", "B", 2)], hospitals={"H1"})
    r = dijkstra(g, "H1", {"H1"})
    check("Ambulance already at a hospital -> 0 min", r["dist"]["H1"] == 0)
    g = _mk(["A", "H1", "H2"], [("A", "H2", 9)], hospitals={"H1", "H2"})
    r = dijkstra(g, "A", {"H1", "H2"})
    check("Unreachable hospital ignored, reachable one chosen", r["reached"] == "H2")
    try:
        _mk(["A", "B"], [("A", "B", -1)])
        check("Negative travel time rejected", False)
    except ValueError:
        check("Negative travel time rejected", True)
    try:
        _mk(["A"], [("A", "A", 1)])
        check("Self-loop road rejected", False)
    except ValueError:
        check("Self-loop road rejected", True)
    n = 2000
    g = _mk([f"N{i}" for i in range(n)], [(f"N{i}", f"N{i + 1}", 1) for i in range(n - 1)])
    check(f"Large input: chain of {n} vertices", dijkstra(g, "N0", None, record=False)["dist"][f"N{n - 1}"] == n - 1)

    rnd, bad = random.Random(42), 0
    for _ in range(300):
        k = rnd.randint(2, 10)
        names = [f"V{i}" for i in range(k)]
        g = _mk(names, [])
        for i in range(k):
            for j in range(i + 1, k):
                if rnd.random() < 0.35:
                    g.add_edge(names[i], names[j], rnd.randint(0, 9))
                    g.edges[Graph.key(names[i], names[j])]["blocked"] = rnd.random() < 0.1
        s = rnd.choice(names)
        if dijkstra(g, s, None, record=False)["dist"] != _bellman_ford(g, s):
            bad += 1
    check("300 random graphs match Bellman-Ford", bad == 0, f"mismatches={bad}")
    return res


if __name__ == "__main__":
    if "--test" in sys.argv:
        out = run_tests()
        for i, (name, ok, detail) in enumerate(out, 1):
            print(f"[{'PASS' if ok else 'FAIL'}] T{i:02d} {name} {detail}")
        print(f"{sum(o[1] for o in out)}/{len(out)} passed")
    else:
        root = tk.Tk()
        App(root)
        root.mainloop()
