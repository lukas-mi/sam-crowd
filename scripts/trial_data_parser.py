import json
import math
import os
import sys

import pandas as pd


def to_brat(ann):
    components = sorted(ann['components'], key=lambda item: item['target']['selector'][1]['start'])
    relations = ann['relations']

    lines = []
    id_mapping = {}

    component_counter = 1
    for c in components:
        cid = f'T{component_counter}'
        label = c['body'][0]['value']
        start = c['target']['selector'][1]['start']
        end = c['target']['selector'][1]['end']
        excerpt = c['target']['selector'][0]['exact']

        lines.append(f'{cid}\t{label} {start} {end}\t{excerpt}')
        id_mapping[c['id']] = cid
        component_counter += 1

    relation_counter = 1
    for r in relations:
        rid = f'R{relation_counter}'
        label = r['body'][0]['value']
        cid_from = id_mapping[r['target'][0]['id']]
        cid_to = id_mapping[r['target'][1]['id']]

        lines.append(f"{rid}\t{label} Arg1:{cid_from} Arg2:{cid_to}\t")
        relation_counter += 1

    return lines


# TODO: log and extract exact annotation mistakes
def parse_trail_data(df, base_path):
    ignored_assignments = []
    incomplete_assignments = []

    for _, entry in df.iterrows():
        worker_id = entry['workerid']
        assignment_id = entry['assignmentid']
        hit_id = entry['hitid']
        mode = entry['mode']

        assignment_path = f'{base_path}/{mode}/{hit_id}'
        base_fp = f'{assignment_path}/{worker_id}:{assignment_id}'
        meta_fp = f'{base_fp}.json'
        brat_fp = f'{base_fp}.ann'

        data = json.loads(entry['datastring']) if isinstance(entry['datastring'], str) else None
        if data:
            os.makedirs(assignment_path, exist_ok=True)

            trial_data = data.pop('data')
            all_ann = [item['trialdata'] for item in trial_data if item.get('trialdata', None)]
            submitted_ann = [item for item in all_ann if item.get('event', None) == 'submit_annotations']

            meta_data = entry.to_dict()
            meta_data.pop('datastring')
            meta_data['beginexp'] = None if isinstance(meta_data['beginexp'], float) and math.isnan(meta_data['beginexp']) else meta_data['beginexp']
            meta_data['task_done'] = len(submitted_ann) >= 1
            meta_data['quiz_done'] = sum(int(item.get('phase', None) == 'questionnaire' and item.get('status', None) == 'submit') for item in all_ann) >= 1
            meta_data['guidelines_opened'] = sum(int(item.get('event', None) == 'open_guidelines') for item in all_ann)
            meta_data['quiz'] = data['questiondata']
            meta_data['events'] = data['eventdata']

            with open(meta_fp, 'w') as f:
                f.write(json.dumps(meta_data, indent=2))

            with open(brat_fp, 'w') as f:
                if meta_data['task_done']:
                    content = '\n'.join(to_brat(submitted_ann[-1]))
                else:
                    incomplete_assignments.append((hit_id, worker_id, assignment_id))
                    content = ''
                f.write(content + '\n')
        else:
            ignored_assignments.append((hit_id, worker_id, assignment_id))

    print('ignored assignments')
    for triple in ignored_assignments:
        print('\t', triple)

    print('incomplete assignments')
    for triple in incomplete_assignments:
        print('\t', triple)


if __name__ == '__main__':
    if len(sys.argv) != 1:
        exit('exactly one argument expected: db_export_path')

    db_export_fp = sys.argv[1]
    # db_export_fp = '../data/db_exports/assignments_202303121718.csv'

    parse_trail_data(pd.read_csv(db_export_fp), '../data/hits')
