# UNHRC-Nominate

## Generating the dataset
```bash
$ python -m pyunhrcnominate.scrape [-f]
$ python -m pyunhrcnominate.enrich examples/category-oecd.csv
$ python -m pyunhrcnominate.export [--match keyword1 orkeyword2]
```