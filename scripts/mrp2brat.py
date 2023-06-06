import json
import sys


def mrp_to_brat(input_path, output_path):
    with open(input_path, 'r') as f:
        entries = [json.loads(line) for line in f.readlines()]

    for entry in entries:
        article = entry['id']
        content = entry['input']
        components = entry['nodes']
        relations = entry['edges']

        lines = []
        stance_counter = 1
        for comp in components:
            id = int(comp['id']) + 1
            start = int(comp['anchors'][0]['from'])
            end = int(comp['anchors'][0]['to'])
            label = comp['label'].replace('AAEC_', '')
            excerpt = content[start:end]

            label_parts = label.split(':')
            if len(label_parts) == 1:
                lines.append(f"T{id}\t{label} {start} {end}\t{excerpt}\n")
            elif len(label_parts) == 2:
                lines.append(f"T{id}\t{label_parts[0]} {start} {end}\t{excerpt}\n")
                lines.append(f"A{stance_counter}\tStance T{id} {label_parts[1]}\n")
                stance_counter += 1
            else:
                raise Exception(f"{label} split by ':' has more than 2 parts: {label_parts}")

        rel_counter = 1
        for rel in relations:
            source = int(rel['target']) + 1
            target = int(rel['source']) + 1
            label = rel['label'].replace('AAEC_', '')

            lines.append(f"R{rel_counter}\t{label} Arg1:T{source} Arg2:T{target}\n")
            rel_counter += 1

        with open(f'{output_path}/{article}.ann', 'w') as f:
            f.writelines(lines)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        exit('2 arguments expected: input_path output_path')

    mrp_to_brat(sys.argv[1], sys.argv[2])
