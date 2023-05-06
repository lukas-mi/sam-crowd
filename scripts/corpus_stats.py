import glob
import string
from collections import Counter

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

import matplotlib
import matplotlib.pyplot as plt
import numpy as np


matplotlib.rcParams.update({'font.size': 16})

def plot_dist(plot_path, token_counter, lang, top=10):
    total = sum(token_counter.values())
    most_common = token_counter.most_common()[:top]
    top_tokens, top_counts = zip(*most_common)

    print(f'\t{10} most frequent tokens for {lang.capitalize()} corpus: {most_common}')

    fig, ax = plt.subplots()

    plt.xticks(rotation=90)
    ax.bar(list(range(0, len(top_tokens))), np.array(top_counts) / total * 100, color='lightseagreen')
    # ax.set_title(f'The {top} most frequent tokens in the {lang.capitalize()} corpus')
    ax.set_ylabel('Proportion in the corpus (%)')
    ax.set_xticks(list(range(0, len(top_tokens))))
    ax.set_xticklabels(top_tokens)
    plt.yticks(np.arange(0.0, 4.0, 0.5))

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

        'could', 'would', 'need', 'must', '\'s', 'also', 'new', 'us', 'therefore', 'one', 'however', 'many'
   ]

    for e in extra_to_remove:
        counter.pop(e, None)

    return counter


def statistics(articles_path, plot_path, lang):
    print('=' * 80)
    print(articles_path)

    articles = []
    for path in articles_path:
        files = glob.glob(path + '/**/full.txt', recursive=True)
        files = glob.glob(path + '/*.txt', recursive=True) if len(files) == 0 else files

        for file in files:
            with open(file, 'r') as f:
                content = ''
                paragraph_count = 0
                for line in f.readlines():
                    s_line = line.strip()
                    content += s_line + '\n'
                    paragraph_count += 1

                articles.append((file, content, paragraph_count - 2, word_tokenize(content, language=lang)))

    lengths_in_tokens = np.array([len(tokens) for _, _, _, tokens in articles])
    print('\ttoken statistics:')
    print('\t\tmin:', np.min(lengths_in_tokens))
    print('\t\tmean:', np.mean(lengths_in_tokens))
    print('\t\tmax:', np.max(lengths_in_tokens))
    print('\t\tstd:', np.std(lengths_in_tokens))

    paragraph_counts = np.array([p_count for _, _, p_count, _ in articles])
    print('\tparagraph statistics:')
    print('\t\tmin:', np.min(paragraph_counts))
    print('\t\tmean:', np.mean(paragraph_counts))
    print('\t\tmax:', np.max(paragraph_counts))
    print('\t\tstd:', np.std(paragraph_counts))

    all_tokens = [token.lower() for _, _, _, tokens in articles for token in tokens]
    token_counter = clean_counter(Counter(all_tokens), lang)

    plot_dist(plot_path, token_counter, lang)


if __name__ == '__main__':
    nltk.download('punkt')

    statistics(['../articles/guardian'], f'../figures/article_stats_guardian.png', 'english')
    statistics(['../articles/pbn'], f'../figures/article_stats_pbn.png', 'english')
    statistics(['../articles/altinget-en'], f'../figures/article_stats_altinget_en.png', 'english')
    statistics(['../articles/altinget'], f'../figures/article_stats_altinget_dk.png', 'danish')
