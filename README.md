SMGLOM Scripts
===

This folder contains three scripts for analyzing *smglom* based on the *.tex* files in the repositories:
* `smglom_harvest.py` collects information about modules, symbols, verbalizations, ...
* `smglom_debug.py` looks for inconsistencies in the data and prints them (e.g. verbalizations for non-existent symbols)
* `smglom_stats.py` prints statistics about *smglom*

### Requirements

The scripts require at least Python 3.6 and have only been run on Unix systems.
The scripts are run on a local folder that contains the required repositories
from [https://gl.mathhub.info/smglom](https://gl.mathhub.info/smglom).
It does not update (`pull`) the repositories automatically.


### smglom_harvest.py

This script contains the code for collecting data.
The script can be run directly with one of the following commands:
* `defi`: Lists all the verbalizations found.
* `trefi`: Lists all the `trefi`s found.
* `symi`: Lists all the symbol declarations/definitions found.
* `sigfile`: Lists all the signature files found.
* `langfile`: Lists all the language files found.

For example, the following command (where `../..` is the folder containing all the repositories):

```bash
./smglom_harvest.py defi ../..
```

Prints lines like the following ones:

```
../../mv/source/piecewise.de.tex at 3:28: piecewise?defined-piecewise de "st"uckweise definiert"
../../mv/source/structure.en.tex at 3:9: structure?structure en "mathematical structure"
../../mv/source/structure.en.tex at 4:7: structure?component en "component"
```

The verbosity can be changed with a command-line option (e.g. `-v1`) to reduce the number of errors
shown during the data gathering.

### smglom_debug.py

This script uses the code from `smglom_harvest.py` to gather data and then checks for
inconsistencies.
Depending on the verbosity, more or fewer types of errors are displayed.

Missing verbalizations can be displayed with extra command line options:
* `-mvx`: Show missing verbalizations in all language files.
* `-mv-...`: `...` should be a language like `en` or `de`.
        The script then prints all missing verbalizations for the language,
        even if no language file for a module has been created yet.

Example call:
```bash
./smglom_debug.py -mvx -v2 ../..
```

`-v2` specifies the verbosity.
The output contains general errors like:
```
Verbalization 'multiset' provided multiple times:
    ../../sets/source/multiset.en.tex at 4:4
    ../../sets/source/multiset.en.tex at 4:73
    ../../sets/source/multiset.en.tex at 8:96
```
as well as missing verbalizations, because of the `-mvx` option:
```
../../mv/source/defeq.en.tex: Missing verbalizations for the following symbols: defequiv, eqdef
../../mv/source/mv.de.tex: Missing verbalizations for the following symbols: biimpl, conj, disj, exis, exisS, foral, foralS, imply, negate, nexis, nexisS, uexis, uexisS
```

### smglom_stats.py

This script uses the code from `smglom_harvest.py` to gather data and then prints some statistics.

Example call:
```bash
./smglom_stats.py -v0 ../..
```

`-v0` suppresses errors during data gathering.
Note that errors can skew the statistics. For example, the percentages for each language
indicate what percentage of symbols has a verbalization in that language.
This can be more than 100% if there are a lot of verbalizations for symbols
that are not declared in signature files.

### Developer notes

The data collection code is in `smglom_harvest.py`.
For simple scripts (like for the generation of other statistics),
you might want to simply import it and then use only the collected data.
To get you started, take a look at the following example script:

```python
import smglom_harvest as harvest

PATH = "../.."   # directory containing the repositories
VERBOSITY = 1

gatherer = harvest.DataGatherer()
harvest.gather_stats_for_all_repos(PATH, harvest.HarvestContext(VERBOSITY, gatherer))

print(gatherer.defis)       # list of dictionaries, each containing the data for one defi
print(gatherer.symis)
print(gatherer.trefis)
print(gatherer.sigfiles)
print(gatherer.langfiles)
```
