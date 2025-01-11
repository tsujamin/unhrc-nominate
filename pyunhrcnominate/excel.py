from .types import *
from .export import resolutions, get_countries
from dataclasses import dataclass
import csv
import argparse

@dataclass
class Args:
    db_filename: str

def main(args: Args):
    import sqlite3
    conn = sqlite3.connect(args.db_filename)

    # Get the list of countries, grouped by their category
    country_map: dict[str, list[CountryShortName]] = {}

    for country in get_countries(conn):
        if country.category not in country_map:
            country_map[country.category] = []

        country_map[country.category].append(country.short_name)
    
    # Sort each country list
    country_map = OrderedDict({cat: list(sorted(countries)) for cat, countries in country_map.items()})

    # Open the output file
    f = open("/tmp/out.csv", "w")
    w = csv.writer(f, dialect="excel")

    # Write headers. Format is resolution_headers, empty, category, ...country
    headers = ["Name", "Type", "Start of Session", "Date", "Summary", "Agenda", "Passed", "Yes", "No", "Abstain", "Missing"]
    for category, countries in country_map.items():
        headers += ["", category] + [c for c in countries]

    w.writerow(headers)

    for resolution in resolutions(conn):
        row = [resolution.name, resolution.resolution_type().value, resolution.session().start_date, resolution.date, resolution.summary, resolution.agenda, resolution.passed()]

        # Write vote tallies
        for vote_type in [Vote.YES, Vote.NO, Vote.ABSTAIN, Vote.NO_VOTE]:
            row.append(len([v for v in resolution.votes.values() if v.vote == vote_type]))

        # Write individual countries votes
        for category, countries in country_map.items():
            row += ["", category]
            for country in countries:
                if country in resolution.votes:
                    row.append(resolution.votes[country].vote.name)
                else:
                    row.append(Vote.NOT_IN_SESSION.name)

        w.writerow(row)
    
    f.close()

    print("See /tmp/out.csv")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="export to excel")
    parser.add_argument("db_filename", nargs="?", default='votes.sqlite3', help="Name of the SQLite database file to connect to.")

    main(parser.parse_args())