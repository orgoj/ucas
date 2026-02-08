"""
Advanced Tkinter GUI for UCAS Mail.
Identifies everything by absolute project PATH.
Sidebar shows absolute paths. Only lowercase agent names permitted.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from . import mail

class MailApp:
    def __init__(self, root, agent_name=None):
        self.root = root
        self.agent_name = agent_name or "USER"
        self.project_root = None 
        self.root.title(f"UCAS Mail Manager")
        self.root.geometry("1250x800")
        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(toolbar, text="Refresh All", command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="New Message", command=self.compose_mail).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Reply", command=self.reply_mail).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Archive", command=self.archive_selected).pack(side=tk.LEFT, padx=2)
        
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        sidebar_frame = ttk.Frame(main_paned)
        main_paned.add(sidebar_frame, weight=1)
        ttk.Label(sidebar_frame, text="ACCOUNTS (BY PATH)", font=("Sans", 10, "bold")).pack(anchor="w", padx=5, pady=5)
        
        self.nav_tree = ttk.Treeview(sidebar_frame, show="tree", selectmode="browse")
        self.nav_tree.pack(fill=tk.BOTH, expand=True)
        self.nav_tree.bind("<<TreeviewSelect>>", self.on_nav_select)
        
        content_frame = ttk.Frame(main_paned)
        main_paned.add(content_frame, weight=4)
        
        folder_bar = ttk.Frame(content_frame, padding=2)
        folder_bar.pack(side=tk.TOP, fill=tk.X)
        self.folder_var = tk.StringVar(value="inbox")
        for f in ["inbox", "read", "sent", "archive"]:
            ttk.Radiobutton(folder_bar, text=f.capitalize(), variable=self.folder_var, value=f, command=self.load_mails).pack(side=tk.LEFT, padx=5)
        
        self.content_paned = ttk.PanedWindow(content_frame, orient=tk.VERTICAL)
        self.content_paned.pack(fill=tk.BOTH, expand=True)
        
        # Mail List
        list_frame = ttk.Frame(self.content_paned)
        self.content_paned.add(list_frame, weight=1)
        columns = ("id", "date", "from", "to", "subject")
        self.mail_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        for c in columns: self.mail_tree.heading(c, text=c.upper())
        self.mail_tree.column("id", width=100)
        self.mail_tree.column("date", width=130)
        self.mail_tree.column("from", width=180)
        self.mail_tree.column("to", width=180)
        self.mail_tree.column("subject", width=300)
        
        mail_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.mail_tree.yview)
        self.mail_tree.configure(yscroll=mail_scroll.set)
        self.mail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.mail_tree.bind("<<TreeviewSelect>>", self.on_mail_select)
        
        viewer_frame = ttk.LabelFrame(self.content_paned, text="Message Viewer")
        self.content_paned.add(viewer_frame, weight=2)
        self.text_area = tk.Text(viewer_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 11))
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def refresh(self):
        self.nav_tree.delete(*self.nav_tree.get_children())
        user_path = str(mail._get_user_mail_dir())
        self.nav_tree.insert("", tk.END, "agent:USER:global", text=f"👤 USER (PATH: {user_path})")
        
        if mail.PROJECT_LIST_FILE.exists():
            original_paths = sorted(list(set(p.strip() for p in mail.PROJECT_LIST_FILE.read_text().splitlines() if p.strip())))
            valid_paths = []
            
            for p_str in original_paths:
                p = Path(p_str).resolve()
                # Check if it exists and is not in /tmp
                if p.exists() and not str(p).startswith("/tmp/"):
                    valid_paths.append(str(p))
                    p_node = self.nav_tree.insert("", tk.END, f"proj:{p}", text=f"📂 {p}", open=True)
                    self.add_agents_to_node(p_node, p)
            
            # Update the list file if some paths were removed
            if len(valid_paths) != len(original_paths):
                try:
                    with open(mail.PROJECT_LIST_FILE, "w") as f:
                        for vp in valid_paths:
                            f.write(f"{vp}\n")
                except:
                    pass
        
        self.nav_tree.selection_set("agent:USER:global")

    def add_agents_to_node(self, parent_node, project_root):
        mails_dir = project_root / ".ucas" / "mails"
        if mails_dir.exists():
            for item in sorted(mails_dir.iterdir()):
                if item.is_dir() and item.name.islower():
                    self.nav_tree.insert(parent_node, tk.END, f"agent:{item.name}:{project_root}", text=f"   {item.name}")

    def on_nav_select(self, event):
        selection = self.nav_tree.selection()
        if not selection: return
        item = selection[0]
        if item.startswith("agent:"):
            _, self.agent_name, root_path = item.split(":", 2)
            self.project_root = Path(root_path) if root_path != "global" else None
            self.root.title(f"UCAS Mail Manager - {self.agent_name} @ {self.project_root if self.project_root else 'Global'}")
            self.load_mails()

    def load_mails(self):
        self.mail_tree.delete(*self.mail_tree.get_children())
        self.text_area.config(state=tk.NORMAL); self.text_area.delete(1.0, tk.END); self.text_area.config(state=tk.DISABLED)
        msgs = mail.get_messages(agent_name=self.agent_name, folders=[self.folder_var.get()], project_root=self.project_root)
        for msg in msgs:
            self.mail_tree.insert("", tk.END, values=(msg.get('id'), msg.get('date_str'), msg.get('from'), msg.get('to'), msg.get('subject')), iid=msg.get('id'))

    def on_mail_select(self, event):
        selection = self.mail_tree.selection()
        if not selection: return
        data, path, folder = mail.get_message_content(selection[0], agent_name=self.agent_name, project_root=self.project_root)
        if data:
            self.display_message(data)
            if folder == 'inbox': mail.mark_as_read(selection[0], agent_name=self.agent_name, project_root=self.project_root)

    def display_message(self, data):
        self.text_area.config(state=tk.NORMAL); self.text_area.delete(1.0, tk.END)
        fields = [('From', data.get('from')), ('To', data.get('to')), ('Date', data.get('date_str')), ('Subject', data.get('subject')), ('PATH', data.get('from_project'))]
        for label, val in fields:
            if val: self.text_area.insert(tk.END, f"{label:<12}: {val}\n")
        self.text_area.insert(tk.END, "-" * 80 + "\n\n" + data.get('body', ''))
        self.text_area.config(state=tk.DISABLED)

    def archive_selected(self):
        selection = self.mail_tree.selection()
        if selection:
            mail.archive_mail(selection[0], agent_name=self.agent_name, project_root=self.project_root)
            self.load_mails()

    def compose_mail(self, reply_to=None):
        ComposeWindow(self.root, reply_to, current_agent=self.agent_name, project_root=self.project_root)

    def reply_mail(self):
        selection = self.mail_tree.selection()
        if selection:
            data, _, _ = mail.get_message_content(selection[0], agent_name=self.agent_name, project_root=self.project_root)
            if data: self.compose_mail(reply_to=data)

class ComposeWindow:
    def __init__(self, parent, reply_to=None, current_agent="USER", project_root=None):
        self.top = tk.Toplevel(parent); self.top.title(f"Compose Message (as {current_agent})"); self.top.geometry("600x550")
        self.current_agent = current_agent; self.project_root = project_root
        tk.Label(self.top, text="To:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.to_entry = tk.Entry(self.top); self.to_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        tk.Label(self.top, text="Subject:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.subject_entry = tk.Entry(self.top); self.subject_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        tk.Label(self.top, text="Body:").grid(row=2, column=0, sticky="nw", padx=5, pady=5)
        self.body_text = tk.Text(self.top, font=("Consolas", 11)); self.body_text.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
        self.top.grid_columnconfigure(1, weight=1); self.top.grid_rowconfigure(2, weight=1)
        btn_frame = tk.Frame(self.top); btn_frame.grid(row=3, column=1, sticky="e", padx=5, pady=5)
        tk.Button(btn_frame, text="Send", command=self.send).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.top.destroy).pack(side=tk.LEFT, padx=5)
        if reply_to:
            self.to_entry.insert(0, reply_to.get('from'))
            subj = reply_to.get('subject', 'No Subject')
            self.subject_entry.insert(0, f"Re: {subj}" if not subj.startswith("Re:") else subj)
            self.reply_id = reply_to.get('id')
        else: self.reply_id = None
    def send(self):
        try:
            mail.send_mail(self.to_entry.get(), self.subject_entry.get(), self.body_text.get("1.0", tk.END), 
                          reply_id=self.reply_id, sender_override=self.current_agent, project_root=self.project_root)
            messagebox.showinfo("Success", "Mail sent successfully"); self.top.destroy()
        except Exception as e: messagebox.showerror("Error", str(e))

def run_gui(agent_name=None):
    root = tk.Tk(); MailApp(root, agent_name); root.mainloop()
