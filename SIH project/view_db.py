from app import app, db, User

# Flask requires app context to access the DB
with app.app_context():
    users = User.query.all()

    for u in users:
        print(f"ID: {u.id}")
        print(f"Google ID: {u.google_id}")
        print(f"Name: {u.name}")
        print(f"Adhaar: {u.adhaar}")
        print(f"DOB: {u.dob}")
        print(f"Gender: {u.gender}")
        print(f"Mobile: {u.mobile}")
        print(f"Username: {u.username}")
        print(f"Password: {u.password}")
        print(f"Gmail: {u.gmail}")
        print("---------------------------")
