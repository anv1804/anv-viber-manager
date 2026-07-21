"""
utils/svg_canvas.py — Lightweight Vector SVG drawing widget using Tkinter Canvas.
Allows native SVG rendering without installing external modules like cairosvg/tksvg.
Works seamlessly on both Windows and Linux.
"""
import os
import re
import xml.etree.ElementTree as ET
import tkinter as tk


class SVGCanvas(tk.Canvas):
    """
    A Tkinter Canvas that parses and renders flat SVG paths.
    Fits the icon content perfectly to the widget dimensions.
    """
    def __init__(self, parent, svg_path: str, size: int = 16, color: str = "#F4F4F5", bg: str = "#27272A", cursor: str = "hand2", **kwargs):
        super().__init__(parent, width=size, height=size, bg=bg, bd=0, highlightthickness=0, cursor=cursor, **kwargs)
        self.svg_path = svg_path
        self.size = size
        self.color = color
        self.bg = bg
        
        self.paths = []
        self._parse_svg()
        self.draw()

    def _parse_svg(self):
        if not os.path.exists(self.svg_path):
            return
        try:
            tree = ET.parse(self.svg_path)
            root = tree.getroot()
            
            # Find all path elements in SVG
            namespaces = {'svg': 'http://www.w3.org/2000/svg'}
            # Handle default namespace or no namespace
            prefix = ""
            if "}" in root.tag:
                prefix = root.tag.split("}")[0] + "}"
                
            for path_node in root.findall(f'.//{prefix}path'):
                d = path_node.get('d')
                if d:
                    self.paths.append(d)
        except Exception as e:
            print(f"Error parsing SVG {self.svg_path}: {e}")

    def draw(self):
        self.delete("all")
        if not self.paths:
            return

        scale = self.size / 24.0  # Assumes standard 24x24 viewBox

        for d in self.paths:
            # Parse tokens
            tokens = []
            curr = ""
            for char in d:
                if char in " \t\r\n,":
                    if curr:
                        tokens.append(curr); curr = ""
                elif char in "MmLlHhVvCcZzSsQqTtAaDdFf":
                    if curr:
                        tokens.append(curr); curr = ""
                    tokens.append(char)
                elif char == "-":
                    if curr:
                        tokens.append(curr)
                    curr = "-"
                elif char == ".":
                    if "." in curr:
                        tokens.append(curr); curr = "."
                    else:
                        curr += "."
                elif char.isdigit():
                    curr += char
                else:
                    pass
            if curr:
                tokens.append(curr)

            # Convert numeric tokens to float
            commands = []
            for t in tokens:
                if t in "MmLlHhVvCcZzSsQqTtAa":
                    commands.append(t)
                else:
                    try:
                        commands.append(float(t))
                    except ValueError:
                        pass

            # Drawing Loop
            i = 0
            curr_x, curr_y = 0.0, 0.0
            poly_points = []
            last_cmd = ""

            while i < len(commands):
                item = commands[i]
                if isinstance(item, str):
                    cmd = item
                    i += 1
                else:
                    # Repeat previous command if no explicit command character
                    cmd = last_cmd
                
                last_cmd = cmd

                if cmd in ('M', 'm'):
                    x, y = commands[i] * scale, commands[i+1] * scale
                    if cmd == 'm':
                        x += curr_x; y += curr_y
                    curr_x, curr_y = x, y
                    if len(poly_points) >= 4:
                        self.create_line(poly_points, fill=self.color, width=1.5, capstyle=tk.ROUND, joinstyle=tk.ROUND)
                    poly_points = [curr_x, curr_y]
                    i += 2
                elif cmd in ('L', 'l'):
                    x, y = commands[i] * scale, commands[i+1] * scale
                    if cmd == 'l':
                        x += curr_x; y += curr_y
                    curr_x, curr_y = x, y
                    poly_points.extend([curr_x, curr_y])
                    i += 2
                elif cmd in ('H', 'h'):
                    x = commands[i] * scale
                    if cmd == 'h':
                        x += curr_x
                    curr_x = x
                    poly_points.extend([curr_x, curr_y])
                    i += 1
                elif cmd in ('V', 'v'):
                    y = commands[i] * scale
                    if cmd == 'v':
                        y += curr_y
                    curr_y = y
                    poly_points.extend([curr_x, curr_y])
                    i += 1
                elif cmd in ('C', 'c'):
                    # Cubic Bezier (6 parameters)
                    x3, y3 = commands[i+4] * scale, commands[i+5] * scale
                    if cmd == 'c':
                        x3 += curr_x; y3 += curr_y
                    curr_x, curr_y = x3, y3
                    poly_points.extend([curr_x, curr_y])
                    i += 6
                elif cmd in ('Z', 'z'):
                    if len(poly_points) >= 4:
                        poly_points.extend([poly_points[0], poly_points[1]])
                        self.create_line(poly_points, fill=self.color, width=1.5, capstyle=tk.ROUND, joinstyle=tk.ROUND)
                    poly_points = []
                    # No parameters to consume, so i is not incremented further
                else:
                    # Ignore unsupported commands
                    i += 1

            if len(poly_points) >= 4:
                self.create_line(poly_points, fill=self.color, width=1.5, capstyle=tk.ROUND, joinstyle=tk.ROUND)


class SVGButton(SVGCanvas):
    """
    An interactive Button powered by custom SVG rendering.
    Supports hover states and click events.
    """
    def __init__(self, parent, svg_path: str, size: int = 16, color: str = "#F4F4F5", bg: str = "#27272A", hover_bg: str = "#3F3F46", command=None, **kwargs):
        super().__init__(parent, svg_path=svg_path, size=size, color=color, bg=bg, **kwargs)
        self.hover_bg = hover_bg
        self.command = command
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, _):
        self.config(bg=self.hover_bg)

    def _on_leave(self, _):
        self.config(bg=self.bg)

    def _on_click(self, _):
        if self.command:
            self.command()
