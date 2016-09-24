import module_bullshit
from module_bullshit.parser import LanguageParser


my_parser = LanguageParser()

with open("sample.code", "r") as f:
    result = my_parser.parse(f.read())
    print(result)
