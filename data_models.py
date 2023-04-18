from dataclasses import dataclass

# (word, frequency), translation
@dataclass
class OneToOneRecord:
    word: str
    frequency: int
    translation: str
