"""
Very experimental tool to generate a GF (Grammatical Framework) Lexicon from SMGloM
"""

import lmh_harvest as harvest
import sys


directories = sys.argv[1:]
mathhub_dir = harvest.get_mathhub_dir(directories[0])
ctx = harvest.HarvestContext(harvest.SimpleLogger(2), harvest.DataGatherer(), mathhub_dir)

for directory in directories:
    harvest.gather_data_for_all_repos(directory, ctx)

symi_dict = {}
for symi in ctx.gatherer.symis:
    symb = symi["mod_name"].replace("-", "_") + "_" + symi["name"].replace("-", "_")
    if "gfc" in symi["params"]:
        symi_dict[symb] = symi["params"]["gfc"]

def umlautSubst(s):
    return s.replace("\"a", "ä")\
            .replace("\"o", "ö")\
            .replace("\"u", "ü")\
            .replace("\"A", "Ä")\
            .replace("\"O", "Ö")\
            .replace("\"U", "Ü")\
            .replace("\"s", "ß")

results = {}
for defi in ctx.gatherer.defis:
    lang = defi["lang"] 
    if lang not in ["de", "en"]:
        continue
    symb = defi["mod_name"].replace("-", "_") + "_" + defi["name"].replace("-", "_")

    if symb not in results:
        results[symb] = {"en" : [], "de" : [], "abstr" : None, "trueName" : None}

    if symb in symi_dict:
        gfc = symi_dict[symb]
    else:
        gfc = None

    if gfc == "N" or gfc == None:
        trueName = symb + "_RN0"
        abstr = " "*8 + trueName + " : RawNoun0 ;\n"
        make = "mkCN (mkN \"" + umlautSubst(defi["string"]) + "\")"
    elif gfc == "A":
        trueName = symb + "_Adj0"
        abstr = " "*8 + trueName + " : RawAdjective0 ;\n"
        make = "mkA \"" + umlautSubst(defi["string"]) + "\""
    else:
        continue
    
    if not ( results[symb]["abstr"] == None or results[symb]["abstr"] == abstr ):
        print(results[symb]["abstr"], "vs", abstr, "with", symb)
    results[symb]["abstr"] = abstr
    results[symb]["trueName"] = trueName

    if make not in results[symb][lang]:
        results[symb][lang].append(make)

abstract = """-- automatically generated lexicon, based on smglom
abstract SmglomLexicon = ForthelCat, ForthelNotions, ForthelTerms, ForthelPredicates ** {
    fun
"""


english = """--# -path=.:../functor:../abstract

concrete SmglomLexiconEng of SmglomLexicon = ForthelCatEng, ForthelNotionsEng, ForthelTermsEng, ForthelPredicatesEng ** open ParadigmsEng, ConstructorsEng, StructuralEng in {
    lin
"""

german = """--# -path=.:../functor:../abstract

concrete SmglomLexiconGer of SmglomLexicon = ForthelCatGer, ForthelNotionsGer, ForthelTermsGer, ForthelPredicatesGer ** open ParadigmsGer, ConstructorsGer, StructuralGer in {
    lin
"""



for result in sorted((r for r in results.values() if r["trueName"]), key=lambda r : r["trueName"]):
    if len(result["de"]) == 0 or len(result["en"]) == 0:
        continue

    abstract += result["abstr"]
    german += " "*8 + result["trueName"] + " = " + " | ".join(result["de"]) + " ;\n"
    english += " "*8 + result["trueName"] + " = " + " | ".join(result["en"]) + " ;\n"

abstract += "}\n"
german += "}\n"
english += "}\n"

with open("/tmp/SmglomLexicon.gf", "w") as fp:
    fp.write(abstract)

with open("/tmp/SmglomLexiconEng.gf", "w") as fp:
    fp.write(english)

with open("/tmp/SmglomLexiconGer.gf", "w") as fp:
    fp.write(german)

