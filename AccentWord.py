import random

Dict = open("Data/dictionary.txt", encoding="utf8").readlines()
Vowels = ['а', 'о', 'и', 'ы', 'у', 'э', 'е', 'ё', 'ю', 'я']
AccentVomels = ['а́', 'о́', 'и́', 'ы́', 'у́', 'э́', 'е́', 'ё', 'ю́', 'я́']


def AddAccent(word, index):
    fixaccent = word[index].replace("ё", "е")
    return word[:index] + AccentVomels[Vowels.index(fixaccent)] + word[index + 1:]


def GenerateAccents():
    word = Dict[random.randint(0, len(Dict) - 1)].rstrip()
    correct_accent = [idx for idx in range(len(word)) if word[idx].isupper()][0]
    word = word.lower()
    correct_word = AddAccent(word, correct_accent)
    variations = []
    for i in range(len(word)):
        if word[i] in Vowels:
            variations.append(AddAccent(word, i))

    return {"CorrectWord": correct_word, "VariationsArray": variations}
