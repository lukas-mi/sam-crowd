import glob
import string
from collections import Counter

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

import matplotlib.pyplot as plt
import numpy as np


def plot_dist(plot_path, token_counter, lang, top=10):
    total = sum(token_counter.values())
    most_common = token_counter.most_common()[:top]
    top_tokens, top_counts = zip(*most_common)

    print(f'{10} most frequent tokens for {lang.capitalize()} corpus:')
    for token, count in most_common:
        print(f'\t{token}: {count}')

    fig, ax = plt.subplots()

    plt.xticks(rotation=90)
    ax.bar(list(range(0, len(top_tokens))), np.array(top_counts) / total * 100, color='lightseagreen')
    # ax.set_title(f'The {top} most frequent tokens in the {lang.capitalize()} corpus')
    ax.set_ylabel('Proportion in the corpus (%)')
    ax.set_xticks(list(range(0, len(top_tokens))))
    ax.set_xticklabels(top_tokens)
    fig.savefig(plot_path, bbox_inches='tight')


def clean_counter(counter, lang):
    # print(stopwords.words(lang))
    for s in stopwords.words(lang):
        counter.pop(s, None)

    for p in string.punctuation:
        counter.pop(p, None)

    # more punctuations and stopwords
    extra_to_remove = [
        '–', '``', '\'\'', '’', '‘', '“', '”',
        'kan',      # can
        'så',       # so
        'mere',     # more
        'derfor',   # therefore
        'hvordan',  # how
        'ved',      # by
        'brug',     # need
        'vores',    # our
        'andre',    # others
        'flere',    # more
        'sikre',    # ensure
        'kun',      # only
        'nye',      # new

        'could', 'would', 'need', 'must', '\'s', 'also', 'new', 'us', 'therefore'
   ]

    for e in extra_to_remove:
        counter.pop(e, None)

    return counter


def statistics(articles_path, plot_path, lang):
    nltk.download('punkt')

    articles = []
    for path in articles_path:
        files = glob.glob(path + '/**/full.txt', recursive=True)

        for file in files:
            with open(file, 'r') as f:
                content = f.read()
                articles.append((file, content, word_tokenize(content, language=lang)))

    lengths_in_tokens = np.array([len(tokens) for _, _, tokens in articles])
    print('token statistics:')
    print('\tmin:', np.min(lengths_in_tokens))
    print('\tmean:', np.mean(lengths_in_tokens))
    print('\tmax:', np.max(lengths_in_tokens))
    print('\tstd:', np.std(lengths_in_tokens))

    all_tokens = [token.lower() for _, _, tokens in articles for token in tokens]
    token_counter = clean_counter(Counter(all_tokens), lang)

    plot_dist(plot_path, token_counter, lang)


if __name__ == '__main__':
    statistics(['../articles/guardian', '../articles/pbn'], f'../figures/article_stats_guardian_pbn.png', 'english')
    statistics(['../articles/altinget-en'], f'../figures/article_stats_altinget_en.png', 'english')
    statistics(['../articles/altinget'], f'../figures/article_stats_altinget_dk.png', 'danish')
