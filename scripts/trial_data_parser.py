import datetime
import json
import math
import os
import sys
import shutil

import pandas as pd

from scripts import utils

BASE_ASSIGNMENTS_PATH = 'data/assignments'
LATEST_ASSIGNMENTS_PATH = 'data/latest_assignments'
ARTICLES_PATH = 'articles'

# component labels
MAJOR_CLAIM = 'MajorClaim'
CLAIM_FOR = 'ClaimFor'
CLAIM_AGAINST = 'ClaimAgainst'
PREMISE = 'PREMISE'

# relation labels
SUPPORT = 'Support'
ATTACK = 'Attack'


def to_aaec_brat(ann, original_content):
    components = sorted(ann['components'], key=lambda item: item['target']['selector'][1]['start'])
    relations = ann['relations']

    lines = []
    id_mapping = {}

    title_offset = original_content.find('\n\n')
    title_offset += 2 if title_offset >= 0 else 1

    component_counter = 1
    attribute_counter = 1
    for c in components:
        cid = f'T{component_counter}'
        label = c['body'][0]['value']
        start = c['target']['selector'][1]['start'] + title_offset - 1
        end = c['target']['selector'][1]['end'] + title_offset - 1
        ann_excerpt = c['target']['selector'][0]['exact']

        # recogito replaces new line with a space
        original_excerpt = original_content[start:end].replace('\n', ' ')
        if not original_excerpt == ann_excerpt:
            raise Exception(
                f"""Annotated excerpt does not match the original ({start}, {end}):
                original: {original_excerpt}
                annotated: {ann_excerpt}"""
            )

        if label.startswith('Claim'):  # case of ClaimFor/ClaimAgainst
            lines.append(f'{cid}\tClaim {start} {end}\t{ann_excerpt}')

            if label == CLAIM_FOR:
                lines.append(f'A{attribute_counter}\tStance {cid} For')
            elif label == CLAIM_AGAINST:
                lines.append(f'A{attribute_counter}\tStance {cid} Against')
            else:
                raise Exception(f"Unsupported claim type {label}")

            attribute_counter += 1
        else:  # case of MajorClaim/Premise
            lines.append(f'{cid}\t{label} {start} {end}\t{ann_excerpt}')

        id_mapping[c['id']] = cid
        component_counter += 1

    relation_counter = 1
    for r in relations:
        rid = f'R{relation_counter}'
        label = r['body'][0]['value']
        cid_from = id_mapping[r['target'][0]['id']]
        cid_to = id_mapping[r['target'][1]['id']]

        if label == SUPPORT:
            label = 'supports'
        elif label == ATTACK:
            label = 'attacks'
        else:
            raise Exception(f"Unsupported relation type {label}")

        lines.append(f"{rid}\t{label} Arg1:{cid_from} Arg2:{cid_to}\t")
        relation_counter += 1

    return lines


def add_ann_event_data(data, name, metadata, include_invalid=True):
    annotations = sorted([item for item in data if item.get('trialdata', None) if item['trialdata'].get('event', None) == name], key=lambda item: item['dateTime'])

    metadata[f'{name}_count'] = len(annotations)
    metadata[f'{name}_times'] = [str(datetime.datetime.utcfromtimestamp(annotation['dateTime'] // 1000)) for annotation in annotations]
    if include_invalid:
        metadata[f'{name}_invalid'] = len([item for item in annotations if not item['trialdata']['valid']])

    return metadata


def get_valid_assignments(hit_ids):
    client = utils.new_client()

    hit_assignments = dict({})
    for hit_id in hit_ids:
        try:
            assignments = client.list_assignments_for_hit(
                HITId=hit_id,
                AssignmentStatuses=['Submitted', 'Approved', 'Rejected'],
                MaxResults=20
            )['Assignments']
            hit_assignments[hit_id] = [(a['WorkerId'], a['AssignmentId']) for a in assignments]
        except Exception as ex:
            print(hit_id, str(ex))

    return hit_assignments


# TODO: log and extract exact annotation mistakes
def parse_trail_data(df, base_path):
    valid_assignments = get_valid_assignments(set(df[df['mode'] == 'live']['hitid'].values))
    invalid_live_assignments = []
    ignored_assignments = []
    incomplete_assignments = []

    for _, entry in df.iterrows():
        worker_id = entry['workerid']
        assignment_id = entry['assignmentid']
        hit_id = entry['hitid']
        mode = entry['mode']

        if mode == 'live' and (worker_id, assignment_id) not in valid_assignments[hit_id]:
            invalid_live_assignments.append((hit_id, worker_id, assignment_id))

        assignment_path = f'{base_path}/{mode}/{hit_id}'
        base_fp = f'{assignment_path}/{worker_id}:{assignment_id}'
        meta_fp = f'{base_fp}_meta.json'
        brat_fp = f'{base_fp}.ann'
        ann_fp = f'{base_fp}_ann.json'

        data = json.loads(entry['datastring']) if isinstance(entry['datastring'], str) else None
        if data:
            os.makedirs(assignment_path, exist_ok=True)

            trial_data = data.pop('data')
            all_ann = [item['trialdata'] for item in trial_data if item.get('trialdata', None)]
            submitted_ann = [item for item in all_ann if item.get('event', None) == 'submit_annotations']
            content_metadata = [item for item in all_ann if item.get('event', None) == 'log_metadata']

            metadata = entry.to_dict()
            metadata.pop('datastring')
            metadata['beginexp'] = None if isinstance(metadata['beginexp'], float) and math.isnan(metadata['beginexp']) else metadata['beginexp']
            metadata['task_done'] = len(submitted_ann) >= 1
            metadata['quiz_done'] = sum(int(item.get('phase', None) == 'questionnaire' and item.get('status', None) == 'submit') for item in all_ann) >= 1
            metadata = add_ann_event_data(trial_data, 'open_guidelines', metadata, include_invalid=False)
            metadata = add_ann_event_data(trial_data, 'create_annotation', metadata)
            metadata = add_ann_event_data(trial_data, 'delete_annotation', metadata)
            metadata = add_ann_event_data(trial_data, 'update_annotation', metadata)
            metadata['quiz'] = data['questiondata']
            metadata['events'] = data['eventdata']
            metadata['content_metadata'] = content_metadata[-1]

            content_path = f"{ARTICLES_PATH}/{content_metadata[-1].get('publisher', 'prep')}/{content_metadata[-1]['article']}/{content_metadata[-1]['excerpt']}.txt"
            if not os.path.isfile(content_path):
                print(f'file under path {content_path} not found, ignoring entry {hit_id}:{assignment_id}')
                continue

            with open(content_path, 'r') as f:
                content = f.read()

            try:
                brat_content = to_aaec_brat(submitted_ann[-1], content)
            except Exception as ex:
                print(f'brat conversion failed for {hit_id}:{assignment_id}:', ex)
                continue

            with open(meta_fp, 'w') as f:
                f.write(json.dumps(metadata, indent=2))

            with open(brat_fp, 'w') as f:
                if metadata['task_done']:
                    content = '\n'.join(brat_content)
                else:
                    incomplete_assignments.append((hit_id, worker_id, assignment_id))
                    content = ''
                f.write(content + '\n')

            with open(ann_fp, 'w') as f:
                f.write(json.dumps(submitted_ann[-1], indent=2))
        else:
            ignored_assignments.append((hit_id, worker_id, assignment_id))

    if len(invalid_live_assignments) > 0:
        print('invalid live assignments')
        for triple in invalid_live_assignments:
            print('\t', triple)

    if len(incomplete_assignments) > 0:
        print('incomplete assignments')
        for triple in incomplete_assignments:
            print('\t', triple)

    if len(incomplete_assignments) > 0:
        print('incomplete assignments')
        for triple in incomplete_assignments:
            print('\t', triple)


def copy_to_latest(assignments_path):
    if os.path.exists(LATEST_ASSIGNMENTS_PATH):
        shutil.rmtree(LATEST_ASSIGNMENTS_PATH)
    shutil.copytree(assignments_path, LATEST_ASSIGNMENTS_PATH)


if __name__ == '__main__':
    if len(sys.argv) != 1:
        exit('exactly one argument expected: db_export_path')
    db_export_path = sys.argv[1]

    # os.chdir('../')
    # db_export_path = 'data/db_exports/assignments_202305062226.csv'

    dir_name = db_export_path.split('/')[-1].split('.')[0]
    base_path = f"{BASE_ASSIGNMENTS_PATH}/{dir_name}"
    parse_trail_data(pd.read_csv(db_export_path), base_path)
    copy_to_latest(base_path)
