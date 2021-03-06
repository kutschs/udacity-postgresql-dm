import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """
    - open and read filepath containing exactly one song
    
    - build a list containing values for table 'songs'
    - insert values into table 'songs'
    
    - build a list containing values for table 'artists'
    - insert values into table 'artists'
    """
    # open song file
    df = pd.read_json(filepath, lines=True)

    # insert song record
    # index 0 because there is only one song per song_file
    song_data = ( df['song_id'][0]
                , df['title'][0]
                , df['artist_id'][0]
                , int(df['year'][0]) # sql can't handle numpy int64 type
                , str(df['duration'][0]) + ' seconds'
                ) 
    cur.execute(song_table_insert, song_data)
    
    # insert artist record
    # index 0 because there is only one song per song_file
    artist_data = ( df['artist_id'][0]
                  , df['artist_name'][0]
                  , df['artist_location'][0]
                  , df['artist_latitude'][0]
                  , df['artist_longitude'][0]
                  )
    cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    """
    - logfiles contain many songplay events
    
    - open and read filepath
    - only process events with 'page = NextSong'
    - build list with values for table 'time'
    - insert values into table 'time'
    
    - build list with values for table 'users'
    - insert values into table 'users'
    
    - build list with values for table 'users'
      - using song_id and artist_id from 
        tables 'songs' and 'artists'
    - insert values into table 'users'
    """
    # open log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    df = df[df['page'] == 'NextSong']

    # convert timestamp column to datetime
    t = pd.to_datetime(df['ts'],unit='ms')
    
    # insert time data records
    time_data = [ t.tolist()
                , t.dt.hour.tolist()
                , t.dt.day.tolist()
                , t.dt.weekofyear.tolist()
                , t.dt.month.tolist()
                , t.dt.year.tolist()
                , t.dt.weekday.tolist()
                ]
    column_labels = ('start_time','hour','day','week of year','month','year','weekday')
    time_df = time_df = pd.DataFrame(time_data).T
    time_df.columns = column_labels

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[['userId', 'firstName', 'lastName', 'gender', 'level']]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():
        
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, str(row.length) + ' seconds'))
        results = cur.fetchone()
        
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = ( pd.to_datetime(row.ts,unit='ms')
                        , row.userId
                        , row.level
                        , songid
                        , artistid
                        , row.sessionId
                        , row.location
                        , row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """
    - get all files under filepath
    - count files
    - process each file using supplied function
      - process_song_file, or
      - process_log_file
    """
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """
    - get DB connection and cursor
    - process files in
      - data/song_data, and
      - data/log_data
    - close DB connection
    """
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()
    
    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)
    
    conn.close()


if __name__ == "__main__":
    main()