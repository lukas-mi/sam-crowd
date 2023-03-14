import os
import subprocess
import sys
import re

import psycopg2
import requests

ARTICLES_BASE_PATH = 'articles'
BASE_URL = 'https://sam-crowd.herokuapp.com'
# BASE_URL = 'http://localhost:22362'
HIT_CONFIGS_TABLE = 'hit_configs'


def validate_wrapper_args(annotation_mode, article, excerpt):
    if annotation_mode not in ['article', 'section']:
        print(f'unsupported annotation_mode {annotation_mode}')
        exit(1)

    file_path = f'{ARTICLES_BASE_PATH}/{article}/{excerpt}.txt'
    meta_path = f'{ARTICLES_BASE_PATH}/{article}/meta.json'
    if not os.path.isfile(file_path) or not os.path.isfile(meta_path):
        print(f'files {file_path} or {meta_path} do not exist locally')
        exit(1)

    excerpt_url = f'{BASE_URL}/articles/{article}/{excerpt}'
    response = requests.get(excerpt_url)
    if response.status_code != 200:
        print(f'resource at {excerpt_url} was not found')
        exit(1)


def create_con():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def check_table(conn):
    query = f'SELECT COUNT(*) FROM {HIT_CONFIGS_TABLE}'

    print(f'running test query: {query}')
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        print(f'test query output = {rows[0][0]}')


def insert_row(conn, hitid, annotation_mode, article, excerpt):
    query = f"INSERT INTO {HIT_CONFIGS_TABLE} VALUES ('{hitid}', '{annotation_mode}', '{article}', '{excerpt}')"

    print(f'running insert: {query}')
    with conn.cursor() as cur:
        cur.execute(query)


def hit_create(psiturk_args):
    print('attempting to create the hit')
    result = subprocess.run(['psiturk', 'hit', 'create'] + psiturk_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.decode('utf-8')
    return_code = result.returncode
    return return_code, output


def hit_expire(hitid):
    print('attempting to expire the hit')
    result = subprocess.run(['psiturk', 'hit', 'expire', hitid], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.decode('utf-8')
    return_code = result.returncode
    return return_code, output


def extract_hitid(output):
    hitid_search = re.search('HITid: (.*)\n', output)
    return hitid_search.group(1) if hitid_search else None


if __name__ == '__main__':
    wrapper_args = sys.argv[1:4]
    psiturk_args = sys.argv[4:]

    print('wrapper args:', wrapper_args)
    print('psiturk args:', psiturk_args)

    annotation_mode, article, excerpt = wrapper_args
    validate_wrapper_args(annotation_mode, article, excerpt)

    with create_con() as conn:
        check_table(conn)

        return_code1, output1 = hit_create(psiturk_args)
        print(output1)
        if return_code1 != 0:
            exit(return_code1)

        hitid = extract_hitid(output1)
        if hitid is None:
            print('failed to extract hitid from psiturk output:')
            print(output1)
            exit(1)

        try:
            insert_row(conn, hitid, annotation_mode, article, excerpt)
            conn.commit()
        except Exception as ex1:
            print('caught exception:', ex1)

            print('rolling back insert')
            try:
                conn.rollback()
            except Exception as ex2:
                print('failed rollback', ex2)

            return_code2, output2 = hit_expire(hitid)
            print(f'psiturk hit expire command exited with {return_code2}, output:')
            print(output2)
            exit(1)
