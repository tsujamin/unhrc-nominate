#! /usr/bin/env python3
import argparse
import sqlite3
import os
import requests
from lxml import etree
from datetime import date
from .types import *
from typing import Generator

NAMESPACES = {"marc": "http://www.loc.gov/MARC21/slim"}
SEARCH_URL = 'https://searchlibrary.ohchr.org/search?cc=Voting&ln=en&p=&f=&rm=&sf=latest+first&so=a&rg={chunk_size}&c=Voting&c=&of=xm&fct__1=Human+Rights+Council&fct__2=RECORDED&jrec={offset}'

def init_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE votes (
            resolution_name TEXT,
            country_short TEXT,
            vote TEXT,
            PRIMARY KEY (resolution_name, country_short)
        )
    """)

    cursor.execute("""
        CREATE TABLE resolutions (
            name TEXT,
            vote_date TEXT,
            summary TEXT,
            agenda TEXT,
            PRIMARY KEY (name)    
        )
    """)
    
    conn.commit()


def record_to_resolution(elem: etree.Element) -> Resolution:
    votes: Votes = OrderedDict()
    res_name = elem.xpath("marc:datafield[@tag='791']/marc:subfield[@code='a']/text()", namespaces=NAMESPACES)[0]
    res_date = date.fromisoformat(elem.xpath("marc:datafield[@tag='269']/marc:subfield[@code='a']/text()", namespaces=NAMESPACES)[0])
    summary  = "".join(elem.xpath("marc:datafield[@tag='245']/marc:subfield/text()", namespaces=NAMESPACES))
    agenda  = "".join(elem.xpath("marc:datafield[@tag='991']/marc:subfield/text()", namespaces=NAMESPACES))

    for vote_elem in elem.xpath("marc:datafield[@tag='967']", namespaces=NAMESPACES):
        country_short = vote_elem.xpath("marc:subfield[@code='b']/text()", namespaces=NAMESPACES)[0]

        if len(country_short) != 3:
            print(f'Illegal country name \'{country_short}\' in res {res_name}. Ignoring.')
            continue

        try:
            vote = Vote.from_record_value(vote_elem.xpath("marc:subfield[@code='d']/text()", namespaces=NAMESPACES)[0])
        except IndexError:
            # Vote missing from voting record
            print(f'In {res_name}, {country_short} was missing a voting intention. Overriding it to NO_VOTE')
            vote = Vote.NO_VOTE

        votes[country_short] = CountryVote(country_short, vote)

    return Resolution(res_name, res_date, summary, votes, agenda)

def get_records_page(offset: int, chunk_size: int = 100) -> list[etree.Element]:
    response = requests.get(SEARCH_URL.format(chunk_size=chunk_size, offset=offset))
    xml: etree.Element = etree.fromstring(response.content)
    
    return xml.getchildren()

def resolutions() -> Generator[Resolution]:
    chunk_size = 100
    n = 0
    while True:
        record_page = get_records_page(n, chunk_size=chunk_size)

        if len(record_page) == 0:
            break
        
        yield from map(record_to_resolution, record_page)

        n += chunk_size    

def save_resolutions(conn: sqlite3.Connection):
    for resolution in resolutions():
        cursor = conn.cursor()

        try:
            query = "INSERT INTO resolutions (name, vote_date, summary, agenda) VALUES (?, ?, ?, ?)"
            cursor.execute(query, (resolution.name, resolution.date.strftime("%Y/%m/%d"), resolution.summary, resolution.agenda))
        except sqlite3.IntegrityError:
            print(f"Resolution {resolution.name} already in the resolutions table, is it a duplicate? Rolling back")
            conn.rollback()
            continue
            
        for country_short, vote in resolution.votes.items():
            query = "INSERT INTO votes (resolution_name, country_short, vote) VALUES (?, ?, ?)"
            try:
                cursor.execute(query, (resolution.name, country_short, vote.vote.name))
            except sqlite3.IntegrityError:
                print(f"Vote already in votes table for {country_short} on res {resolution.name}, is it a duplicate? Ignoring")

        conn.commit()

def main(db_filename: str):
    if os.path.exists(db_filename):
        os.remove(db_filename)

    conn = sqlite3.connect(db_filename)

    init_schema(conn)
    save_resolutions(conn)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape the UN HRC vote records into an sqlite3 database")
    parser.add_argument("db_filename", nargs='?', default='votes.sqlite3', help="the name of the SQLite database file to write", )
    parser.add_argument("-f", "--force", action="store_true", help="replace existing database file")

    args = parser.parse_args()

    if os.path.exists(args.db_filename) and not args.force:
        raise FileExistsError(f"Database file {args.db_filename} already exists.")

    main(args.db_filename)