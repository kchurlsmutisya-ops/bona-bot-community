import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from .gemini_client import GeminiClient, GeminiError
from .workspace import Workspace, WorkspaceError


DEFAULT_MODEL = "gemini-2.5-flash"


class BonaBotApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Bona Bot Community Edition")
        self.root.geometry("860x680")
        self.client = GeminiClient()
        self.workspace: Workspace | None = None
        self.attached_file: str | None = None
        self.attached_text: str | None = None
        self.messages: list[dict[str, Any]] = []
        self.latest_response: str | None = None

        self.api_key = tk.StringVar()
        self.model = tk.StringVar(value=DEFAULT_MODEL)
        self.workspace_label = tk.StringVar(value="No workspace selected")
        self.attachment_label = tk.StringVar(value="No file attached")
        self.status = tk.StringVar(value="Ready")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(3, weight=1)

        ttk.Label(outer, text="Gemini API key (memory only)").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ttk.Entry(outer, textvariable=self.api_key, show="*", width=42).grid(
            row=0, column=1, sticky="ew", pady=4
        )
        ttk.Label(outer, text="Model").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(outer, textvariable=self.model).grid(row=1, column=1, sticky="ew", pady=4)

        workspace_row = ttk.Frame(outer)
        workspace_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        workspace_row.columnconfigure(1, weight=1)
        ttk.Button(workspace_row, text="Choose workspace", command=self._choose_workspace).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Label(workspace_row, textvariable=self.workspace_label).grid(
            row=0, column=1, sticky="w"
        )

        self.transcript = tk.Text(outer, wrap="word", state="disabled", height=18)
        self.transcript.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=8)
        self.transcript.tag_configure("speaker", font=("TkDefaultFont", 10, "bold"))

        attachment_row = ttk.Frame(outer)
        attachment_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Button(attachment_row, text="Attach one file", command=self._attach_file).pack(
            side="left", padx=(0, 8)
        )
        ttk.Label(attachment_row, textvariable=self.attachment_label).pack(side="left")
        ttk.Label(
            outer,
            text="Attached file text is sent to Google Gemini when you press Send.",
            foreground="#5a5a5a",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.prompt = tk.Text(outer, wrap="word", height=5)
        self.prompt.grid(row=6, column=0, columnspan=2, sticky="ew", pady=4)
        actions = ttk.Frame(outer)
        actions.grid(row=7, column=0, columnspan=2, sticky="ew", pady=4)
        self.send_button = ttk.Button(actions, text="Send", command=self._send)
        self.send_button.pack(side="left")
        ttk.Button(actions, text="Save latest response…", command=self._save_response).pack(
            side="left", padx=8
        )
        ttk.Button(actions, text="New chat", command=self._new_chat).pack(side="left")
        ttk.Label(actions, textvariable=self.status).pack(side="right")

    def _choose_workspace(self) -> None:
        selected = filedialog.askdirectory(title="Choose a workspace folder")
        if not selected:
            return
        try:
            self.workspace = Workspace(selected)
        except WorkspaceError as exc:
            messagebox.showerror("Workspace error", str(exc))
            return
        self.workspace_label.set(str(self.workspace.root))
        self._clear_attachment()

    def _attach_file(self) -> None:
        if self.workspace is None:
            messagebox.showinfo("Choose a workspace", "Choose a workspace before attaching a file.")
            return
        selected = filedialog.askopenfilename(
            title="Choose one text file",
            initialdir=str(self.workspace.root),
            filetypes=[
                ("Text files", "*.txt *.md *.py *.js *.ts *.json *.yaml *.yml *.toml *.html *.css"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return
        try:
            self.attached_file, self.attached_text = self.workspace.read_selected_file(selected)
        except WorkspaceError as exc:
            messagebox.showerror("Cannot attach file", str(exc))
            return
        self.attachment_label.set(f"{self.attached_file} (sent with next prompt)")

    def _send(self) -> None:
        prompt = self.prompt.get("1.0", "end-1c").strip()
        key = self.api_key.get()
        model = self.model.get()
        if not prompt:
            messagebox.showinfo("Prompt required", "Enter a prompt before sending.")
            return
        if not key.strip():
            messagebox.showinfo("API key required", "Enter your Gemini API key.")
            return

        request_text = prompt
        attachment_name = self.attached_file
        if self.attached_text is not None and attachment_name is not None:
            request_text += (
                f"\n\n--- User-selected file: {attachment_name} ---\n"
                f"{self.attached_text}"
            )
        user_message = {"role": "user", "parts": [{"text": request_text}]}
        contents = [*self.messages[-20:], user_message]
        history_message = {"role": "user", "parts": [{"text": prompt}]}

        self._append_message("You", prompt)
        if attachment_name:
            self._append_message("Attached file", attachment_name)
        self.prompt.delete("1.0", "end")
        self._clear_attachment()
        self.send_button.state(["disabled"])
        self.status.set("Waiting for Gemini…")
        threading.Thread(
            target=self._request_response,
            args=(key, model, contents, history_message),
            daemon=True,
        ).start()

    def _request_response(
        self,
        api_key: str,
        model: str,
        contents: list[dict[str, Any]],
        user_message: dict[str, Any],
    ) -> None:
        try:
            response = self.client.generate(api_key, model, contents)
        except GeminiError as exc:
            self._schedule_ui(self._request_failed, str(exc))
            return
        self._schedule_ui(self._request_succeeded, user_message, response)

    def _schedule_ui(self, callback, *args: Any) -> None:
        try:
            self.root.after(0, callback, *args)
        except tk.TclError:
            pass

    def _request_failed(self, error: str) -> None:
        self._append_message("Error", error)
        self.status.set("Request failed")
        self.send_button.state(["!disabled"])

    def _request_succeeded(self, user_message: dict[str, Any], response: str) -> None:
        self.messages.extend(
            [user_message, {"role": "model", "parts": [{"text": response}]}]
        )
        self.latest_response = response
        self._append_message("Bona Bot", response)
        self.status.set("Ready")
        self.send_button.state(["!disabled"])

    def _append_message(self, speaker: str, message: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}\n", "speaker")
        self.transcript.insert("end", f"{message}\n\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def _clear_attachment(self) -> None:
        self.attached_file = None
        self.attached_text = None
        self.attachment_label.set("No file attached")

    def _save_response(self) -> None:
        if self.workspace is None:
            messagebox.showinfo("Choose a workspace", "Choose a workspace before saving a response.")
            return
        if self.latest_response is None:
            messagebox.showinfo("No response", "There is no response to save yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Save response as a new file",
            initialdir=str(self.workspace.root),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            relative_path = self.workspace.save_new_file(Path(path), self.latest_response)
        except WorkspaceError as exc:
            messagebox.showerror("Cannot save response", str(exc))
            return
        self.status.set(f"Saved {relative_path}")

    def _new_chat(self) -> None:
        self.messages.clear()
        self.latest_response = None
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.configure(state="disabled")
        self.status.set("New chat")

    def _close(self) -> None:
        self.api_key.set("")
        self.attached_text = None
        self.messages.clear()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    BonaBotApp(root)
    root.mainloop()
