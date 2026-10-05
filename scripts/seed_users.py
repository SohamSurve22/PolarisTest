"""Create one test user and one test officer in MongoDB.

Run from the project root:  python scripts/seed_users.py
Needs:  pip install pymongo bcrypt   (and the mongo container running)
"""
import os

import bcrypt
from pymongo import MongoClient

uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
users = MongoClient(uri, serverSelectionTimeoutMS=3000)["polarislex"]["users"]
users.create_index("email", unique=True)

users.delete_one({"email": "officer@test.com"})  # old non-govt test officer

ACCOUNTS = [
  ("user@test.com", "User@123", "user"),
  ("officer@gov.in", "Officer@123", "officer"),
]
for email, password, role in ACCOUNTS:
  users.update_one(
    {"email": email},
    {"$set": {"passwordHash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()), "role": role}},
    upsert=True,
  )
  print(f"Seeded {role}: {email} / {password}")
