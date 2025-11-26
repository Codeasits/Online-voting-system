import tkinter as tk
from tkinter import messagebox
import sqlite3
import face_recognition
import numpy as np
import base64
import cv2

# === DECODE ENCODING STRING BACK TO NUMPY ===
def string_to_encoding(enc_str):
    return np.frombuffer(base64.b64decode(enc_str), dtype=np.float64)

# === LOAD ALL REGISTERED ENCODINGS FROM DATABASE ===
def load_registered_voters():
    conn = sqlite3.connect("voters.db")
    c = conn.cursor()
    c.execute("SELECT name, encoding FROM voters")
    rows = c.fetchall()
    conn.close()

    voter_data = []
    for name, encoding_str in rows:
        encoding = string_to_encoding(encoding_str)
        voter_data.append((name, encoding))
    return voter_data

# === CAPTURE FACE VIA CAMERA ===
def capture_face():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Camera Error", "Unable to access the webcam.")
        return None

    messagebox.showinfo("Info", "Press 's' to capture your face.")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow("Camera - Press 's' to capture", frame)

        key = cv2.waitKey(1)
        if key == ord('s'):
            face_locations = face_recognition.face_locations(frame)
            encodings = face_recognition.face_encodings(frame, face_locations)
            cap.release()
            cv2.destroyAllWindows()
            if encodings:
                return encodings[0]
            else:
                messagebox.showerror("Face Error", "No face detected. Try again.")
                return None
        elif key == 27:  # ESC to exit
            cap.release()
            cv2.destroyAllWindows()
            return None

# === CAST VOTE OPTION ===
def cast_vote(name):
    # Show voting options after successful authentication
    voting_window = tk.Toplevel()
    voting_window.title("🗳️ Cast Your Vote")
    voting_window.geometry("400x300")

    tk.Label(voting_window, text=f"Welcome {name}, please cast your vote:", font=("Segoe UI", 14)).pack(pady=20)

    # List of candidates 
    candidates = [
        ("🟥 Party Red - Candidate A", "Candidate A"),
        ("🟦 Party Blue - Candidate B", "Candidate B"),
        ("🟩 Party Green - Candidate C", "Candidate C")
    ]
    for candidate in candidates:
        tk.Button(voting_window, text=f"Vote for {candidate}", command=lambda c=candidate: submit_vote(name, c, voting_window)).pack(pady=10)

    voting_window.mainloop()

# === SUBMIT VOTE AND RECORD ===
def submit_vote(name, candidate, window):
    
    messagebox.showinfo("Vote Recorded", f"Thank you, {name}! You voted for {candidate}.")
    window.destroy()

# === AUTHENTICATE LOGIC ===
def authenticate_voter():
    input_encoding = capture_face()
    if input_encoding is None:
        return

    voters = load_registered_voters()
    for name, registered_encoding in voters:
        match = face_recognition.compare_faces([registered_encoding], input_encoding, tolerance=0.5)[0]
        if match:
            messagebox.showinfo("Success ✅", f"Welcome {name}! Authentication successful.")
            cast_vote(name)
            return

    messagebox.showerror("Access Denied ❌", "Face not recognized. You are not a registered voter.")

# === GUI ===
def main():
    root = tk.Tk()
    root.title("🔐 Voter Authentication")
    root.state('zoomed')
    root.configure(bg="#f0f4f8")

    title_label = tk.Label(
        root,
        text="🔍 Face Recognition Voter Authentication",
        font=("Segoe UI", 28, "bold"),
        bg="#f0f4f8",
        fg="#333"
    )
    title_label.pack(pady=50)

    auth_btn = tk.Button(
        root,
        text="📷 Authenticate via Webcam",
        command=authenticate_voter,
        font=("Segoe UI", 20, "bold"),
        bg="#2196F3",
        fg="white",
        padx=20,
        pady=10,
        bd=0,
        relief="raised",
        activebackground="#1976D2"
    )
    auth_btn.pack(pady=20)

    footer = tk.Label(
        root,
        text="Developed by Shami| Secure Voting System",
        font=("Segoe UI", 14),
        bg="#f0f4f8",
        fg="#888"
    )
    footer.pack(side="bottom", pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()
