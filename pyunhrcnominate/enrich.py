#! /usr/bin/env python
import os
import sqlite3
from datetime import datetime
from argparse import ArgumentParser
from .types import *
import csv
import iso3166
from collections import defaultdict

CategoryMap = defaultdict[CountryShortName, str]

def update_schema_and_clean(conn: sqlite3.Connection):
    cursor = conn.cursor()
    query = """
        CREATE TABLE IF NOT EXISTS countries (
            country_short TEXT PRIMARY KEY,
            country_long TEXT,
            category TEXT
        );
    """
    cursor.execute(query)

    # Clear Country table
    query = "DELETE FROM countries"
    cursor.execute(query)

    conn.commit()

def save_country(conn: sqlite3.Connection, country: Country):
    """Saves the country to the countries table with an sqlite3 conn."""
    cursor = conn.cursor()
    query = """
        INSERT INTO countries (country_short, country_long, category)
        VALUES (?, ?, ?);
    """
    cursor.execute(query, (country.short_name, country.long_name, country.category))
    conn.commit()


def load_category_map(filename: str) -> CategoryMap:
    with open(filename, "r") as f:
        category_csv = csv.DictReader(f, dialect=csv.excel, skipinitialspace=True)

        cmap = {r["Country"]: r["Category"].strip() for r in category_csv}

        default_value = cmap.get('_', 'MISSING')

        return defaultdict(lambda: default_value, cmap)


def countries(conn: sqlite3.Connection, categories: CategoryMap):
    cursor = conn.cursor()
    
    query = "SELECT country_short FROM votes GROUP BY country_short"
    cursor.execute(query)
    
    for (short_name,) in cursor.fetchall():
        yield Country(
            short_name,
            iso3166.countries_by_alpha3[short_name].name,
            categories[short_name]
        )

def main(db_filename: str, category_filename: str):
    conn = sqlite3.connect(db_filename)

    update_schema_and_clean(conn)

    map = load_category_map(category_filename)

    for country in countries(conn, map):
        save_country(conn, country)


if __name__ == "__main__":
    parser = ArgumentParser(description='A dummy main method')
    parser.add_argument("db_filename", nargs='?', default='votes.sqlite3', help="the name of the SQLite database file to process")
    parser.add_argument("category_file", help="the name of the CSV file that maps country codes to categories")

    args = parser.parse_args()

    if not os.path.exists(args.db_filename):
        raise FileNotFoundError(f"Database file {args.db_filename} not found.")
    
    if not os.path.exists(args.category_file):
        raise FileNotFoundError(f"Category file {args.category_file} not found.")

    main(args.db_filename, args.category_file)
