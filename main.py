import itertools
import time
from collections import deque

from reverso_api.context import ReversoContextAPI

# The aim is to find words which have a very clear 1-to-1 between the source and target languages.
# Here, 1-to-1 translation means that both words are each other's most frequent translation.
# The words to be translated are gathered from the context sentences of the words previously processed.


# TODO
#  - Save one-to-one translations to a file
#  - Compare words against translations from the same part of speech
#  - Add only lemmatized words to the pool of words to translate
#  - Add back translations to the pool of words to translate
#  - Add a check for 1-to-1 translations in the other direction


def check_one_to_one(word, top_translation, source_lang, target_lang):
    # Source and target languages have to be swapped
    reverso_context_api = ReversoContextAPI(
        source_text=top_translation,
        source_lang=target_lang,
        target_lang=source_lang,
    )
    back_translation_objects = list(reverso_context_api.get_translations())
    back_translation_strings = [t.translation for t in back_translation_objects]
    # print(
    #     f"Back translations for {top_translation}: {' '.join(back_translation_strings)}\n"
    # )
    if back_translation_strings:
        top_back_translation = back_translation_strings[0]
        if top_back_translation == word:
            return True
    return False


def clean_up_words(words):
    # Remove punctuation
    words = [word.strip(",.?!") for word in words]
    # Decapitalize
    words = [word.lower() for word in words]
    return words


def get_words_from_context_sentences(context_api: ReversoContextAPI):
    context_sentences = context_api.get_examples()
    words = set()
    # Get source language words from context sentences
    sentence_count = 10
    limited_context_sentences = itertools.islice(context_sentences, sentence_count)
    for context_sentence in limited_context_sentences:
        source_text = context_sentence[0].text
        cleaned_words = clean_up_words(source_text.split())
        words.update(cleaned_words)
    # print(f"Words to translate: {' '.join(words)}\n")
    return words


def run(start_word, source_lang, target_lang, iteration_count):
    print("Starting word: " + start_word)
    print()

    SLEEP_TIME = 1
    REPORT_INTERVAL = 25

    # Each word has a key in a dictionary. The value is a list of Translation namedtuples.
    translations = {}
    # Note 1-to-1 translations
    one_to_one = {}
    # A pool of words is established
    words_to_translate = deque()
    # Words already scraped
    scraped_words = set()

    current_word = start_word

    for i in range(iteration_count):
        context_api = ReversoContextAPI(
            source_text=current_word,
            source_lang=source_lang,
            target_lang=target_lang,
        )

        # Get translations
        translation_objects = list(context_api.get_translations())
        translation_strings = [t.translation for t in translation_objects]
        # print(f"Translations for {current_word}: {' '.join(translation_strings)}\n")
        translations[current_word] = translation_objects

        # Check if the word has a 1-to-1 translation
        top_translation = translation_strings[0] if translation_strings else None
        if top_translation and check_one_to_one(
            current_word, top_translation, source_lang, target_lang
        ):
            one_to_one[current_word] = top_translation
            print(f"1-to-1: {current_word} -> {top_translation}")

        # Add new words to the pool
        batch_of_words = get_words_from_context_sentences(context_api)
        new_words = set(batch_of_words) - scraped_words
        words_to_translate.extend(new_words)
        scraped_words.update(new_words)

        # Set the next word to translate
        current_word = words_to_translate.popleft()
        # print(f"Next word: {current_word}\n")

        # Report progress
        if i % REPORT_INTERVAL == 0:
            print()
            print(f"Iteration {i}")
            print(f"Words to translate: {len(words_to_translate)}")
            print(f"Scraped words: {len(scraped_words)}")
            print(f"One-to-one translations: {len(one_to_one)}")
            print()
        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    start_word = "желание"
    source_lang = "ru"
    target_lang = "en"
    iteration_count = 1000
    run(start_word, source_lang, target_lang, iteration_count)
