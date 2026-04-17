import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import os

BG = "#0d0d1a"
BG2 = "#151528"
ACC = "#7c3aed"
GRN = "#22c55e"
WHT = "#f1f5f9"

class ClipFusionApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ClipFusion V3.0")
        self.root.geometry("900x600")
        self.root.configure(bg=BG)
        self.video_path = None
        self._build_ui()

    def run(self):
        self.root.mainloop()

    def _build_ui(self):
        # Header
        tk.Frame(self.root, bg=ACC, height=50).pack(fill="x")
        tk.Label(self.root, text="✂ ClipFusion V3.0", font=("Helvetica", 16, "bold"), bg=ACC, fg=WHT).place(x=20, y=10)

        # Notebook
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)

        # Abas
        self._tab_projeto()
        self._tab_transcricao()
        self._tab_render()

    def _tab_projeto(self):
        f = tk.Frame(self.nb, bg=BG2)
        self.nb.add(f, text="📁 Projeto")
        tk.Label(f, text="Projeto", font=("Helvetica", 14), bg=BG2, fg=WHT).pack(pady=20)
        tk.Button(f, text="Selecionar Vídeo", command=self._select_video, bg=ACC, fg=WHT).pack()
        self.lbl_video = tk.Label(f, text="Nenhum vídeo", bg=BG2, fg=WHT)
        self.lbl_video.pack(pady=10)

        tk.Label(f, text="Proteção:", bg=BG2, fg=WHT).pack()
        self.protection = tk.StringVar(value="none")
        for val, txt in [("none", "🟢 Nenhum"), ("basic", "🟡 Básico"), ("maximum", "🔴 Máximo")]:
            tk.Radiobutton(f, text=txt, variable=self.protection, value=val, bg=BG2, fg=WHT, selectcolor=ACC).pack()

    def _tab_transcricao(self):
        f = tk.Frame(self.nb, bg=BG2)
        self.nb.add(f, text="📝 Transcrição")
        self.txt_trans = scrolledtext.ScrolledText(f, height=20, bg="#1e1e3a", fg=WHT)
        self.txt_trans.pack(fill="both", expand=True, padx=20, pady=10)
        tk.Button(f, text="Iniciar", command=self._start_trans, bg=GRN, fg=WHT).pack()

    def _tab_render(self):
        f = tk.Frame(self.nb, bg=BG2)
        self.nb.add(f, text="🎬 Render")
        self.txt_log = scrolledtext.ScrolledText(f, height=20, bg="#1e1e3a", fg=GRN)
        self.txt_log.pack(fill="both", expand=True, padx=20, pady=10)
        tk.Button(f, text="Renderizar", command=self._start_render, bg=ACC, fg=WHT).pack()

    def _select_video(self):
        p = filedialog.askopenfilename(filetypes=[("Vídeos", "*.mp4")])
        if p:
            self.video_path = p
            self.lbl_video.config(text=os.path.basename(p))

    def _start_trans(self):
        self.txt_trans.insert("end", "Transcrevendo...\n")

    def _start_render(self):
        if not self.video_path:
            messagebox.showwarning("Aviso", "Selecione um vídeo!")
            return
        self.txt_log.insert("end", f"Renderizando com {self.protection.get()}...\n")
