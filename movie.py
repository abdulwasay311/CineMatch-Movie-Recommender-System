import streamlit as st
import pandas as pd
import pickle
import requests
import os
import base64
import gdown

# ---------------- Page config ----------------
st.set_page_config(layout="wide", page_title="CineMatch")

# ---------------- Background ----------------
def add_bg_from_local(image_file):
    if os.path.exists(image_file):
        with open(image_file, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        page_bg_img = f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """
        st.markdown(page_bg_img, unsafe_allow_html=True)

add_bg_from_local("backgroundimage.jpg")
st.markdown("<h1 style='color:red; text-align:center;'> CineMatch</h1>", unsafe_allow_html=True)

# ---------------- Google Drive downloader ----------------
def drive_url(file_id):
    return f"https://drive.google.com/uc?id={file_id}"

def download_file_from_google_drive(id, destination):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    response = session.get(URL, params={'id': id}, stream=True)
    token = None
    for k, v in response.cookies.items():
        if k.startswith('download_warning'):
            token = v
            break
    if token:
        response = session.get(URL, params={'id': id, 'confirm': token}, stream=True)
    CHUNK_SIZE = 32768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                f.write(chunk)

def ensure_file(file_id, filename):
    """Try gdown first, then fallback to requests. Return True if file exists at end."""
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        return True

    # try gdown
    try:
        gdown.download(drive_url(file_id), filename, quiet=True)
    except Exception:
        pass

    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        return True

    # fallback requests method
    try:
        download_file_from_google_drive(file_id, filename)
    except Exception:
        pass

    return os.path.exists(filename) and os.path.getsize(filename) > 0

# ---------- Put your Drive file IDs here ----------
MOVIE_DICT_ID = "1WPVZi5ml3R40TchTj3SVEOyabSYJHzlz"
SIMILARITY_ID = "1ScPtUm3YeEkF0qjjlrt8LqHOif7luTok"

ok1 = ensure_file(MOVIE_DICT_ID, "movie_dict.pkl")
ok2 = ensure_file(SIMILARITY_ID, "similarity.pkl")

if not (ok1 and ok2):
    st.error(
        "Required data files (movie_dict.pkl or similarity.pkl) could not be loaded.\n\n"
        "Fix checklist:\n"
        "1) Ensure the Drive files are set to **Anyone with the link** (Viewer).\n"
        "2) Confirm the file IDs in app.py match the Drive links exactly.\n"
        "3) Make sure your `requirements.txt` includes `gdown` and `requests` and you re-deployed.\n\n"
        "If you need, test locally with `gdown 'https://drive.google.com/uc?id=YOUR_ID'` to confirm the file downloads."
    )
    st.stop()

# ---------------- Load pickles ----------------
movies_dict = pickle.load(open("movie_dict.pkl", "rb"))
movies = pd.DataFrame(movies_dict)
similarity = pickle.load(open("similarity.pkl", "rb"))

# ---------------- TMDB config ----------------
TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"
API_BASE_URL = "https://api.themoviedb.org/3/movie/"

def fetch_movie_details(movie_id):
    url = f"{API_BASE_URL}{movie_id}?api_key={TMDB_API_KEY}&language=en-US&append_to_response=credits,videos"
    try:
        data = requests.get(url).json()
        poster_path = data.get('poster_path')
        poster = f"https://image.tmdb.org/t/p/w500/{poster_path}" if poster_path else "https://placehold.co/500x750"
        cast = [member['name'] for member in data.get('credits', {}).get('cast', [])[:5]]
        overview = data.get('overview', "No overview available.")
        release_date = data.get('release_date', "Unknown")
        rating = data.get('vote_average', 0)
        vote_count = data.get('vote_count', 0)
        trailer_link = None
        for video in data.get("videos", {}).get("results", []):
            if video["type"] == "Trailer" and video["site"] == "YouTube":
                trailer_link = f"https://www.youtube.com/watch?v={video['key']}"
                break
        return {
            "poster": poster,
            "title": data.get("title", "Unknown"),
            "cast": ", ".join(cast) if cast else "No cast info",
            "overview": overview,
            "release_date": release_date,
            "rating": f"{rating:.1f}/10 ({vote_count} votes)",
            "trailer": trailer_link
        }
    except requests.exceptions.RequestException:
        return None

def recomend(movie):
    try:
        movie_index = movies[movies['title'] == movie].index[0]
    except IndexError:
        st.warning("Movie not found in dataset.")
        return []
    distance = similarity[movie_index]
    movies_list = sorted(list(enumerate(distance)), reverse=True, key=lambda x: x[1])[1:6]
    recommended_movies = []
    for i in movies_list:
        movie_data = movies.iloc[i[0]]
        movie_id = movie_data['movie_id']
        details = fetch_movie_details(movie_id)
        if details:
            recommended_movies.append(details)
    return recommended_movies

# ---------------- UI ----------------
selected_movie_name = st.selectbox(
    'Select a movie to get recommendations:',
    movies['title'].values,
    placeholder="Select a movie..."
)

if st.button('Show Recommendations'):
    if selected_movie_name:
        recommended_movies = recomend(selected_movie_name)
        if recommended_movies:
            st.subheader("Recommended for you:")
            for movie in recommended_movies:
                with st.container():
                    col_poster, col_details = st.columns([1, 3])
                    with col_poster:
                        st.image(movie['poster'])
                    with col_details:
                        st.markdown(f"## {movie['title']}")
                        st.markdown(f"*Release Date:* {movie['release_date']}")
                        st.markdown(f"*Rating:* {movie['rating']}")
                        st.markdown(f"*Cast:* {movie['cast']}")
                        st.markdown(f"*Overview:* {movie['overview']}")
                        if movie['trailer']:
                            st.markdown(f"[▶ Watch Trailer]({movie['trailer']})")
                st.markdown("---")
