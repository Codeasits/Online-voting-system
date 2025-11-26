import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import sqlite3
import face_recognition
import numpy as np
import os
import base64

# === DATABASE INITIALIZATION ===
def init_database():
    conn = sqlite3.connect("voters.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image BLOB,
            encoding TEXT
        )
    ''')
    conn.commit()
    conn.close()

# === CONVERT ENCODING TO STRING FOR DB STORAGE ===
def encoding_to_string(encoding):
    return base64.b64encode(encoding.tobytes()).decode('utf-8')

# === SAVE VOTER TO DATABASE ===
def save_to_database(name, image_path, encoding):
    with open(image_path, "rb") as f:
        image_blob = f.read()
    encoding_str = encoding_to_string(encoding)

    conn = sqlite3.connect("voters.db")
    c = conn.cursor()
    c.execute("INSERT INTO voters (name, image, encoding) VALUES (?, ?, ?)", (name, image_blob, encoding_str))
    conn.commit()
    conn.close()

# === REGISTER VOTER FLOW ===
def register_voter():
    image_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
    if not image_path:
        messagebox.showwarning("Warning", "No image selected.")
        return

    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)

    if not encodings:
        messagebox.showerror("Error", "No face detected in image.")
        return

    name = simpledialog.askstring("Voter Name", "Enter Voter Name:")
    if not name:
        messagebox.showwarning("Warning", "Name is required.")
        return

    save_to_database(name, image_path, encodings[0])
    messagebox.showinfo("Success", f"✅ Voter '{name}' registered successfully!")

# === MAIN APP WINDOW ===
def main():
    init_database()
    
    root = tk.Tk()
    root.title("🗳️ Voter Registration System")
    root.state('zoomed')  # Full screen
    root.configure(bg="#f0f4f8")

    title_label = tk.Label(
        root,
        text="📸 Face Recognition Voter Registration",
        font=("Segoe UI", 28, "bold"),
        bg="#f0f4f8",
        fg="#333"
    )
    title_label.pack(pady=50)

    register_btn = tk.Button(
        root,
        text="📁 Upload Voter Photo",
        command=register_voter,
        font=("Segoe UI", 20, "bold"),
        bg="#4CAF50",
        fg="white",
        padx=20,
        pady=10,
        bd=0,
        relief="raised",
        activebackground="#45a049"
    )
    register_btn.pack(pady=20)

    footer = tk.Label(
        root,
        text="Developed by Shami | Secure Voting System",
        font=("Segoe UI", 14),
        bg="#f0f4f8",
        fg="#888"
    )
    footer.pack(side="bottom", pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()
