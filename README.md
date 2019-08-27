LMH Scripts
===

This folder contains four scripts for analyzing MathHub based on the *.tex* files in the repositories:
* `lmh_harvest.py` collects information about modules, symbols, verbalizations, ...
* `lmh_debug.py` looks for inconsistencies in the data and prints them (e.g. verbalizations for non-existent symbols)
* `lmh_stats.py` prints statistics about *smglom*
* `concept_graph.py` creates the concept graph of a lecture for TGView

The scripts do not parse *TeX* 'properly'.
Instead, they use regular expressions, which means that the parsing is very limited
and error-prone.

### Requirements

The scripts require at least Python 3.6 and have only been run on Unix systems.
No special libraries should be necessary.
The scripts are run on a local folder that contains the required repositories
from [https://gl.mathhub.info/smglom](https://gl.mathhub.info/smglom).
Note that it does not update (`pull`) the repositories automatically.
The scripts may require that the repositories follow the typical
MathHub directory structure (in particular, they should lie in a directory
called *MathHub*).


### lmh_debug.py

This script uses the code from `lmh_harvest.py` to gather data and then checks for
inconsistencies.
Depending on the verbosity, more or fewer types of errors are displayed.

Other issues that are not really considered errors can be shown with extra command line options:
* `-ma`: Show missing alignments.
* `-im`: Show missing verbalizations in all existing language files.
* `-mv`: The script prints all missing verbalizations for the languages specified after this argument,
         including if a language file is missing for a module.
         Examples with the language arguments could be `-mv en de` or `-mv all`.
* `-e`: emacs mode (different formatting of file paths, output directly opened in emacs)

Example call:
```bash
./lmh_debug.py -mv -v2 /path/to/MathHub/smglom
```

`-v2` specifies the verbosity.
The output contains general errors like:
```
Verbalization 'multiset' provided multiple times:
    /path/to/MathHub/smglom/sets/source/multiset.en.tex at 4:4
    /path/to/MathHub/smglom/sets/source/multiset.en.tex at 4:73
    /path/to/MathHub/smglom/sets/source/multiset.en.tex at 8:96
```
as well as missing verbalizations, because of the `-im` option:
```
/path/to/MathHub/smglom/mv/source/defeq.en.tex: Missing verbalizations for the following symbols: defequiv, eqdef
/path/to/MathHub/smglom/mv/source/mv.de.tex: Missing verbalizations for the following symbols: biimpl, conj, disj, exis, exisS, foral, foralS, imply, negate, nexis, nexisS, uexis, uexisS
```

Note that several directories can be passed to the script.

For more information run

```bash
./lmh_debug.py --help
```

### lmh_stats.py

This script uses the code from `lmh_harvest.py` to gather data and then prints some statistics.

Example call:
```bash
./lmh_stats.py -v0 /path/to/MathHub/smglom
```

Note that several directories can be passed to the script.

`-v0` sets the verbosity to 0, which suppresses errors during data gathering.
Note that errors can skew the statistics. For example, the percentages for each language
indicate what percentage of symbols has a verbalization in that language (ignoring symbols with `noverb` for that language).
This can be more than 100% if there are a lot of verbalizations for symbols
that are not declared in signature files.

For more information run

```bash
./lmh_stats.py --help
```

### concept_graph.py

This script is can be used to generate [TGView](https://github.com/uniformal/tgview) concept graphs of
sTeX-based lectures.
It is still under development.

Example call:
```bash
./concept_graph.py /path/to/MathHub/MiKoMH/AI/source/course/notes/notes.tex
```

The resulting graph is stored in the file `graph.json`.

### make_dictionary.py

This script creates a (multi-lingual) dictionary.

For example,
```bash
./make_dictionary.py en,de,ro /path/to/MathHub/smglom > out.tex
```
creates a dictionary from English to German and Romanian (which is written as a latex file to `out.tex`).
You can also specify individual repositories to be included:
```bash
./make_dictionary.py en,de,ro /path/to/MathHub/smglom/numbers /path/to/MathHub/smglom/sets > out.tex
```

### lmh_harvest.py

This script contains the code for collecting data.
The script can be run directly with one of the following commands:
* `repo`: Lists all repositories found.
* `defi`: Lists all the verbalizations found.
* `trefi`: Lists all the `trefi`s found.
* `symi`: Lists all the symbol declarations/definitions found.
* `sigfile`: Lists all the signature files found.
* `langfile`: Lists all the language files found.

For example, the following command
```bash
./lmh_harvest.py defi /path/to/MathHub/smglom
``` 
prints lines like the following ones:

```
/path/to/MathHub/smglom/mv/source/piecewise.de.tex at 3:28: piecewise?defined-piecewise de "st"uckweise definiert"
/path/to/MathHub/smglom/mv/source/structure.en.tex at 3:9: structure?structure en "mathematical structure"
/path/to/MathHub/smglom/mv/source/structure.en.tex at 4:7: structure?component en "component"
```

The verbosity can be changed with a command-line option (e.g. `-v1`) to reduce the number of errors
shown during the data gathering.

For more information run

```bash
./lmh_harvest.py --help
```


### Developer notes

The data collection code is in `lmh_harvest.py`.
For simple scripts (like to generate other statistcs)
which do not require changes to the data collection,
this code can be easily imported and used.

Consider the following snippet to get you started:
```python
import lmh_harvest as harvest

PATH = "../.."   # directory containing the repositories
VERBOSITY = 1

gatherer = harvest.DataGatherer()
logger = harvest.SimpleLogger(VERBOSITY)
harvest.gather_data_for_all_repos(PATH, harvest.HarvestContext(logger, gatherer))

print(gatherer.defis)       # list of dictionaries, each containing the data for one defi
print(gatherer.repos)
print(gatherer.symis)
print(gatherer.trefis)
print(gatherer.sigfiles)
print(gatherer.langfiles)
```

Please make a GitHub issue if you encounter any problems. And, of course, feel free to reach out to us!
