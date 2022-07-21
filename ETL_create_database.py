import json
import pandas as pd
import numpy as np
import os
import re

from sqlalchemy import create_engine
import psycopg2

from config import db_password

import time


#  Add the clean movie function that takes in the argument, "movie".
def clean_movie(movie):
    movie = dict(movie) #create a non-destructive copy
    
    # Empty dict to hold all alt titles
    alt_titles = {}
   
    # Loop through a list of all alternative title keys
    for alt_title_key in ["Also known as", "Arabic", "Cantonese", "Chinese", "French", 
                          "Hangul", "Hebrew", "Hepburn", "Japanese", "Literally", 
                          "Mandarin", "McCune–Reischauer", "Original title", "Polish", 
                          "Revised Romanization", "Romanized", "Russian", "Simplified", 
                          "Traditional", "Yiddish"]:
    
        # Check if the current key exists in the movie object
        if alt_title_key in movie:
            
            # Add to alt_titles dict and remove from movie object
            alt_titles[alt_title_key] = movie[alt_title_key]
            movie.pop(alt_title_key)
    
    # add alternative titles dict to the movie object
    if len(alt_titles) > 0:
        movie["alt_titles"] = alt_titles
    
    # Define function to change column name
    def change_column_name(old_name, new_name):
        if old_name in movie:
            movie[new_name] = movie.pop(old_name)
    # consolidate columns
    change_column_name("Directed by", "Director")
    change_column_name("Country of origin", "Country")
    change_column_name("Distributed by", "Distributor")
    change_column_name("Edited by", "Editor(s)")
    change_column_name("Music by", "Composer(s)")
    change_column_name("Produced by", "Producer(s)")
    change_column_name("Producer", "Producer(s)")
    change_column_name("Directed by", "Director")
    change_column_name("Productioncompany ", "Production company(s)")
    change_column_name("Productioncompanies ", "Production company(s)")
    change_column_name("Original release", "Release date")
    change_column_name("Released", "Release date")
    change_column_name("Length", "Running time")
    change_column_name("Theme music composer", "Composer(s)")
    change_column_name("Adaptation by", "Writer(s)")
    change_column_name("Screen story by", "Writer(s)")
    change_column_name("Screenplay by", "Writer(s)")
    change_column_name("Story by", "Writer(s)")
    change_column_name("Written by", "Writer(s)")

    return movie


# 1 Add the function that takes in three arguments;
# Wikipedia data, Kaggle metadata, and MovieLens rating data (from Kaggle)

def extract_transform_load():
    # Read in the kaggle metadata and MovieLens ratings CSV files as Pandas DataFrames.
    kaggle_metadata = pd.read_csv(os.path.join('Resources','movies_metadata.csv'), low_memory=False)
    ratings = pd.read_csv(os.path.join('Resources','ratings.csv'))

    # Open and read the Wikipedia data JSON file.
    with open(os.path.join('Resources','wikipedia-movies.json'), mode='r') as file:
        wiki_movies_raw = json.load(file)    
    
    # Write a list comprehension to filter out TV shows.
    wiki_movies = [movie for movie in wiki_movies_raw \
                   if ('Director' in movie or 'Directed by' in movie) \
                   and 'imdb_link' in movie \
                   and "No. of episodes" not in movie]

    # Write a list comprehension to iterate through the cleaned wiki movies list
    # and call the clean_movie function on each movie.
    cleaned_wiki_movies = [clean_movie(movie) for movie in wiki_movies]

    # Read in the cleaned movies list as a DataFrame.
    cleaned_wiki_movies_df = pd.DataFrame(cleaned_wiki_movies)

    # Write a try-except block to catch errors while extracting the IMDb ID using a regular expression string and
    #  dropping any imdb_id duplicates. If there is an error, capture and print the exception.
    try:
        cleaned_wiki_movies_df["imdb_id"] = cleaned_wiki_movies_df['imdb_link'].str.extract(r"(tt\d{7})")
        cleaned_wiki_movies_df.drop_duplicates(subset="imdb_id", inplace=True)
    except Exception as e: print(e)

    #  Write a list comprehension to keep the columns that don't have null values from the wiki_movies_df DataFrame.
    non_null_columns = [column for column in cleaned_wiki_movies_df.columns \
                        if cleaned_wiki_movies_df[column].isnull().sum() < (0.9 * len(cleaned_wiki_movies_df))]
    wiki_movies_df = cleaned_wiki_movies_df[non_null_columns]
    
    # Create a variable that will hold the non-null values from the “Box office” column.
    box_office = wiki_movies_df["Box office"].dropna()
    
    # Convert the box office data created in Step 8 to string values using the lambda and join functions.
    box_office = box_office.apply(lambda x: ' '.join(x) if x == list else x)

    # Write a regular expression to match the six elements of "form_one" of the box office data.
    form_one = r"\$\s*\d+\.?\d*\s*[mb]illi?on"
    
    # Write a regular expression to match the three elements of "form_two" of the box office data.
    form_two = r"\$\s*\d{1,3}(?:[,\.]\d{3})+(?!\s[mb]illion)"

    # Add the parse_dollars function.
    def parse_dollars(s):
        # if s is not a string, return NaN
        if type(s) != str:
            return np.nan
    
        # if input is of the form $###.# million
        if re.match(r'\$\s*\d+\.?\d*\s*milli?on', s, flags=re.IGNORECASE):
            # remove dollar sign and "million"
            s = re.sub('\$|\s|[a-zA-Z]', '', s)
            # convert to float and multiply by a million
            value = float(s) * 10**6
            # return value
            return value
    
        # if input is of the form $###.# billion
        elif re.match(r'\$\s*\d+\.?\d*\s*billi?on', s, flags=re.IGNORECASE):
            # remove dollar sign and "billion"
            s = re.sub('\$|\s|[a-zA-Z]', '', s)
            # convert to float and multiply by a billion
            value = float(s) * 10**9
            # return value
            return value
    
        # if input is of the form $###,###,###
        elif re.match(r'\$\s*\d{1,3}(?:[,\.]\d{3})+(?!\s[mb]illion)', s, flags=re.IGNORECASE):    
            # remove dollar sign and commas
            s = re.sub('\$|,', '', s)
            # covert to float
            value = float(s)
            # return value
            return value
    
        # otherwise, return NaN
        else:
            return np.nan
    
        
    # Clean the box office column in the wiki_movies_df DataFrame.
    wiki_movies_df['box_office'] = box_office.str.extract(f'({form_one}|{form_two})', \
                                                          flags=re.IGNORECASE)[0].apply(parse_dollars)
    wiki_movies_df.drop('Box office', axis=1, inplace=True)
    
    # Clean the budget column in the wiki_movies_df DataFrame.
    # Drop null values from 'Budget' column and parse
    budget = wiki_movies_df['Budget'].dropna().apply(lambda x: ' '.join(x) if x == list else x)
    # Remove values between dollar sign and a hyphen
    budget = budget.str.replace(r'\$.*[---–](?![a-z])', '$', regex=True)
    # Handle the citation references
    budget = budget.str.replace(r'\[\d+\]\s*', '')
    # Apply extract and parsing
    wiki_movies_df['budget'] = budget.str.extract(f'({form_one}|{form_two})', \
                                                  flags=re.IGNORECASE)[0].apply(parse_dollars)
    #wiki_movies_df.drop('Budget', axis=1, inplace=True)
    
    # Clean the release date column in the wiki_movies_df DataFrame.
    # Parse Release Date
    release_date = wiki_movies_df["Release date"].dropna().apply(lambda x: " ".join(x) if type(x) == list else x)
    # Regular expressions to match date formats
    date_form_one = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s[123]\d,\s\d{4}'
    date_form_two = r'\d{4}.[01]\d.[123]\d'
    date_form_three = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}'
    date_form_four = r'\d{4}'
    # Apply extract and parsing
    wiki_movies_df['release_date'] = pd.to_datetime(release_date.str.\
        extract(f'({date_form_one}|{date_form_two}|{date_form_three}|{date_form_four})')[0], infer_datetime_format=True)
    #wiki_movies_df.drop('Release date', axis=1, inplace=True)
    
    # Clean the running time column in the wiki_movies_df DataFrame.
    # Parse Running Time
    running_time = wiki_movies_df['Running time'].dropna().apply(lambda x: " ".join(x) if type(x) == list else x)
    # Extract running times
    running_time_extract = running_time.str.extract(r'(\d+)\s*ho?u?r?s?\s*(\d*)|(\d+)\s*m')
    # Change to numeric and fill nulls with 0
    running_time_extract = running_time_extract.apply(lambda col: pd.to_numeric(col, errors='coerce')).fillna(0)
    # Parse data
    wiki_movies_df['running_time'] = running_time_extract.apply(lambda row: row[0]*60 + row[1] if row[2] == 0 else row[2], axis=1)
    wiki_movies_df.drop('Running time', axis=1, inplace=True)
    
     
    # 2. Clean the Kaggle metadata.
    # Keep columns where 'adult' is False and drop the 'adult' column
    kaggle_metadata = kaggle_metadata[kaggle_metadata['adult'] == 'False'].drop('adult', axis=1)
    # Convert data types
    kaggle_metadata['video'] = kaggle_metadata['video'] == 'True'
    kaggle_metadata['budget'] = kaggle_metadata['budget'].astype(int)
    kaggle_metadata['id'] = pd.to_numeric(kaggle_metadata['id'], errors='raise')
    kaggle_metadata['popularity'] = pd.to_numeric(kaggle_metadata['popularity'], errors='raise')
    kaggle_metadata['release_date'] = pd.to_datetime(kaggle_metadata['release_date'])

    # 3. Merged the two DataFrames into the movies DataFrame.
    movies_df = pd.merge(wiki_movies_df, kaggle_metadata, on='imdb_id', suffixes=['_wiki','_kaggle'])

    # 4. Drop unnecessary columns from the merged DataFrame.
    movies_df.drop(columns=['title_wiki','release_date_wiki', 'Language', 'Production company(s)'], inplace=True)

    # 5. Add in the function to fill in the missing Kaggle data.
    # Function to replace kaggle nulls by wiki values then drop wiki column
    def fill_missing_kaggle_data(df, kaggle_column, wiki_column):
        df[kaggle_column] = df.apply(lambda row: row[wiki_column] if row[kaggle_column] == 0 else row[kaggle_column], axis=1)
        df.drop(columns=wiki_column, inplace=True)

    # 6. Call the function in Step 5 with the DataFrame and columns as the arguments.
    fill_missing_kaggle_data(movies_df, 'runtime', 'running_time')
    fill_missing_kaggle_data(movies_df, 'budget_kaggle', 'budget_wiki')
    fill_missing_kaggle_data(movies_df, 'revenue', 'box_office')

    # 7. Filter the movies DataFrame for specific columns.
    # Drop 'video' column
    movies_df.drop('video', axis=1, inplace=True)

    # 8. Rename the columns in the movies DataFrame.
    # Reorder the columns
    movies_df = movies_df.loc[:, ['imdb_id','id','title_kaggle','original_title','tagline','belongs_to_collection','url','imdb_link',
                       'runtime','budget_kaggle','revenue','release_date_kaggle','popularity','vote_average','vote_count',
                       'genres','original_language','overview','spoken_languages','Country',
                       'production_companies','production_countries','Distributor',
                       'Producer(s)','Director','Starring','Cinematography','Editor(s)','Writer(s)','Composer(s)','Based on']]
    # Rename columns
    movies_df.rename({'id':'kaggle_id',
                  'title_kaggle':'title',
                  'url':'wikipedia_url',
                  'budget_kaggle':'budget',
                  'release_date_kaggle':'release_date',
                  'Country':'country',
                  'Distributor':'distributor',
                  'Producer(s)':'producers',
                  'Director':'director',
                  'Starring':'starring',
                  'Cinematography':'cinematography',
                  'Editor(s)':'editors',
                  'Writer(s)':'writers',
                  'Composer(s)':'composers',
                  'Based on':'based_on'
                 }, axis='columns', inplace=True)

    # 9. Transform and merge the ratings DataFrame.
    # Convert Unix dates to regular date format
    ratings['timestamp'] = pd.to_datetime(ratings['timestamp'], unit='s')
    # Group ratings by movieId and ratings counts / Rename the column / Pivot the data
    rating_counts = ratings.groupby(['movieId','rating'], as_index=False).count() \
                .rename({'userId':'count'}, axis=1) \
                .pivot(index='movieId',columns='rating', values='count')
    # Rename columns
    rating_counts.columns = ['rating_' + str(col) for col in rating_counts.columns]
    movies_with_ratings_df = pd.merge(movies_df, rating_counts, how='left', left_on='kaggle_id', right_index=True)
    # Fill nulls in rating counts columns with 0
    movies_with_ratings_df[rating_counts.columns] = movies_with_ratings_df[rating_counts.columns].fillna(0)
    
    # Database engine connection
    # "postgres://[user]:[password]@[location]:[port]/[database]"
    db_string = f"postgres://postgres:{db_password}@127.0.0.1:5432/movie_data"
    # Create the database engine
    engine = create_engine(db_string)
    # Save movie_df to SQL table
    movies_df.to_sql(name='movies', con=engine, if_exists='replace')
    
    # Remove ratings table from database if needed
    # Opening a connection
    connection = engine.raw_connection()
    # Creating a cursor object using the cursor() method
    cursor = connection.cursor()
    # Droping ratings table if already exists
    cursor.execute("DROP TABLE IF EXISTS ratings")
    # Commit your changes in the database
    connection.commit()
    # Closing the connection
    connection.close()
    
    # Create the path to your file directory and variables for the three files.
    file_dir = '/Users/Cedoula/Desktop/AnalysisProjects/Module_08/Repo/Movies-ETL/Resources'
    
    # Import rating data to sql using chunksize param
    # create a variable for the number of rows imported
    rows_imported = 0
    # Create start time variable
    start_time = time.time()
    for data in pd.read_csv(f'{file_dir}/ratings.csv', chunksize=1000000):
    
        # print out the range of rows that are being imported
        print(f'importing rows {rows_imported} to {rows_imported + len(data)}...', end='')

        data.to_sql(name='ratings', con=engine, if_exists='append')
    
        # increment the number of rows imported by the chunksize
        rows_imported += len(data)
    
        # print that the rows have finished importing
        # add elapsed time to final print out
        print(f'Done. {time.time() - start_time} total seconds elapsed')