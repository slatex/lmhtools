import smglom_harvest as harvest
import sys

PATH = sys.argv[1]
VERBOSITY = 1

gatherer = harvest.DataGatherer()
logger = harvest.SimpleLogger(VERBOSITY)
harvest.gather_data_for_all_repos(PATH, harvest.HarvestContext(logger, gatherer))

for symi in gatherer.symis:
    if "gfc" in symi["params"]:
        print("I found a symi with gfc:")
        print("  ", symi)

for defi in gatherer.defis:
    if "gfa" in defi["params"]:
        print("I found a defi with gfa:")
        print("  ", defi)

