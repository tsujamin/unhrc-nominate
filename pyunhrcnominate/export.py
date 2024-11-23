import argparse
import sqlite3
import os
import csv
from datetime import datetime
from .types import *
from typing import Generator
from collections import OrderedDict

def get_votes_by_resolution(conn: sqlite3.Connection, resolution_name: str) -> OrderedDict[CountryVote]:
    cursor = conn.cursor()
    query = "SELECT country_short, vote FROM votes WHERE resolution_name = ?"
    cursor.execute(query, (resolution_name,))
    rows = cursor.fetchall()

    return OrderedDict({country[0]: CountryVote(country[0], Vote.from_record_value(country[1])) for country in rows})

def resolutions(conn: sqlite3.Connection) -> Generator[Resolution]:
    cursor = conn.cursor()
    query = "SELECT name, vote_date, summary FROM resolutions order by vote_date asc"
    cursor.execute(query)

    for (name, vote_date, summary) in cursor.fetchall():
        yield Resolution(name, datetime.strptime(vote_date, "%Y/%m/%d"), summary, get_votes_by_resolution(conn, name))

def get_countries(conn: sqlite3.Connection) -> Generator[Country]:
    cursor = conn.cursor()
    query = "SELECT country_short, country_long, category FROM countries"
    cursor.execute(query)

    for (country_short, country_long, category) in cursor.fetchall():
        yield Country(country_short, country_long, category)


def countries_for_resolutions(resolutions: list[Resolution]) -> list[CountryShortName]:
    countires = set()

    for res in resolutions:
        for country in res.votes.keys():
            countires.add(country)

    return list(sorted(countires))

def write_votes(filename: str, resolutions: list[Resolution], countries: list[CountryShortName]):
    # Each row is a voter, in alphabetical order
    # Each column is a vote, in the order of the votes list
    # Each cell is the integer value corresponding to the vote decision
    with open(filename, 'w') as f:
        csv_out = csv.writer(f, dialect=csv.excel)
        csv_out.writerow(['Country'] + [r.name for r in resolutions])

        # For each country, 
        for country in countries:
            row = [country]

            for res in resolutions:
                if country in res.votes:
                    # If the country actually was in this HRC session, then record their Y/N/A/Missing vote. 
                    row.append(str(res.votes[country].vote.value))
                else:
                    # Append not-present
                    row.append(str(Vote.NOT_IN_SESSION.value))
            
            csv_out.writerow(row)

def write_vote_data(filename: str, resolutions: list[Resolution]):
    with open(filename, 'w') as f:
        csv_out = csv.writer(f, dialect=csv.excel)
        csv_out.writerow(['Resolution', 'Date', 'Summary'])

        for res in resolutions:
            csv_out.writerow([res.name, res.date.strftime("%Y/%m/%d"), res.summary])

def write_country_data(filename, countries: list[Country]):
    with open(filename, 'w') as f:
        csv_out = csv.writer(f, dialect=csv.excel)
        csv_out.writerow(['Country', 'Country Long', 'party']) # dwnominate needs a "party" column in the legislator dataframe

        for country in countries:
            csv_out.writerow([country.short_name, country.long_name, country.category])


def export(prefix: str, resolutions: list[Resolution], all_countries: list[Country]):
    resolution_country_names = countries_for_resolutions(resolutions)

    # Ensure that resolution_countries is in the same order as resolution_country_names
    all_countries = {c.short_name: c for c in all_countries}
    resolution_countries = [all_countries[c] for c in resolution_country_names] 

    write_votes(f'{prefix}-votes.csv', resolutions, resolution_country_names)
    write_vote_data(f'{prefix}-vote-data.csv', resolutions)
    write_country_data(f'{prefix}-legis-data.csv', resolution_countries)


def main(output_dir: str, db_name: str, keywords: list[str] = []):
    import sqlite3
    conn = sqlite3.connect(db_name)

    filtered_resolutions: list[Resolution] = []

    # Filter down based on keywords (if any)
    for res in resolutions(conn):
        lower_res = res.summary.lower()
        matched = len(keywords) == 0
        for kw in keywords:
            if kw.lower() in lower_res:
                matched = True
                break

        if matched:
            filtered_resolutions.append(res)

    batches: dict[str, list[Resolution]] = {}
    batches['all'] = filtered_resolutions
    
    # Batch resolutions by year
    for res in filtered_resolutions:
        year = str(res.date.year)

        if year in batches:
            batches[year].append(res)
        else:
            batches[year] = [res]

    # Read in the country table
    all_countries = list(get_countries(conn))

    for batch, resolution_batch in batches.items():
        export(f'{output_dir}/{batch}', resolution_batch, all_countries)

    conn.close()

def make_output_dir(keywords: list[str] = []) -> str:
    try:
        os.mkdir("output")
    except:
        pass

    datetime.now().strftime("%y%m%d-%H%M%S")

    folder_parts = [datetime.now().strftime("%y%m%d-%H%M%S")]
    folder_parts += keywords
    out_folder = "output/" + "-".join(folder_parts)

    os.mkdir(out_folder)
    
    return out_folder

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite Database Manager")
    parser.add_argument("db_filename", nargs="?", default='votes.sqlite3', help="Name of the SQLite database file to connect to.")
    parser.add_argument("--match", nargs="+", default=[], help="Simmary keywords to filter resolutions on")

    args = parser.parse_args()

    if not os.path.exists(args.db_filename):
        raise FileNotFoundError(f"Database file {args.db_filename} not found.")

    out_dir = make_output_dir(args.match)

    print(f"created output directory {out_dir}")

    main(out_dir, args.db_filename, args.match)
