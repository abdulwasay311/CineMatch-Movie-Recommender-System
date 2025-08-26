import streamlit as st
import pandas as pd
import pickle
import requests
import os
import ast
import base64

def add_bg_from_local(image_file):
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

add_bg_from_local("cinema.jpg")


st.markdown("<h1 style='color:red; text-align:center;'> CineMatch</h1>", unsafe_allow_html=True)


TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"
API_BASE_URL = "https://api.themoviedb.org/3/movie/"

st.set_page_config(layout="wide")


try:
    movies_dict = pickle.load(open('movie_dict.pkl', 'rb'))
    movies = pd.DataFrame(movies_dict)
    similarity = pickle.load(open('similarity.pkl', 'rb'))
except FileNotFoundError:
    st.error("Error: movie_dict.pkl or similarity.pkl not found.")
    st.stop()


def fetch_movie_details(movie_id):
    """Fetch poster, cast, overview, release date, rating, and trailer link from TMDB"""
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

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching details for movie ID {movie_id}: {e}")
        return None


def recomend(movie):
    """Recommends top 5 movies"""
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



selected_movie_name = st.selectbox(
    'Select a movie to get recommendations:',
    movies['title'].values,
    placeholder="Select a movie...",
    index=None
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