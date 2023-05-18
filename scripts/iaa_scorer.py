import sys
from collections import defaultdict

import numpy as np

import scoring_utils as sutils


def main(multi_ann_path):
    mrps = sutils._read_mrp(multi_ann_path)

    mrps_by_articles = defaultdict(list)
    for mrp in mrps:
        parts = mrp['id'].split(':')
        worker = parts[0]
        article = parts[-1]
        mrp['id'] = article
        mrps_by_articles[article].append((worker, mrp))

    f_scores = defaultdict(list)

    for article, article_mrps in list(mrps_by_articles.items()):
        print('=' * 120)
        print(article)

        res_tops = []
        res_anchors = []
        res_labels = []
        res_edges = []

        for idx1 in range(len(article_mrps) - 1):
            worker1, article_mrps1 = article_mrps[idx1]
            for idx2 in range(idx1 + 1, len(article_mrps)):
                worker2, article_mrps2 = article_mrps[idx2]
                res_tops.append((worker1, worker2, sutils.eval_top(s_mrps=[article_mrps1], g_mrps=[article_mrps2])))
                res_anchors.append((worker1, worker2, sutils.eval_anchor(s_mrps=[article_mrps1], g_mrps=[article_mrps2])))
                res_labels.append((worker1, worker2, sutils.eval_label(s_mrps=[article_mrps1], g_mrps=[article_mrps2])))
                res_edges.append((worker1, worker2, sutils.eval_edge(s_mrps=[article_mrps1], g_mrps=[article_mrps2])))

        f_scores['tops'].append(np.mean([tops[2]['f'] for tops in res_tops]))
        f_scores['anchors'].append(np.mean([anchors[2]['f'] for anchors in res_anchors]))
        f_scores['labels'].append(np.mean([labels[2]['total']['f'] for labels in res_labels]))
        f_scores['links'].append(np.mean([edges[2]['link']['f'] for edges in res_edges]))
        f_scores['edges'].append(np.mean([edges[2]['total']['f'] for edges in res_edges]))

        for worker1, worker2, tops in res_tops:
            f_scores[f'{worker1}_{worker2}_tops'].append(tops['f'])

        for worker1, worker2, anchors in res_anchors:
            f_scores[f'{worker1}_{worker2}_anchors'].append(anchors['f'])

        for worker1, worker2, labels in res_labels:
            f_scores[f'{worker1}_{worker2}_labels'].append(labels['total']['f'])

        for worker1, worker2, edges in res_edges:
            f_scores[f'{worker1}_{worker2}_links'].append(edges['link']['f'])

        for worker1, worker2, edges in res_edges:
            f_scores[f'{worker1}_{worker2}_edges'].append(edges['total']['f'])

        for idx in range(len(res_anchors)):
            worker1, worker2, metric = res_anchors[idx]
            print(worker1, worker2, metric)
        print(np.mean([a[2]['f'] for a in res_anchors]))

    print('=' * 120)
    for metric, values in f_scores.items():
        print(metric, np.mean(values))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        exit('1 argument expected: multi_ann_path')
    main(sys.argv[1])
