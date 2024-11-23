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

@dataclass
class Country:
    short_name: CountryShortName
    long_name: str
    category: str