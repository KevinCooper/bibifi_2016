import interpreter_scripts
from interpreter_scripts.parser import LanguageParser


my_parser = LanguageParser()

with open("sample_whitespace.code", "r") as f:
    result = my_parser.parse(f.read())
    print(result)
