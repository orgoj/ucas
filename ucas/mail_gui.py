"""
Simple Tkinter GUI for UCAS Mail.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from . import mail

# Enforce uppercase USER
USER_AGENT_NAME = "USER"

class MailApp:
    def __init__(self, root, agent_name=None):
        self.root = root
        self.agent_name = agent_name or USER_AGENT_NAME
        self.root.title(f"UCAS Mail - {self.agent_name}")
        self.root.geometry("1000x700")
        
        # Override sender info in mail module for this session if needed
        # But mail module uses os.environ["UCAS_AGENT"]
        # If we are viewing as USER, we should UNSET UCAS_AGENT to be safe?
        # Or set it to USER_AGENT_NAME?
        # mail.py: if agent_name == USER_AGENT_NAME -> USER_MAIL_DIR
        # but _get_sender_info: if override_agent -> return it.
        # GUI doesn't set env var for the whole process, but maybe it should for child calls?
        # Actually standard mail operations in GUI just call mail functions directly.
        # We don't rely on env var for "viewing" logic inside GUI class, 
        # but we might for 'send_mail'.
        
        self.current_project = str(mail._get_project_root())
        
        self.setup_ui()
        self.load_projects()
        self.load_mails()

    def setup_ui(self):
        # Sidebar for Projects/Mailboxes
        sidebar = ttk.Frame(self.root, width=200, padding=5)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(sidebar, text="Mailboxes", font=("Arial", 12, "bold")).pack(anchor="w", pady=5)
        
        self.project_list = tk.Listbox(sidebar, selectmode=tk.SINGLE, height=10)
        self.project_list.pack(fill=tk.X, pady=5)
        self.project_list.bind("<<ListboxSelect>>", self.on_project_select)
        
        # Add User Mailbox option
        self.project_list.insert(tk.END, "User Mailbox (Global)")
        
        # Current Scope Label
        self.scope_label = ttk.Label(sidebar, text=f"Scope: {self.current_project}", wraplength=190)
        self.scope_label.pack(side=tk.BOTTOM, pady=10)

        # Main Content
        main_frame = ttk.Frame(self.root)
        main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar = ttk.Frame(main_frame, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Button(toolbar, text="Refresh", command=self.load_mails).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="New Message", command=self.compose_mail).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Reply", command=self.reply_mail).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Archive", command=self.archive_mail).pack(side=tk.LEFT, padx=2)
        
        # Folder Selection
        self.folder_var = tk.StringVar(value="inbox")
        ttk.Radiobutton(toolbar, text="Inbox", variable=self.folder_var, value="inbox", command=self.load_mails).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(toolbar, text="Sent", variable=self.folder_var, value="sent", command=self.load_mails).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(toolbar, text="Read", variable=self.folder_var, value="read", command=self.load_mails).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(toolbar, text="Archive", variable=self.folder_var, value="archive", command=self.load_mails).pack(side=tk.LEFT, padx=2)

        # Paned Window (Split View)
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Mail List
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=1)
        
        columns = ("id", "date", "from", "subject")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Date")
        self.tree.heading("from", text="From")
        self.tree.heading("subject", text="Subject")
        
        self.tree.column("id", width=150, anchor="w")
        self.tree.column("date", width=150, anchor="w")
        self.tree.column("from", width=200, anchor="w")
        self.tree.column("subject", width=350, anchor="w")
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Message Viewer
        viewer_frame = ttk.LabelFrame(paned, text="Message Content")
        paned.add(viewer_frame, weight=2)
        
        self.text_area = tk.Text(viewer_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def load_projects(self):
        # Load from ~/.ucas/mail-projects.txt
        projects = []
        try:
            if mail.PROJECT_LIST_FILE.exists():
                projects = mail.PROJECT_LIST_FILE.read_text().splitlines()
        except:
            pass
            
        # Add to listbox
        for p in projects:
            if Path(p).exists():
                self.project_list.insert(tk.END, p)

    def on_project_select(self, event):
        selection = self.project_list.curselection()
        if not selection:
            return
            
        value = self.project_list.get(selection[0])
        if value == "User Mailbox (Global)":
            self.agent_name = USER_AGENT_NAME
            self.current_project = "GLOBAL"
            # Update scope label??
        else:
            # Switch project?
            # Creating a GUI for PROJECT SWITCHING inside mail client is complex
            # because mail module relies on _get_project_root() which uses CWD.
            # To support switching, we'd need to mock _get_project_root or pass explicit root.
            # mail.py functions need refactoring to accept project_root more widely?
            # _get_agent_mail_dir takes project_root.
            # get_messages calls _get_sender_info which calls _get_agent_mail_dir.
            # But get_messages DOES NOT accept project_root arg.
            # It relies on _get_sender_info which relies on env/cwd.
            
            # Since strict plan said "User Mailbox OR Project", maybe we stick to current project for now?
            # Or we hack CWD?
            pass
        
        # For now, just logging
        print(f"Project switching not fully implemented in GUI (needs backend support). Selected: {value}")


    def load_mails(self):
        # Clear current list
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state=tk.DISABLED)
            
        folder = self.folder_var.get()
        
        # If we are viewing as USER, we want to see USER's inbox
        # If we are viewing as AGENT, we want to see AGENT's inbox
        # mail.get_messages(agent_name) handles this.
        
        msgs = mail.get_messages(self.agent_name, folders=[folder])
        
        for msg in msgs:
            display_from = msg.get('to') if folder == 'sent' else msg.get('from')
            self.tree.insert("", tk.END, values=(msg.get('id'), msg.get('date_str'), display_from, msg.get('subject')), iid=msg.get('id'))

    def on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        
        mail_id = selection[0]
        data, _, found_folder = mail.get_message_content(mail_id, self.agent_name)
        
        if data:
            self.display_message(data)
            if found_folder == 'inbox':
                mail.mark_as_read(mail_id, self.agent_name)

    def display_message(self, data):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        
        header = f"From:    {data.get('from')}\n"
        header += f"To:      {data.get('to')}\n"
        header += f"Date:    {data.get('date_str')}\n"
        header += f"Subject: {data.get('subject')}\n"
        if data.get('from_project'):
             header += f"Project: {data.get('from_project')}\n"
        header += "-" * 60 + "\n\n"
        
        self.text_area.insert(tk.END, header)
        self.text_area.insert(tk.END, data.get('body'))
        self.text_area.config(state=tk.DISABLED)

    def compose_mail(self, reply_to=None):
        ComposeWindow(self.root, reply_to, self.agent_name)

    def reply_mail(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Select a message to reply to.")
            return
        
        mail_id = selection[0]
        data, _, _ = mail.get_message_content(mail_id, self.agent_name)
        if data:
            self.compose_mail(reply_to=data)

    def archive_mail(self):
        selection = self.tree.selection()
        if not selection:
            return
        mail_id = selection[0]
        mail.archive_mail(mail_id, self.agent_name)
        self.load_mails()

class ComposeWindow:
    def __init__(self, parent, reply_to=None, sender_name=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Compose Message")
        self.top.geometry("600x400")
        self.sender_name = sender_name
        
        # Fields
        tk.Label(self.top, text="To:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.to_entry = tk.Entry(self.top)
        self.to_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(self.top, text="Subject:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.subject_entry = tk.Entry(self.top)
        self.subject_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(self.top, text="Body:").grid(row=2, column=0, sticky="nw", padx=5, pady=5)
        self.body_text = tk.Text(self.top, font=("Consolas", 10))
        self.body_text.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
        
        self.top.grid_columnconfigure(1, weight=1)
        self.top.grid_rowconfigure(2, weight=1)
        
        # Buttons
        btn_frame = tk.Frame(self.top)
        btn_frame.grid(row=3, column=1, sticky="e", padx=5, pady=5)
        
        tk.Button(btn_frame, text="Send", command=self.send).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.top.destroy).pack(side=tk.LEFT, padx=5)
        
        if reply_to:
            self.to_entry.insert(0, reply_to.get('from'))
            self.subject_entry.insert(0, f"Re: {reply_to.get('subject')}")
            self.reply_id = reply_to.get('id')
        else:
            self.reply_id = None

    def send(self):
        recipient = self.to_entry.get().strip()
        subject = self.subject_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).strip()
        
        if not recipient:
            messagebox.showerror("Error", "Recipient is required")
            return
            
        try:
            # Pass sender_override to send_mail
            mail.send_mail(recipient, subject, body, reply_id=self.reply_id, sender_override=self.sender_name)
            messagebox.showinfo("Success", "Mail sent successfully")
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

def run_gui(agent_name=None):
    root = tk.Tk()
    app = MailApp(root, agent_name)
    root.mainloop()
