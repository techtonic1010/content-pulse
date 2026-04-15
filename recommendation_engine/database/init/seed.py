import random
# seed.py ✅ → only prints SQL, does NOT save it to a file. Run it and copy-paste the output into your SQL client.
genres = ["crime", "comedy", "action", "romance", "thriller",
          "documentary", "sci-fi", "horror", "drama", "animation"]

regions = ["Mumbai", "Delhi", "Bangalore", "Chennai"]
age_groups = ["18-25", "26-35", "36-50"]

# ---- CONTENT ----
for i, genre in enumerate(genres):
    for j in range(10):
        content_id = f"c_{i*10+j+1:03d}"
        title = f"{genre.capitalize()} Story {j+1}"

        print(f"INSERT INTO content VALUES ('{content_id}', '{title}', 'Sample description', 120, 2020, 'English', 'MOVIE');")

        # genres (primary + random secondary)
        second = random.choice([g for g in genres if g != genre])
        print(f"INSERT INTO content_genres VALUES ('{content_id}', '{genre}');")
        print(f"INSERT INTO content_genres VALUES ('{content_id}', '{second}');")


# ---- USERS ----
for i in range(1, 21):
    user_id = f"u_{i:03d}"
    username = f"user{i}"
    email = f"user{i}@test.com"
    region = random.choice(regions)
    age = random.choice(age_groups)

    print(f"INSERT INTO users (user_id, username, email, region, age_group) VALUES ('{user_id}', '{username}', '{email}', '{region}', '{age}');")