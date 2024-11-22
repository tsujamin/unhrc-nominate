#! /usr/bin/env python
import os
import sqlite3
from datetime import datetime
from argparse import ArgumentParser
from .types import *
from typing import Generator, Tuple


def get_resolution_countries(conn: sqlite3.Connection, resolution_name: str) -> list[CountryShortName]:
    c = conn.cursor()
    query = "SELECT country_short FROM votes WHERE resolution_name = ?"
    c.execute(query, (resolution_name,))
    
    return list(sorted(set([row[0] for row in c.fetchall()])))

def resolutions(conn: sqlite3.Connection) -> Generator[Tuple[ResolutionName, date, list[CountryShortName]], None, None]:
    """Returns each resolution, in date ascending order, and countries that voted on it"""
    c = conn.cursor()
    query = "SELECT name, vote_date FROM resolutions ORDER BY vote_date ASC"
    c.execute(query)
    
    for row in c.fetchall():
        yield (row[0], datetime.strptime(row[1], "%Y/%m/%d").date(), get_resolution_countries(conn, row[0]))

def calculate_sessions(conn: sqlite3.Connection) -> Generator[Session]:
    session_idx = 1

    session_cache: dict[str, Session] = {}
    last_country_key: str = None

    for resolution, voted_date, countries in resolutions(conn):
        country_key = '|'.join(countries)

        # This check confirms that no set of countries is seen again after a change of membership
        # This should catch cases where a particular vote in a particular session forgot to include a voter
        # E.g. this catches [a,b,c] -> [a,b] -> [a,b,c]
        if last_country_key != country_key and country_key in session_cache:
            breakpoint()

        if country_key not in session_cache:
            print(f'New UNHRC session #{session_idx} on {voted_date}, Resolution {resolution}, Members ' + ', '.join(countries))
            
            new_session = Session(session_idx, set(countries), set(), voted_date, last_vote=None)

            session_cache[country_key] = new_session
            session_idx += 1

        session_cache[country_key].last_vote = voted_date
        session_cache[country_key].resolutions.add(resolution)
        last_country_key = country_key

    for session in session_cache.values():
        yield session

def save_session(conn: sqlite3.Connection, session: Session):
    breakpoint()

def clear_tables(conn: sqlite3.Connection):
    """Clears the contents of the Session_Member, Sessions and Country tables."""
    cursor = conn.cursor()
    
    # Clear Session_Member table
    query = "DELETE FROM session_members"
    cursor.execute(query)
    
    # Clear Sessions table
    query = "DELETE FROM sessions"
    cursor.execute(query)
    
    # Clear Country table
    query = "DELETE FROM countries"
    cursor.execute(query)
    
    conn.commit()

def update_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    query = """
        CREATE TABLE IF NOT EXISTS countries (
            country_short TEXT PRIMARY KEY,
            country_long TEXT,
            polarity TEXT
        );
    """
    cursor.execute(query)

    query = """
        CREATE TABLE IF NOT EXISTS sessions (
            session_number INTEGER PRIMARY KEY AUTOINCREMENT,
            first_vote TEXT,
            last_vote TEXT
        );
    """
    cursor.execute(query)   

    query = """
        CREATE TABLE IF NOT EXISTS session_members (
            session_number INTEGER,
            country_short TEXT,
            PRIMARY KEY (session_number, country_short),
            FOREIGN KEY (country_short) REFERENCES Country(country_short)
        );
    """
    cursor.execute(query)   

    query = """
        CREATE TABLE IF NOT EXISTS resolutions (
            resolution_name TEXT PRIMARY KEY,
            first_session_number INTEGER,
            last_session_number INTEGER
        );
    """
    cursor.execute(query)   

    # Add session number column if it doesn't exist
    query = "SELECT COUNT(*) FROM resolutions"
    cursor.execute(query)
    try:
        query = "ALTER TABLE resolutions ADD COLUMN IF NOT EXIST session_number INTEGER;"
        cursor.execute(query)
    except:
        pass
    conn.commit()


def main(db_filename: str):
    conn = sqlite3.connect(db_filename)

    update_schema(conn)
    clear_tables(conn)

    for session in calculate_sessions(conn):
        save_session(conn, session)


if __name__ == "__main__":
    parser = ArgumentParser(description='A dummy main method')
    parser.add_argument("db_filename", nargs='?', default='votes.sqlite3', help="the name of the SQLite database file to process")
    args = parser.parse_args()

    if not os.path.exists(args.db_filename):
        raise FileNotFoundError(f"Database file {args.db_filename} not found.")

    main(args.db_filename)
