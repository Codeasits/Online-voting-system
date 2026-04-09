from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3, os, base64, io
import numpy as np
import face_recognition
from PIL import Image
from blockchain import blockchain

app = Flask(__name__) 
app.secret_key = "secure_voting_key_2024"

DB = "database.db"
UPLOAD = "uploads"
os.makedirs(UPLOAD, exist_ok=True)

# ---------- DATABASE ----------
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    d = db()
    d.execute("""
        CREATE TABLE IF NOT EXISTS voters(
            voter_id TEXT PRIMARY KEY,
            name TEXT,
            encoding TEXT,
            voted INTEGER DEFAULT 0
        )
    """)
    d.execute("""
        CREATE TABLE IF NOT EXISTS votes(
            party TEXT,
            block_index INTEGER,
            block_hash TEXT
        )
    """)
    d.commit()

init_db()

# ---------- HELPERS ----------
def enc_to_str(enc):
    return base64.b64encode(enc.tobytes()).decode()

def str_to_enc(s):
    return np.frombuffer(base64.b64decode(s), dtype=np.float64)

# ---------- ROUTES ----------
@app.route("/")
def index():
    # Check blockchain integrity
    chain_valid = blockchain.is_chain_valid()
    total_votes = len(blockchain.chain) - 1  # Exclude genesis
    return render_template("index.html", chain_valid=chain_valid, total_votes=total_votes)

# -------- REGISTER --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        aadhaar = request.form["aadhaar"]
        photo = request.files["photo"]

        if not aadhaar.isdigit() or len(aadhaar) != 12:
            return render_template("register.html", error="Aadhaar must be 12 digits")

        path = os.path.join(UPLOAD, aadhaar + ".jpg")
        photo.save(path)

        image = face_recognition.load_image_file(path)
        enc = face_recognition.face_encodings(image)

        if len(enc) != 1:
            os.remove(path)
            return render_template("register.html", error="Upload clear face image")

        try:
            d = db()
            d.execute(
                "INSERT INTO voters VALUES(?,?,?,0)",
                (aadhaar, name, enc_to_str(enc[0]))
            )
            d.commit()
        except:
            return render_template("register.html", error="Already registered")

        return redirect("/authenticate")

    return render_template("register.html")

# -------- AUTHENTICATE (AADHAAR ONLY) --------
@app.route("/authenticate", methods=["GET", "POST"])
def authenticate():
    if request.method == "POST":
        aadhaar = request.form["aadhaar"]
        d = db()

        voter = d.execute(
            "SELECT * FROM voters WHERE voter_id=?",
            (aadhaar,)
        ).fetchone()

        if not voter:
            return render_template("authenticate.html", error="Not registered")

        if voter["voted"] == 1:
            return render_template("authenticate.html", error="Already voted")

        session["voter"] = aadhaar
        session["voter_name"] = voter["name"]
        return redirect("/live_verify")

    return render_template("authenticate.html")

# -------- LIVE CAMERA PAGE --------
@app.route("/live_verify")
def live_verify():
    if "voter" not in session:
        return redirect("/authenticate")
    return render_template("live_verify.html")

# -------- FACE VERIFICATION API --------
@app.route("/verify_face", methods=["POST"])
def verify_face():
    if "voter" not in session:
        return jsonify({"status": "error"})

    image_data = request.files["image"].read()
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    image_np = np.array(image)

    d = db()
    voter = d.execute(
        "SELECT encoding FROM voters WHERE voter_id=?",
        (session["voter"],)
    ).fetchone()

    stored_encoding = str_to_enc(voter["encoding"])
    faces = face_recognition.face_encodings(image_np)

    if not faces:
        return jsonify({"status": "no_face"})

    match = face_recognition.compare_faces(
        [stored_encoding],
        faces[0],
        tolerance=0.45
    )

    if match[0]:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "fail"})

# -------- VOTE --------
@app.route("/vote", methods=["GET", "POST"])
def vote():
    if "voter" not in session:
        return redirect("/authenticate")

    if request.method == "POST":
        party = request.form["vote"]
        aadhaar = session["voter"]
        
        # Add vote to blockchain
        new_block = blockchain.add_vote(aadhaar, party)
        
        # Store in local database for quick queries
        d = db()
        d.execute("INSERT INTO votes VALUES(?, ?, ?)", 
                  (party, new_block.index, new_block.hash))
        d.execute("UPDATE voters SET voted=1 WHERE voter_id=?", (aadhaar,))
        d.commit()

        # Prepare vote receipt data
        receipt_data = {
            "voter_id": aadhaar[:4] + "****" + aadhaar[-4:],
            "party": party,
            "block_index": new_block.index,
            "block_hash": new_block.hash,
            "timestamp": new_block.timestamp,
            "previous_hash": new_block.previous_hash[:16] + "..."
        }
        
        session.clear()
        return render_template("success.html", receipt=receipt_data)

    return render_template("vote.html")

# -------- VOTE VERIFICATION --------
@app.route("/verify_vote", methods=["POST"])
def verify_vote():
    """Verify a vote using block index and hash"""
    data = request.get_json()
    block_index = data.get("block_index")
    expected_hash = data.get("hash")
    
    result = blockchain.verify_vote(block_index, expected_hash)
    return jsonify(result)

# -------- BLOCKCHAIN STATUS --------
@app.route("/blockchain_status")
def blockchain_status():
    """Get blockchain status and statistics"""
    chain_valid = blockchain.is_chain_valid()
    vote_counts = blockchain.get_vote_count()
    total_votes = len(blockchain.chain) - 1
    
    return jsonify({
        "valid": chain_valid,
        "total_blocks": len(blockchain.chain),
        "total_votes": total_votes,
        "vote_counts": vote_counts
    })

# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():
    d = db()
    total = d.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
    voted = d.execute("SELECT COUNT(*) FROM voters WHERE voted=1").fetchone()[0]
    
    # Get blockchain stats
    chain_valid = blockchain.is_chain_valid()
    vote_counts = blockchain.get_vote_count()
    
    return render_template(
        "dashboard.html",
        total=total,
        voted=voted,
        not_voted=total - voted,
        chain_valid=chain_valid,
        vote_counts=vote_counts,
        blockchain_blocks=len(blockchain.chain)
    )

# -------- ANALYTICS --------
@app.route("/analytics")
def analytics():
    # Use blockchain for vote data
    vote_counts = blockchain.get_vote_count()
    
    parties = list(vote_counts.keys())
    counts = list(vote_counts.values())
    
    # Get all votes for verification
    all_votes = blockchain.get_all_votes()
    
    return render_template(
        "analytics.html",
        parties=parties,
        counts=counts,
        all_votes=all_votes,
        chain_valid=blockchain.is_chain_valid()
    )

# -------- VERIFY SPECIFIC VOTE --------
@app.route("/verify")
def verify_page():
    """Page to verify individual votes"""
    return render_template("verify.html")

@app.route("/verify", methods=["POST"])
def verify_vote_page():
    """Verify a vote from the verification page"""
    block_index = request.form.get("block_index", type=int)
    block_hash = request.form.get("block_hash")
    
    if not block_index or not block_hash:
        return render_template("verify.html", error="Please provide both Block Index and Hash")
    
    result = blockchain.verify_vote(block_index, block_hash)
    return render_template("verify.html", result=result)

if __name__ == "__main__":
    app.run(debug=True)

