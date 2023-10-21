import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from dotenv import load_dotenv
import requests
from movie_getter import movie_database_getter, imdb_getter, rotten_tomatoes_getter
from data_access import movie_data_access
from models.movie import Movie

load_dotenv()

MOVIE_DB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"
MOVIE_DB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"
MOVIE_DB_API_KEY = os.environ["MOVIE_DB_API_KEY"]

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ["SECRET_KEY"]
Bootstrap(app)

#Init xml file
movie_data_access.initialize_movies_if_not_exists()


class RateMovieForm(FlaskForm):
    rating = StringField(label="Your Rating Out of 10 e.g. 7.5", validators=[DataRequired()])
    review = StringField(label="Your Review", validators=[DataRequired()])
    submit = SubmitField(label="Done")


class AddMovieForm(FlaskForm):
    title = StringField(label="Movie Title", validators=[DataRequired()])
    add_movie_btn = SubmitField(label="Add Movie")


@app.route("/")
def home():
    # create a list of movies sorted by rating
    all_movies = movie_data_access.get_all_movies()
    if len(all_movies) > 0:
        sorted_movies = movie_data_access.sort_movies_by_rating(all_movies)
        for i in range(len(sorted_movies)):
            sorted_movies[i].ranking = len(sorted_movies) - i
            movie_data_access.update_movie(sorted_movies[i])
    else:
        sorted_movies = all_movies
    return render_template("index.html", movies=sorted_movies)


# Add movie route
@app.route("/add", methods=["GET", "POST"])
def add_movie():
    add_form = AddMovieForm()
    if add_form.validate_on_submit():
        movie_title = add_form.title.data
        # Search for the movie using the title in the MovieDB API
        data = movie_database_getter.search_movies_by_title(movie_title)
        if not data:
            flash(f"Movie with title {movie_title} not found!", category="error")
            return redirect(url_for("add_movie"))
        return render_template("select.html", options=data)
    return render_template("add.html", form=add_form)


@app.route("/find")
def find_movie():
    movie_id = request.args.get("id")
    if movie_id:
        data = movie_database_getter.get_movie_by_movie_id(movie_id)
        existing_movie = movie_data_access.existing_title(check_title= data["title"])
        if existing_movie:
            flash("Movie already exists!", category="danger")
            return redirect(url_for("edit_movie", id=existing_movie.movie_id))

        new_movie = Movie(
            movie_id=None,
            title=data["title"],
            year=data["release_date"].split("-")[0],
            image_url=f"{MOVIE_DB_IMAGE_URL}{data['poster_path']}",
            description=data["overview"],
        )
        new_movie_id, new_movie_title = movie_data_access.create_movie(new_movie)
        return redirect(url_for("edit_movie", id=new_movie_id, title=new_movie_title))
    return redirect(url_for("home"))


# Edit movie route
@app.route("/edit", methods=["GET", "POST"])
def edit_movie():
    form = RateMovieForm()
    movie_id = request.args.get("id")
    movie_title = request.args.get("title")
    update_movie = movie_data_access.search_movie_by_id(movie_id)
    imdb_rating = imdb_getter.get_movie_rating(movie_title=movie_title)
    rotten_rating = rotten_tomatoes_getter.get_movie_ratings(movie_title=movie_title)
    if form.validate_on_submit():
        update_movie.rating = str(float(form.rating.data))
        update_movie.review = form.review.data
        update_movie.imdb_rating = imdb_rating
        update_movie.rotten_rating = rotten_rating
        movie_data_access.update_movie(update_movie)
        return redirect(url_for("home"))
    return render_template("edit.html", movie=update_movie, form=form)


# Delete movie route
@app.route("/delete")
def delete_movie():
    movie_id = request.args.get("id")
    movie_data_access.delete_movie(delete_movie_id=movie_id)
    return redirect(url_for("home"))


@app.errorhandler(404)
def handle_not_found_error(error):
    return render_template("error.html", error="404 - Page Not Found"), 404


@app.errorhandler(500)
def handle_internal_error(error):
    return render_template("error.html", error="500 - Internal Server Error"), 500


if __name__ == '__main__':
    app.run(debug=True)
