# -*- coding: utf-8 -*-
# Copyright 2022 by Hitachi, Ltd.
# All rights reserved.

import json
from typing import List, Dict, Tuple, Set

# The code in this file is copied/modified from:
#   https://github.com/hitachi-nlp/graph_parser/blob/main/amparse/evaluator/scorer.py


class Scorer:
    def __init__(self):
        self.s = 0
        self.g = 0
        self.c = 0
        return

    def add(self, system: Set[Tuple], gold: Set[Tuple]):
        self.s += len(system)
        self.g += len(gold)
        self.c += len(gold & system)
        return

    @property
    def p(self):
        return self.c / self.s if self.s else 0.

    @property
    def r(self):
        return self.c / self.g if self.g else 0.

    @property
    def f(self):
        p = self.p
        r = self.r
        return (2. * p * r) / (p + r) if p + r > 0 else 0.0

    def dump(self):
        return {
            'g': self.g,
            's': self.s,
            'c': self.c,
            'p': self.p,
            'r': self.r,
            'f': self.f
        }


def read_mrp(fp: str):
    with open(fp, 'r') as f:
        jds = [json.loads(l) for l in f.readlines() if l]
    return jds


def eval_anchor(s_mrps: List[Dict], g_mrps: List[Dict]) -> Dict:
    scorer = Scorer()
    for s_mrp, g_mrp in zip(s_mrps, g_mrps):
        scorer.add(
            system=set([
                (s_mrp['id'], node['anchors'][0]['from'], node['anchors'][0]['to'])
                for node in s_mrp['nodes']]),
            gold=set([
                (g_mrp['id'], node['anchors'][0]['from'], node['anchors'][0]['to'])
                for node in g_mrp['nodes']]),
        )
    return scorer.dump()


def eval_top(s_mrps: List[Dict], g_mrps: List[Dict]) -> Dict:
    scorer = Scorer()
    for s_mrp, g_mrp in zip(s_mrps, g_mrps):
        s_nid2anc = {node['id']: (node['anchors'][0]['from'], node['anchors'][0]['to']) for node in s_mrp['nodes']}
        g_nid2anc = {node['id']: (node['anchors'][0]['from'], node['anchors'][0]['to']) for node in g_mrp['nodes']}
        scorer.add(
            system=set([
                (s_mrp['id'],) + s_nid2anc[top] for top in s_mrp['tops']]),
            gold=set([
                (g_mrp['id'],) + g_nid2anc[top] for top in g_mrp['tops']]),
        )
    return scorer.dump()


def eval_label(s_mrps: List[Dict], g_mrps: List[Dict]) -> Dict:
    labels = set()
    for g_mrp in g_mrps:
        labels |= set([n['label'] for n in g_mrp['nodes'] if 'label' in n])
    label_scores = dict()
    for label in labels:
        scorer = Scorer()
        for s_mrp, g_mrp in zip(s_mrps, g_mrps):
            scorer.add(
                system=set([
                    (
                        s_mrp['id'],
                        node['anchors'][0]['from'],
                        node['anchors'][0]['to'],
                    )
                    for node in s_mrp['nodes']
                    if 'label' in node and node['label'] == label
                ]),
                gold=set([
                    (
                        g_mrp['id'],
                        node['anchors'][0]['from'],
                        node['anchors'][0]['to'],
                    )
                    for node in g_mrp['nodes']
                    if 'label' in node and node['label'] == label
                ]),
            )
        label_scores[label] = scorer.dump()

    scorer = Scorer()
    for s_mrp, g_mrp in zip(s_mrps, g_mrps):
        scorer.add(
            system=set([
                (
                    s_mrp['id'],
                    node['anchors'][0]['from'],
                    node['anchors'][0]['to'],
                    node['label']
                )
                for node in s_mrp['nodes']
                if 'label' in node
            ]),
            gold=set([
                (
                    g_mrp['id'],
                    node['anchors'][0]['from'],
                    node['anchors'][0]['to'],
                    node['label']
                )
                for node in g_mrp['nodes']
                if 'label' in node
            ]),
        )
    label_scores['total'] = scorer.dump()
    return label_scores


def eval_edge(s_mrps: List[Dict], g_mrps: List[Dict]) -> Dict:
    # Align node anchor and edge
    s_n2anc, g_n2anc = dict(), dict()
    for s_mrp, g_mrp in zip(s_mrps, g_mrps):
        for node in s_mrp['nodes']:
            anc = node['anchors'][0]
            s_n2anc[(s_mrp['id'], node['id'])] = (anc['from'], anc['to'])
        for node in g_mrp['nodes']:
            anc = node['anchors'][0]
            g_n2anc[(g_mrp['id'], node['id'])] = (anc['from'], anc['to'])
    # Obtain edge labels
    edge_labels = set()
    for g_mrp in g_mrps:
        labels = [e['label'] for e in g_mrp['edges'] if 'label' in e]
        edge_labels |= set(labels)
    # Calculate label scores
    label_scores = dict()
    for label in edge_labels:
        scorer = Scorer()
        for s_mrp, g_mrp in zip(s_mrps, g_mrps):
            scorer.add(
                system=set([
                    (
                        s_mrp['id'],
                        *s_n2anc[(s_mrp['id'], edge['source'])],
                        *s_n2anc[(s_mrp['id'], edge['target'])]
                    )
                    for edge in s_mrp['edges']
                    if 'label' in edge and edge['label'] == label
                ]),
                gold=set([
                    (
                        g_mrp['id'],
                        *g_n2anc[(g_mrp['id'], edge['source'])],
                        *g_n2anc[(g_mrp['id'], edge['target'])]
                    )
                    for edge in g_mrp['edges']
                    if 'label' in edge and edge['label'] == label
                ]),
            )
        label_scores[label] = scorer.dump()

    link_scorer = Scorer()
    for s_mrp, g_mrp in zip(s_mrps, g_mrps):
        link_scorer.add(
            system=set([
                (
                    s_mrp['id'],
                    *s_n2anc[(s_mrp['id'], edge['source'])],
                    *s_n2anc[(s_mrp['id'], edge['target'])]
                )
                for edge in s_mrp['edges']
            ]),
            gold=set([
                (
                    g_mrp['id'],
                    *g_n2anc[(g_mrp['id'], edge['source'])],
                    *g_n2anc[(g_mrp['id'], edge['target'])]
                )
                for edge in g_mrp['edges']
            ]),
        )
    label_scores['link'] = link_scorer.dump()

    scorer = Scorer()
    for s_mrp, g_mrp in zip(s_mrps, g_mrps):
        scorer.add(
            system=set([
                (
                    s_mrp['id'],
                    *s_n2anc[(s_mrp['id'], edge['source'])],
                    *s_n2anc[(s_mrp['id'], edge['target'])],
                    (edge['label'] if 'label' in edge else '')
                )
                for edge in s_mrp['edges']
            ]),
            gold=set([
                (
                    g_mrp['id'],
                    *g_n2anc[(g_mrp['id'], edge['source'])],
                    *g_n2anc[(g_mrp['id'], edge['target'])],
                    (edge['label'] if 'label' in edge else '')
                )
                for edge in g_mrp['edges']
            ]),
        )
    label_scores['total'] = scorer.dump()
    return label_scores
