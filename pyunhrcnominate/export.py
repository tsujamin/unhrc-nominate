import argparse
import sqlite3
import os
import csv
import jinja2
from datetime import datetime
from .types import *
from typing import Generator
from collections import OrderedDict
from abc import ABC

class Args(ABC):
    db_filename: str
    title_match: list[str]
    agenda_match: list[str]
    abstain_is_no_vote: bool
    missing_is_no_vote: bool
    only_passed: bool
    only_failed: bool
    only_amendments: bool
    only_resolutions: bool


def get_votes_by_resolution(conn: sqlite3.Connection, resolution_name: str) -> OrderedDict[CountryVote]:
    cursor = conn.cursor()
    query = "SELECT country_short, vote FROM votes WHERE resolution_name = ?"
    cursor.execute(query, (resolution_name,))
    rows = cursor.fetchall()

    return OrderedDict({country[0]: CountryVote(country[0], Vote.from_record_value(country[1])) for country in rows})

def resolutions(conn: sqlite3.Connection) -> Generator[Resolution]:
    cursor = conn.cursor()
    query = "SELECT name, vote_date, summary, agenda FROM resolutions order by vote_date asc"
    cursor.execute(query)

    for (name, vote_date, summary, agenda) in cursor.fetchall():
        yield Resolution(name, datetime.strptime(vote_date, "%Y/%m/%d").date(), summary, get_votes_by_resolution(conn, name), agenda)

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

def write_r_script(filename: str):
    with open(f'{os.path.dirname(__file__)}/dwnominate.r.tmpl') as tf:
        tmpl = jinja2.Template(tf.read())

    with open(filename, "w") as f:

        f.write(tmpl.render(output_directory=os.path.abspath(os.path.dirname(filename).replace("\\", "\\\\"))))



def export(prefix: str, resolutions: list[Resolution], all_countries: list[Country]):
    resolution_country_names = countries_for_resolutions(resolutions)

    # Ensure that resolution_countries is in the same order as resolution_country_names
    all_countries = {c.short_name: c for c in all_countries}
    resolution_countries = [all_countries[c] for c in resolution_country_names] 

    write_votes(f'{prefix}-votes.csv', resolutions, resolution_country_names)
    write_vote_data(f'{prefix}-vote-data.csv', resolutions)
    write_country_data(f'{prefix}-legis-data.csv', resolution_countries)

def main(output_dir: str, args: Args):
    import sqlite3
    conn = sqlite3.connect(args.db_filename)

    filtered_resolutions: list[Resolution] = []

    for res in resolutions(conn):
        # Map abstain/missing to no if required
        for country_vote in res.votes.values():
            if args.abstain_is_no_vote and country_vote.vote == Vote.ABSTAIN:
                country_vote.vote = Vote.NO

            if args.missing_is_no_vote and country_vote.vote == Vote.NOT_IN_SESSION:
                country_vote.vote = Vote.NO

        # Filter down based on keywords (if any)
        lower_res = res.summary.lower()
        matched = (len(args.title_match) + len(args.agenda_match)) == 0
        for kw in args.title_match:
            if kw.lower() in lower_res:
                matched = True
                break

        for kw in args.agenda_match:
            if kw.lower() in lower_res:
                matched = True
                break

        if matched:
            filtered_resolutions.append(res)

    if args.only_passed:
        filtered_resolutions = [r for r in filtered_resolutions if r.passed()]
    
    if args.only_failed:
        filtered_resolutions = [r for r in filtered_resolutions if not r.passed()]

    if args.only_amendments:
        filtered_resolutions = [r for r in filtered_resolutions if r.resolution_type() == ResolutionType.AMENDMENT]

    if args.only_resolutions:
        filtered_resolutions = [r for r in filtered_resolutions if r.resolution_type() == ResolutionType.RESOLUTION]

    batches: dict[str, list[Resolution]] = {}
    batches['all'] = filtered_resolutions
    
    # Batch resolutions by year
    for res in filtered_resolutions:
        session = res.session().label()

        if session in batches:
            batches[session].append(res)
        else:
            batches[session] = [res]

    # Read in the country table
    all_countries = list(get_countries(conn))

    for batch, resolution_batch in batches.items():
        export(f'{output_dir}/{batch}', resolution_batch, all_countries)

    write_r_script(f'{output_dir}/plot.R')

    conn.close()

def make_output_dir(args: Args) -> str:
    try:
        os.mkdir("output")
    except:
        pass

    datetime.now().strftime("%y%m%d-%H%M%S")

    folder_parts = [datetime.now().strftime("%y%m%d-%H%M%S")]
    folder_parts += args.title_match
    folder_parts += args.agenda_match

    if args.abstain_is_no_vote:
        folder_parts.append("abstainisno")

    if args.missing_is_no_vote:
        folder_parts.append("missingisno")

    if args.only_passed:
        folder_parts.append("onlypassed")

    if args.only_failed:
        folder_parts.append("onlyfailed")

    if args.only_amendments:
        folder_parts.append("onlyamendments")

    if args.only_resolutions:
        folder_parts.append("onlyresolutions")

    out_folder = "output/" + "-".join(folder_parts)

    os.mkdir(out_folder)
    
    return out_folder

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite Database Manager")
    parser.add_argument("db_filename", nargs="?", default='votes.sqlite3', help="Name of the SQLite database file to connect to.")
    parser.add_argument("--title-match", nargs="+", default=[], help="Simmary keywords to filter resolution titles on")
    parser.add_argument("--agenda-match", nargs="+", default=[], help="Simmary keywords to filter resolution agendas on")
    parser.add_argument('--abstain-is-no-vote', action="store_true", default=False)
    parser.add_argument('--missing-is-no-vote', action="store_true", default=False)
    parser.add_argument('--only-passed', action="store_true", default=False)
    parser.add_argument('--only-failed', action="store_true", default=False)
    parser.add_argument('--only-amendments', action="store_true", default=False)
    parser.add_argument('--only-resolutions', action="store_true", default=False)

    args = parser.parse_args()

    if not os.path.exists(args.db_filename):
        raise FileNotFoundError(f"Database file {args.db_filename} not found.")

    out_dir = make_output_dir(args)

    print(f"created output directory {out_dir}")

    main(out_dir, args)
