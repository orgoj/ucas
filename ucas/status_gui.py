"""
KISS GUI for live UCAS status.
Shows running teams/agents and allows quick actions.
"""

import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from . import project
from . import team


_REFRESH_MS = 5000


def _find_project_root(path_str: str) -> Optional[Path]:
    try:
        path = Path(path_str).expanduser().resolve()
    except Exception:
        return None
    root = path
    while root != root.parent:
        if (root / ".ucas").exists():
            return root
        root = root.parent
    return None


def _get_running_tree() -> Dict[str, Any]:
    panes = team._get_tmux_sessions()
    by_project: Dict[Path, Dict[str, List[Dict[str, str]]]] = {}

    for pane in panes:
        project_root = _find_project_root(pane.get("path", ""))
        if not project_root:
            continue
        by_project.setdefault(project_root, {})
        by_project[project_root].setdefault(pane["session"], [])
        by_project[project_root][pane["session"]].append(pane)

    return by_project


def _open_terminal(path: Path) -> None:
    if not project.open_terminal_in_path(path):
        messagebox.showerror("Terminal", "Failed to open terminal.")


def _attach_tmux(session: str, window: str) -> None:
    term_cmd = project.get_terminal_command()
    if not term_cmd:
        messagebox.showerror("Terminal", "No terminal found. Install xdg-terminal or x-terminal-emulator.")
        return

    cmd = f"tmux select-window -t {session}:{window} && tmux attach -t {session}"
    try:
        if term_cmd == "xdg-terminal":
            subprocess.Popen([term_cmd, "--", "bash", "-lc", cmd])
        else:
            subprocess.Popen([term_cmd, "-e", "bash", "-lc", cmd])
    except Exception as e:
        messagebox.showerror("Terminal", f"Failed to attach tmux: {e}")


def run_status_gui(refresh_ms: Optional[int] = None) -> None:
    root = tk.Tk()
    root.title("UCAS Status")
    root.geometry("900x600")

    header = ttk.Frame(root, padding=8)
    header.pack(fill="x")

    title = ttk.Label(header, text="UCAS Status", font=("TkDefaultFont", 14, "bold"))
    title.pack(side="left")

    controls = ttk.Frame(header)
    controls.pack(side="right")

    refresh_btn = ttk.Button(controls, text="Refresh")
    refresh_btn.pack(side="right", padx=(8, 0))

    auto_var = tk.BooleanVar(value=bool(refresh_ms and refresh_ms > 0))
    auto_check = ttk.Checkbutton(controls, text="Auto refresh", variable=auto_var)
    auto_check.pack(side="right", padx=(8, 0))

    interval_var = tk.StringVar(value=str((refresh_ms or _REFRESH_MS) // 1000))
    interval_entry = ttk.Entry(controls, width=5, textvariable=interval_var)
    interval_entry.pack(side="right")
    interval_label = ttk.Label(controls, text="sec")
    interval_label.pack(side="right", padx=(4, 0))

    tree = ttk.Treeview(root, columns=("status", "idle", "pid", "path"), show="tree headings")
    tree.heading("#0", text="Name")
    tree.heading("status", text="Status")
    tree.heading("idle", text="Idle")
    tree.heading("pid", text="PID")
    tree.heading("path", text="Path")
    tree.column("status", width=80, anchor="w")
    tree.column("idle", width=80, anchor="w")
    tree.column("pid", width=80, anchor="w")
    tree.column("path", width=360, anchor="w")
    tree.pack(fill="both", expand=True)

    meta: Dict[str, Dict[str, Any]] = {}

    def rebuild() -> None:
        # Preserve expansion and selection across refresh
        open_items = {i for i in tree.get_children("") if tree.item(i, "open")}
        selected = set(tree.selection())
        tree.delete(*tree.get_children())
        meta.clear()

        by_project = _get_running_tree()
        if not by_project:
            tree.insert("", "end", text="No running teams found.")
            return

        for project_root, sessions in sorted(by_project.items(), key=lambda x: str(x[0])):
            proj_id = tree.insert("", "end", text=f"{project_root.name}", open=True)
            meta[proj_id] = {"type": "project", "project_root": project_root}

            prefix = project_root.name
            for session_name, panes in sorted(sessions.items()):
                team_name = session_name[len(prefix) + 1:] if session_name.startswith(prefix + "-") else "Default"
                team_id = tree.insert(
                    proj_id,
                    "end",
                    text=f"Team: {team_name}",
                    open=True,
                    values=("", "", "", str(project_root))
                )
                meta[team_id] = {"type": "team", "project_root": project_root}

                seen_windows = set()
                for p in panes:
                    window = p["window"]
                    if window in seen_windows:
                        continue
                    seen_windows.add(window)
                    status = "DEAD" if p["dead"] == "1" else "RUNNING"
                    agent_id = tree.insert(
                        team_id,
                        "end",
                        text=window,
                        values=(status, f"{p['idle']}s", p["pid"], "")
                    )
                    meta[agent_id] = {
                        "type": "agent",
                        "session": p["session"],
                        "window": p["window"],
                        "project_root": project_root
                    }
            if proj_id in open_items:
                tree.item(proj_id, open=True)
        for item in selected:
            if tree.exists(item):
                tree.selection_add(item)

    def on_refresh() -> None:
        rebuild()
        if auto_var.get():
            try:
                seconds = int(interval_var.get())
            except ValueError:
                seconds = 0
            if seconds > 0:
                root.after(seconds * 1000, on_refresh)

    def on_double_click(event) -> None:
        sel = tree.selection()
        if not sel:
            return
        item_id = sel[0]
        info = meta.get(item_id)
        if not info:
            return
        if info["type"] == "team":
            _open_terminal(info["project_root"])
            return "break"
        elif info["type"] == "agent":
            _attach_tmux(info["session"], info["window"])
            return "break"
        return None

    def on_apply_auto(event=None) -> None:
        if auto_var.get():
            on_refresh()

    refresh_btn.configure(command=rebuild)
    tree.bind("<Double-1>", on_double_click)
    auto_check.configure(command=on_apply_auto)

    rebuild()
    root.mainloop()
