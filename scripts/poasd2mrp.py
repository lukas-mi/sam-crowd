import glob
import os
import sys

import pandas as pd

import parsing_utils


def split_dataset(mrps, split_df):
    train_articles = split_df[split_df['split'] == 'train']['article']
    dev_articles = split_df[split_df['split'] == 'dev']['article']
    test_articles = split_df[split_df['split'] == 'test']['article']

    train_mrps = [mrp for mrp in mrps if mrp['id'].split(':')[-1] in train_articles.values]
    dev_mrps = [mrp for mrp in mrps if mrp['id'].split(':')[-1] in dev_articles.values]
    test_mrps = [mrp for mrp in mrps if mrp['id'].split(':')[-1] in test_articles.values]

    return train_mrps, dev_mrps, test_mrps


def convert(article_path, annotations_path):
    with open(os.path.join(article_path, 'full.txt'), 'r') as f:
        txt = f.read()

    ann_file_paths = glob.glob(os.path.join(annotations_path, '*.ann'))

    mrps = []
    for ann_fp in ann_file_paths:
        parent_path, article_name = os.path.split(article_path)
        publisher = os.path.split(parent_path)[-1]
        worker_id = os.path.split(ann_fp)[-1].split(':')[0]
        ann_id = f'{worker_id}:{publisher}:{article_name}'

        with open(ann_fp, 'r') as f:
            ann_lines = f.readlines()

        mrp = parsing_utils.read_brat(ann_id, ann_lines, txt, 'aaec', 'AAEC_')
        mrp = parsing_utils.reverse_edge(mrp=mrp)
        mrp = parsing_utils.sort_mrp_elements(mrp=mrp)
        mrps.append(mrp)

    return mrps


def main(articles_path, annotations_paths, output_path, split_info_path, excluded_publishers):
    mrps = []
    for publisher in os.listdir(articles_path):
        if publisher in excluded_publishers:
            continue

        for article_name in os.listdir(os.path.join(articles_path, publisher)):
            mrps += convert(
                os.path.join(articles_path, publisher, article_name),
                os.path.join(annotations_paths, publisher, article_name),
            )

    mrps = sorted(mrps, key=lambda item: item['id'])

    split_df = pd.read_csv(split_info_path)
    train_mrps, dev_mrps, test_mrps = split_dataset(mrps, split_df)
    mrp_splits = [mrps, train_mrps, dev_mrps, test_mrps]
    split_suffixes = ['', '_train', '_dev', '_test']

    for mrps, split_suffix in zip(mrp_splits, split_suffixes):
        output_file_path = os.path.join(output_path, f'poasd{split_suffix}.mrp')
        parsing_utils.dump_jsonl(output_file_path, mrps)


if __name__ == '__main__':
    if len(sys.argv) == 5:
        articles_path, annotation_path, output_path, split_info_path = sys.argv[1:]
        excluded_publishers = []
    elif len(sys.argv) == 6:
        articles_path, annotation_path, output_path, split_info_path = sys.argv[1:-1]
        excluded_publishers = sys.argv[-1].split(',')
    else:
        exit('4 or 5 arguments expected: db_export_path, articles_path, annotation_path, output_path, split_info_path, [excluded_publishers]')

    main(articles_path, annotation_path, output_path, split_info_path, excluded_publishers)
