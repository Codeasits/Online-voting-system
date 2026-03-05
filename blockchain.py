import hashlib
import json
import time
from typing import List, Dict, Any
import os

BLOCKCHAIN_FILE = "blockchain.json"

class Block:
    def __init__(self, index: int, timestamp: float, vote_data: Dict[str, Any], previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.vote_data = vote_data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of the block"""
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "vote_data": self.vote_data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int = 2) -> None:
        """Simple proof of work mining"""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary"""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "vote_data": self.vote_data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Block':
        """Create block from dictionary"""
        block = Block(
            index=data["index"],
            timestamp=data["timestamp"],
            vote_data=data["vote_data"],
            previous_hash=data["previous_hash"]
        )
        block.nonce = data.get("nonce", 0)
        block.hash = data.get("hash", "")
        return block


class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.difficulty = 2
        self.load_chain()

    def create_genesis_block(self) -> Block:
        """Create the first block (genesis)"""
        return Block(0, time.time(), {"type": "genesis", "message": "Voting System Started"}, "0")

    def load_chain(self) -> None:
        """Load blockchain from file or create new"""
        if os.path.exists(BLOCKCHAIN_FILE):
            try:
                with open(BLOCKCHAIN_FILE, 'r') as f:
                    data = json.load(f)
                    self.chain = [Block.from_dict(b) for b in data]
            except:
                self.chain = [self.create_genesis_block()]
                self.save_chain()
        else:
            self.chain = [self.create_genesis_block()]
            self.save_chain()

    def save_chain(self) -> None:
        """Save blockchain to file"""
        with open(BLOCKCHAIN_FILE, 'w') as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)

    def get_latest_block(self) -> Block:
        """Get the last block in the chain"""
        return self.chain[-1]

    def add_vote(self, voter_id: str, party: str) -> Block:
        """Add a new vote to the blockchain"""
        previous_block = self.get_latest_block()
        new_block = Block(
            index=previous_block.index + 1,
            timestamp=time.time(),
            vote_data={
                "voter_id": voter_id,
                "party": party
            },
            previous_hash=previous_block.hash
        )
        
        # Mine the block (proof of work)
        new_block.mine_block(self.difficulty)
        
        self.chain.append(new_block)
        self.save_chain()
        
        return new_block

    def is_chain_valid(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Verify hash calculation
            if current_block.hash != current_block.calculate_hash():
                return False

            # Verify previous hash link
            if current_block.previous_hash != previous_block.hash:
                return False

        return True

    def get_vote_count(self) -> Dict[str, int]:
        """Get vote count by party"""
        counts = {}
        for block in self.chain[1:]:  # Skip genesis block
            party = block.vote_data.get("party")
            if party:
                counts[party] = counts.get(party, 0) + 1
        return counts

    def verify_vote(self, block_index: int, expected_hash: str) -> Dict[str, Any]:
        """Verify a specific vote by block index"""
        if block_index >= len(self.chain):
            return {"valid": False, "message": "Block not found"}
        
        block = self.chain[block_index]
        
        if block.hash == expected_hash:
            return {
                "valid": True,
                "message": "Vote verified",
                "vote_data": block.vote_data,
                "timestamp": block.timestamp,
                "block_hash": block.hash
            }
        else:
            return {"valid": False, "message": "Vote has been tampered!"}

    def get_all_votes(self) -> List[Dict[str, Any]]:
        """Get all votes with verification data"""
        votes = []
        for block in self.chain[1:]:
            votes.append({
                "index": block.index,
                "timestamp": block.timestamp,
                "voter_id": block.vote_data.get("voter_id"),
                "party": block.vote_data.get("party"),
                "hash": block.hash,
                "previous_hash": block.previous_hash
            })
        return votes


# Global blockchain instance
blockchain = Blockchain()

