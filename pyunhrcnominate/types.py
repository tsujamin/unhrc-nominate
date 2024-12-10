from enum import Enum
from datetime import date
from dataclasses import dataclass
from collections import OrderedDict

class Vote(Enum):
    NO             = 0
    YES            = 1
    ABSTAIN        = 2
    NO_VOTE        = 3
    NOT_IN_SESSION = 4

    @staticmethod
    def from_record_value(val: str) -> 'Vote':
        match val.upper():
            case 'NO': return Vote.NO
            case 'N': return Vote.NO
            case 'YES': return Vote.YES
            case 'Y': return Vote.YES
            case 'ABSTAIN': return Vote.ABSTAIN
            case 'A': return Vote.ABSTAIN
            case 'NO_VOTE': return Vote.NO_VOTE
            case '.': return Vote.NO_VOTE
            case _: breakpoint()

class ResolutionType(Enum):
    DECISION = 'decision'
    RESOLUTION = 'resolution'
    AMENDMENT  = 'amendment'

    @staticmethod
    def from_resolution_id(id: str) -> 'ResolutionType':
         # Ends with L.NNN, limited distribution document voted on, likely amendment to existing resolution
        if id.split('/')[-1].lower().startswith("l."):
            return ResolutionType.AMENDMENT
        elif '/hrc/res' in id.lower():
            return ResolutionType.RESOLUTION
        elif '/hrc/dec' in id.lower():
            return ResolutionType.DECISION
        else:
            raise Exception(f"unknown resolution type for id {id}")
        
CountryShortName = str

@dataclass
class CountryVote():
    country: CountryShortName
    vote: Vote

Votes = OrderedDict[CountryShortName, CountryVote]

@dataclass
class Resolution:
    name: str
    date: date
    summary: str
    votes: OrderedDict[CountryShortName, Vote]
    agenda: str

    def session(self) -> 'Session':
        for session in Session._generate():
            if self.date >= session.start_date and self.date <= session.end_date:
                return session
            
        raise Exception(f'missing session for resolution {self.name} ({self.date})')

    def passed(self) -> bool:
        votes = [cv.vote for cv in self.votes.values()]

        return len([v for v in votes if v == Vote.YES]) > len([v for v in votes if v == Vote.NO])
            
    def resolution_type(self) -> ResolutionType:
        return ResolutionType.from_resolution_id(self.name)

@dataclass
class Country:
    short_name: CountryShortName
    long_name: str
    category: str

@dataclass
class Session:
    start_date: date
    end_date: date

    @staticmethod
    def _generate():
        # 2006->2011: 19 June->18 June
        for year in range(2006, 2011):
            yield Session(date(year, 6, 19), date(year+1, 6, 18))

        # 2011 was rounded to the end of 2012
        yield Session(date(2011,6,19), date(2012,12,31))

        # 2012 -> 2024 are round calendar years
        for year in range(2012, 2025):
            yield Session(date(year, 1, 1), date(year, 12, 31))

    def label(self) -> str:
        return str(self.start_date.year)