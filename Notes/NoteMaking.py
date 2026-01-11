import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import openai
import markdown
import os

class MarkdownNotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-Driven Markdown Notes")
        self.root.geometry("1200x800")

        # Configure OpenAI API
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            self.api_key = self.prompt_for_api_key()
        openai.api_key = self.api_key

        # Create menu
        self.create_menu()

        # Create main frame
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create left panel for notes
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="Markdown Notes", font=("Arial", 14, "bold")).pack(pady=5)

        self.notes_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, font=("Courier", 10))
        self.notes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Buttons frame
        buttons_frame = tk.Frame(left_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(buttons_frame, text="Summarize", command=self.summarize_notes).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Clear", command=self.clear_notes).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Save", command=self.save_notes).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Load", command=self.load_notes).pack(side=tk.LEFT, padx=5)

        # Create right panel for summary
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(right_frame, text="Summary", font=("Arial", 14, "bold")).pack(pady=5)

        self.summary_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, font=("Courier", 10))
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.summary_text.insert("1.0", "Summary will appear here...")

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_notes)
        file_menu.add_command(label="Open", command=self.load_notes)
        file_menu.add_command(label="Save", command=self.save_notes)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Clear Notes", command=self.clear_notes)
        edit_menu.add_command(label="Clear Summary", command=self.clear_summary)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def prompt_for_api_key(self):
        api_key = tk.simpledialog.askstring("API Key", "Enter your OpenAI API Key:", show='*')
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
        return api_key

    def summarize_notes(self):
        notes = self.notes_text.get("1.0", tk.END).strip()
        if not notes:
            messagebox.showwarning("Warning", "Please enter some notes to summarize.")
            return

        self.status_var.set("Summarizing...")
        self.root.update()

        try:
            # Prompt engineering for better summaries
            prompt = f"""Please provide a concise and well-structured summary of the following markdown notes. 
Focus on the key points, main ideas, and any important details. Use bullet points or numbered lists where appropriate.
Maintain the markdown formatting where relevant.

Notes:
{notes}

Summary:"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes markdown notes effectively."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            summary = response.choices[0].message.content.strip()

            # Display the summary
            self.summary_text.delete("1.0", tk.END)
            self.summary_text.insert("1.0", summary)

            self.status_var.set("Summary generated successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate summary: {str(e)}")
            self.status_var.set("Error generating summary")

    def clear_notes(self):
        self.notes_text.delete("1.0", tk.END)

    def clear_summary(self):
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", "Summary will appear here...")

    def new_notes(self):
        self.clear_notes()
        self.clear_summary()

    def save_notes(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown files", "*.md"), ("All files", "*.*")])
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.notes_text.get("1.0", tk.END))
            self.status_var.set(f"Saved to {file_path}")

    def load_notes(self):
        file_path = filedialog.askopenfilename(filetypes=[("Markdown files", "*.md"), ("All files", "*.*")])
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.notes_text.delete("1.0", tk.END)
            self.notes_text.insert("1.0", content)
            self.status_var.set(f"Loaded from {file_path}")

    def show_about(self):
        messagebox.showinfo("About", "AI-Driven Markdown Notes\n\nA tool for writing markdown notes and generating AI-powered summaries.\n\nBuilt with Python, Tkinter, and OpenAI GPT.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MarkdownNotesApp(root)
    root.mainloop()
