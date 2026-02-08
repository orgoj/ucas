"""
Simple Tkinter GUI for UCAS Mail.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from . import mail

class MailApp:
    def __init__(self, root, agent_name=None):
        self.root = root
        self.agent_name = agent_name or "user"
        self.root.title(f"UCAS Mail - {self.agent_name}")
        self.root.geometry("800x600")
        
        # Override sender info in mail module for this session
        self.original_env_agent = mail.os.environ.get("UCAS_AGENT")
        if self.agent_name != "user":
            mail.os.environ["UCAS_AGENT"] = self.agent_name
        
        self.setup_ui()
        self.load_mails()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Button(toolbar, text="Refresh", command=self.load_mails).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="New Message", command=self.compose_mail).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Reply", command=self.reply_mail).pack(side=tk.LEFT, padx=2)
        
        # Folder Selection
        self.folder_var = tk.StringVar(value="inbox")
        ttk.Radiobutton(toolbar, text="Inbox", variable=self.folder_var, value="inbox", command=self.load_mails).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(toolbar, text="Sent", variable=self.folder_var, value="sent", command=self.load_mails).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(toolbar, text="Read", variable=self.folder_var, value="read", command=self.load_mails).pack(side=tk.LEFT, padx=2)

        # Paned Window (Split View)
        paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Mail List
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=1)
        
        columns = ("id", "date", "from", "subject")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Date")
        self.tree.heading("from", text="From/To")
        self.tree.heading("subject", text="Subject")
        
        self.tree.column("id", width=150, anchor="w")
        self.tree.column("date", width=150, anchor="w")
        self.tree.column("from", width=100, anchor="w")
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

    def load_mails(self):
        # Clear current list
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Clear message viewer
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state=tk.DISABLED)
            
        folder = self.folder_var.get()
        # mail.get_messages expects list of folders to search
        # We modify mail.get_messages to take explicit agent if needed, 
        # but here we relied on env var hack in __init__ or we can update mail.py again.
        # Let's rely on the env var hack for now as it's simplest for KISS.
        
        # Actually mail.get_messages calls _get_sender_info which checks env vars.
        
        # We need to construct list of folders. get_messages searches ALL given folders.
        # But we want to filter by folder in UI.
        
        # Let's call a lower level function or just filter results?
        # mail.get_messages returns everything from passed folders.
        
        msgs = mail.get_messages(folders=[folder])
        
        for msg in msgs:
            # Display 'To' if in Sent folder, otherwise 'From'
            display_name = msg.get('to') if folder == 'sent' else msg.get('from')
            self.tree.insert("", tk.END, values=(msg.get('id'), msg.get('date_str'), display_name, msg.get('subject')), iid=msg.get('id'))

    def on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        
        mail_id = selection[0]
        folder = self.folder_var.get()
        
        # We need to fetch full content
        # mail.get_message_content searches all folders, which is fine
        data, path, found_folder = mail.get_message_content(mail_id)
        
        if data:
            self.display_message(data)
            # If checking inbox, move to read?
            # Maybe only on explicit action or double click?
            # For now, let's auto-mark read if in inbox
            if found_folder == 'inbox':
                mail.mark_as_read(mail_id)
                # Refresh list if we are in inbox to show it moved? 
                # Or just keep it there until refresh.
                # Standard mail clients keep it but unbold it.
                # Here we physically move files. So it will disappear on refresh.
                # Let's just update the status internally but not refresh immediately to not jar the user.

    def display_message(self, data):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        
        header = f"From:    {data.get('from')}\n"
        header += f"To:      {data.get('to')}\n"
        header += f"Date:    {data.get('date_str')}\n"
        header += f"Subject: {data.get('subject')}\n"
        header += "-" * 60 + "\n\n"
        
        self.text_area.insert(tk.END, header)
        self.text_area.insert(tk.END, data.get('body'))
        self.text_area.config(state=tk.DISABLED)

    def compose_mail(self, reply_to=None):
        ComposeWindow(self.root, reply_to)

    def reply_mail(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Select a message to reply to.")
            return
        
        mail_id = selection[0]
        data, _, _ = mail.get_message_content(mail_id)
        if data:
            self.compose_mail(reply_to=data)

class ComposeWindow:
    def __init__(self, parent, reply_to=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Compose Message")
        self.top.geometry("600x400")
        
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
            # We use the public send_mail from ucas.mail
            # Since we set the ENV var in MailApp, send_mail will pick up the right sender
            mail.send_mail(recipient, subject, body, reply_id=self.reply_id)
            messagebox.showinfo("Success", "Mail sent successfully")
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

def run_gui(agent_name=None):
    root = tk.Tk()
    app = MailApp(root, agent_name)
    root.mainloop()
