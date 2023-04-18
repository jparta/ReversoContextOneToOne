import dataclasses
import itertools
import json
import logging
import time
from collections import deque
from typing import cast

import stanza
from reverso_api.context import ReversoContextAPI, Translation
from stanza.pipeline.core import DownloadMethod

import custom_logging
from data_models import OneToOneRecord

# The aim is to find words which have a 1-to-1 translation between the source and target languages.
# Here, a 1-to-1 translation means that the two words are each other's most frequent translation.
# The words to be translated are gathered from the context sentences of the words previously processed.


# TODO
#  - Compare words against translations from the same part of speech
#  - Periodically sort words to translate by length. Shorter words tend to be more frequent.
#  - Give option to check whether word is already included in Anki deck
#  - Analyze and visualize scraping progress


def check_one_to_one(
    original_word: str,
    translation_strings: list[str],
    source_lang: str,
    target_lang: str,
) -> OneToOneRecord | None:
    # Returns a 1-to-1 translation record or None if the word does not have a 1-to-1 translation
    # Source and target languages have to be swapped
    if not translation_strings:
        return None
    top_translation = translation_strings[0]
    reverso_context_api = ReversoContextAPI(
        source_text=top_translation,
        source_lang=target_lang,
        target_lang=source_lang,
    )
    back_translation_objects = list(reverso_context_api.get_translations())
    if back_translation_objects:
        top_back_translation_object = back_translation_objects[0]
        top_back_translation = top_back_translation_object.translation
        if top_back_translation == original_word:
            frequency = top_back_translation_object.frequency
            record = OneToOneRecord(original_word, frequency, top_translation)
            return record
    return None


def clean_up_text(text: str, source_nlp: stanza.Pipeline):
    # Tokenize and lemmatize
    all_lemmas: set[str] = set()
    doc = source_nlp(text)
    doc = cast(stanza.Document, doc)
    for sentence in doc.sentences:
        for word in sentence.words:
            all_lemmas.add(word.lemma)
    # Remove lemmas consisting only of non-alphabetic characters
    clean_lemmas = set(lemma for lemma in all_lemmas if any(c.isalpha() for c in lemma))
    logging.debug(
        f"Words to translate: {' '.join(clean_lemmas)}", extra={"postfix": "\n"}
    )
    return clean_lemmas


def get_words_from_context_sentences(
    context_api: ReversoContextAPI,
    source_nlp: stanza.Pipeline,
) -> set[str]:
    # Get source language words from context sentences
    all_text = ""
    context_sentences = context_api.get_examples()
    sentence_count = 10
    limited_context_sentences = itertools.islice(context_sentences, sentence_count)
    for context_sentence in limited_context_sentences:
        all_text += context_sentence[0].text
    lemmas = clean_up_text(all_text, source_nlp)
    return lemmas


def report_progress(
    iteration: int,
    words_to_translate_count: int,
    scraped_words_count: int,
    translations_count: int,
    one_to_one_count: int,
):
    logging.info(f"Iteration {iteration}", extra={"prefix": "\n"})
    logging.info(f"Words to translate: {words_to_translate_count}")
    logging.info(f"Scraped words: {scraped_words_count}")
    logging.info(f"Translations: {translations_count}")
    translated_proportion = translations_count / scraped_words_count
    logging.info(
        f"Proportion of translations to scraped words: {translated_proportion*100:.3g}%"
    )
    logging.info(f"One-to-one translations: {one_to_one_count}")
    one_to_one_proportion = one_to_one_count / translations_count
    logging.info(
        f"Proportion of 1-to-1 translations: {one_to_one_proportion*100:.3g}%",
        extra={"postfix": "\n"},
    )


def save_to_file(
    source_lang: str,
    target_lang: str,
    translations: dict[str, list[Translation]],
    one_to_one_translations: list[OneToOneRecord],
    file_path: str,
):
    # Default JSON encoding converts namedtuples to lists and
    # doesn't handle dataclasses, so convert them to dictionaries
    translations_dicts = {
        source_word: [t._asdict() for t in translation_list]
        for source_word, translation_list in translations.items()
    }
    one_to_one_translations_dicts = [
        dataclasses.asdict(trans) for trans in one_to_one_translations
    ]
    struct = {
        "source_lang": source_lang,
        "target_lang": target_lang,
        "translations": translations_dicts,
        "one_to_one_translations": one_to_one_translations_dicts,
    }
    with open(file_path, "w") as f:
        json.dump(struct, f, indent=4)


def run(
    start_word: str,
    source_lang: str,
    target_lang: str,
    iteration_count: int,
    source_nlp: stanza.Pipeline,
    savefile_path: str,
):
    logging.info(f"Starting word: {start_word}", extra={"postfix": "\n"})

    SLEEP_TIME = 1
    REPORT_INTERVAL = 25
    SAVE_INTERVAL = 100

    # Each processed word has a key in a dictionary. The value is a list of Translation namedtuples.
    translations: dict[str, list[Translation]] = {}
    # Note 1-to-1 translations
    one_to_one_translations: list[OneToOneRecord] = []
    # A pool of words is established
    words_to_translate: deque[str] = deque()
    # Words already scraped
    scraped_words: set[str] = set()

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
        logging.debug(
            f"Translations for {current_word}: {' '.join(translation_strings)}",
            extra={"postfix": "\n"},
        )
        translations[current_word] = translation_objects

        # Check if the word has a 1-to-1 translation, and if so, add it to the list
        record = check_one_to_one(
            current_word, translation_strings, source_lang, target_lang
        )
        if record is None:
            logging.info(current_word)
        else:
            one_to_one_translations.append(record)
            top_translation = record.translation
            logging.info(f"1-to-1: {current_word} -> {top_translation}")
        logging.debug(one_to_one_translations)

        # Add new words to the pool
        batch_of_words = get_words_from_context_sentences(
            context_api,
            source_nlp,
        )
        new_words = batch_of_words - scraped_words
        words_to_translate.extend(new_words)
        scraped_words.update(new_words)

        # Set the next word to translate
        current_word = words_to_translate.popleft()

        # Report progress
        if i % REPORT_INTERVAL == 0:
            report_progress(
                i,
                words_to_translate_count=len(words_to_translate),
                scraped_words_count=len(scraped_words),
                translations_count=len(translations),
                one_to_one_count=len(one_to_one_translations),
            )
        if i % SAVE_INTERVAL == 0:
            save_to_file(
                source_lang,
                target_lang,
                translations,
                one_to_one_translations,
                savefile_path,
            )
        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    start_word = "желание"
    source_lang = "ru"
    target_lang = "en"
    iteration_count = 1000
    stanza_verbose = False
    savefile_path = "translations.json"

    custom_logging.set_up_logging()

    # Initialize stanza using source language, without downloading when not necessary
    logging.info("Initializing NLP pipeline...")
    source_nlp = stanza.Pipeline(
        source_lang,
        download_method=DownloadMethod.REUSE_RESOURCES,
        verbose=stanza_verbose,
    )
    logging.info("Done.", extra={"postfix": "\n"})

    # Run with new parameter source_nlp
    run(
        start_word,
        source_lang,
        target_lang,
        iteration_count,
        source_nlp,
        savefile_path,
    )
