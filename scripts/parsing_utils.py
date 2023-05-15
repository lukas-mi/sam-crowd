import copy
import json
from typing import Dict, List


# The code in this file is copied/modified from:
#   https://github.com/hitachi-nlp/graph_parser/blob/main/amparse/common/util.py


def read_brat(ann_id: str, ann_lines: List[str], txt: str, framework: str, prefix: str = '', source: str = 'N/A') -> Dict:
    """
    Read the brat formatted file and text file, converting them into the mrp dictionary

    Parameters
    ----------
    ann_id : str
        The id associated to the annotation
    ann_lines : str
        The lines of a brat annotation file (.ann)
    txt : str
        Text associated with the annotation
    framework : str
        The name of the framework
    prefix : str
        The name of the label prefix
    source : str
        The source of the dataset, e.g., URL

    Returns
    ----------
    mrp : Dict
        The converted mrp dictionary
    """

    nodes, edges, tops = [], [], []
    major_claims = []
    for ann_line in ann_lines:

        annots = ann_line.split('\t')

        if len(annots) < 2:
            assert False, 'Invalid ann format at {}'.format(id)
        if annots[1].startswith('AnnotatorNotes'):
            continue

        # Add component
        if annots[0].startswith('T'):
            adu_data = annots[1].split(' ')

            if len(adu_data) == 3:
                adu_type, start, stop = adu_data
            else:
                adu_type = adu_data[0]
                start, stop = adu_data[1], adu_data[-1]

            node = {
                "id": int(annots[0][1:]),
                "label": adu_type,
                "anchors": [{"from": int(start), "to": int(stop)}],
            }
            nodes.append(node)

            if adu_type == 'MajorClaim':
                major_claims.append(node)

        # Add relation
        elif annots[0].startswith('R'):
            edge_label, src, trg = annots[1].split(' ')
            src = int(src.replace('Arg1:', '')[1:])
            trg = int(trg.replace('Arg2:', '')[1:])

            find = [e for e in edges if e['source'] == src and e['target'] == trg]
            if find:
                print(f'Found duplication: {ann_id}, {find}')
            else:
                edges.append({"source": src, "target": trg, "label": edge_label})

    if major_claims:
        # Assign a stance (For or Against) for each Claim
        nid2node = {n['id']: n for n in nodes}

        for ann_line in ann_lines:
            annots = ann_line.split('\t')
            if annots[1].startswith('AnnotatorNotes'):
                continue

            # Add stance for a claim
            if annots[0].startswith('A'):
                _, src, stance = annots[1].split(' ')
                src = src[1:]
                stance = stance.strip()
                nid2node[int(src)]['label'] += f':{stance}'

    # Reassign node id to make the id starts with zero
    nodes = sorted(nodes, key=lambda x: x['anchors'][0]['from'])
    nid2newid = {n['id']: i for i, n in enumerate(nodes)}
    for node in nodes:
        node['id'] = nid2newid[node['id']]
        node['label'] = prefix + node['label']
    for edge in edges:
        edge['source'] = nid2newid[edge['source']]
        edge['target'] = nid2newid[edge['target']]
        edge['label'] = prefix + edge['label']

    tops = []
    for node in nodes:
        out_edges = [e for e in edges if e['source'] == node['id']]
        if not out_edges:
            tops.append(node['id'])

    mrp = {
        "id": ann_id,
        "input": txt,
        "framework": framework,
        "time": "2023-04-15",
        "flavor": 0,
        "version": 1.0,
        "language": "en",
        "provenance": source,
        "source": source,
        "nodes": nodes,
        "edges": edges,
        "tops": tops,
    }
    return mrp


def reverse_edge(mrp: Dict) -> Dict:
    """
    Reverse edges (exchange source and target)

    Example usage:
    >>> reverse_edge(mrp={'edges': [{'source': 0, 'target': 1}, {'source': 2, 'target': 3}]})
    {'edges': [{'source': 1, 'target': 0}, {'source': 3, 'target': 2}]}

    Parameters
    ----------
    mrp : Dict
        The input mrp dictionary

    Returns
    ----------
    mrp : Dict
        The output mrp dictionary
    """
    mrp = copy.deepcopy(mrp)
    new_edges = []
    for e in mrp['edges']:
        e['source'], e['target'] = e['target'], e['source']
        new_edges.append(e)
    mrp['edges'] = new_edges
    return mrp


def sort_mrp_elements(mrp: Dict) -> Dict:
    """
    Sort mrp tops, nodes and edges by ID

    Parameters
    ----------
    mrp : Dict
        The input mrp dictionary

    Returns
    ----------
    mrp : Dict
        The output mrp dictionary
    """
    mrp = copy.deepcopy(mrp)
    mrp['tops'] = sorted(mrp['tops'])
    mrp['nodes'] = sorted(mrp['nodes'], key=lambda x: x['id'])
    mrp['edges'] = sorted(mrp['edges'], key=lambda x: (x['source'], x['target']))
    return mrp


def dump_jsonl(fpath: str, jsonl: List[Dict]):
    """
    Save a file in the jsonline (mrp) format

    Parameters
    ----------
    fpath : str
        The path for the saved file
    jsonl : List[Dict]
        The list of dictionary to be saved
    """
    with open(fpath, 'w') as f:
        for jl in jsonl:
            line = json.dumps(jl, ensure_ascii=False)
            f.write(f'{line}\n')
