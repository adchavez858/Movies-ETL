# Movies-ETL


## Overview

In this exercise movie data from Wikipedia/Kaggle along with aggregated ratings and used to assemble a movie database from a clean dataset for a hackathon.The ETL process was used to extract the Wikipedia/Kaggle data from their respective files, transform the datasets, preforming joins, and loading the cleaned dataset into a SQL database.


## Summary
The goal of this exercise is to create an automated pipeline that extracts, transform and loads data. The ETL process can be executed with a single call of the function extract_transform_load in the final step ETL_create_database.ipynb. The ETL process is broken down into four jupyter notebook files. The ETL_function_test.ipynb was designed to extract Data from the website in JSON and CSV formats, and transform it into Pandas data frames. The ETL_clean_wiki_movies.ipynb used the function clean_movie to combine scattered data of alternative languages into one column alt_titles, Its other function change_column_name organizes column names into consistent pattern. The ETL_clean_kaggle_data.ipynb used the function extract_transform_load to get new tasks for cleaning Kaggle data and includes Changing datatypes, using methods pd.to_numeric, astype() and python comparison operators for Boolean types. As well as, filling missing values and filtering unwanted columns and merging data frames using pd_merge method. 
