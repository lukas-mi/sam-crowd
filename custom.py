# this file imports custom routes into the experiment server
from __future__ import generator_stop

import json
import os

import flask
from flask import Blueprint, render_template, request, jsonify, Response, abort, current_app, make_response
from jinja2 import TemplateNotFound
from functools import wraps
from sqlalchemy import or_

from psiturk.psiturk_config import PsiturkConfig
from psiturk.experiment_errors import ExperimentError, InvalidUsageError
from psiturk.user_utils import PsiTurkAuthorization, nocache

# # Database setup
from psiturk.db import db_session, init_db
from psiturk.models import Participant
from json import dumps, loads

# load the configuration options
config = PsiturkConfig()
config.load_config()
# if you want to add a password protect route, uncomment and use this
# myauth = PsiTurkAuthorization(config)

# explore the Blueprint
custom_code = Blueprint('custom_code', __name__,
                        template_folder='templates', static_folder='static')


###########################################################
#  serving warm, fresh, & sweet custom, user-provided routes
#  add them here
###########################################################
articles_path = config.get('Custom Parameters', 'articles_path')
hit_configs_table = config.get('Custom Parameters', 'hit_configs_table')


# ----------------------------------------------
# accessing specific article
# ----------------------------------------------
@custom_code.route('/articles', methods=['GET'])
def list_articles():
    return jsonify(**{'articles': next(os.walk(articles_path))[1]})


# ----------------------------------------------
# accessing specific article
# ----------------------------------------------
@custom_code.route('/articles/<article>', methods=['GET'])
def list_excerpts(article):
    excerpts_path = f'{articles_path}/{article}'
    if os.path.isdir(excerpts_path):
        excerpts = [fn.replace('.txt', '') for fn in next(os.walk(excerpts_path))[2] if fn.endswith('txt')]
        return jsonify(**{'excerpts': excerpts})
    else:
        abort(404)


def get_excerpt_helper(publisher, article, excerpt):
    file_path = f'{articles_path}/{publisher}/{article}/{excerpt}.txt'
    meta_path = f'{articles_path}/{publisher}/{article}/meta.json'

    if os.path.isfile(file_path) and os.path.isfile(meta_path):
        with open(file_path, 'r') as f:
            content = f.read()
        with open(meta_path, 'r') as f:
            meta = json.loads(f.read())
        return {'content': content, 'meta': meta}
    else:
        return None


# ----------------------------------------------
# accessing specific article
# ----------------------------------------------
@custom_code.route('/articles/<publisher>/<article>/<excerpt>', methods=['GET'])
def get_excerpt(publisher, article, excerpt):
    excerpt_data = get_excerpt_helper(publisher, article, excerpt)
    if excerpt_data:
        return jsonify(**excerpt_data)
    else:
        abort(404)


annotation_examples = [
    ('pbn', 'should-vegans-stop-replicating-meat-cheese', 'full', 'article', 'EN'),
    ('pbn', 'should-vegans-stop-replicating-meat-cheese', 'section_1', 'section', 'EN'),
    ('prep', 'salmon-deaths-scotland-fish-farming', 'section_2', 'section', 'EN'),
    ('prep', 'salmon-deaths-scotland-fish-farming', 'full', 'full', 'EN'),
    ('prep', 'har-soja-en-fremtid-i-dansk-landbrug', 'full', 'full', 'DK'),
    ('prep', 'har-soja-en-fremtid-i-dansk-landbrug', 'section_1', 'section', 'DK'),
    ('prep', 'har-soja-en-fremtid-i-dansk-landbrug-en', 'full', 'full', 'EN'),
    ('prep', 'har-soja-en-fremtid-i-dansk-landbrug-en', 'section_1', 'section', 'EN'),
    ('prep', 'americans-diet-public-health-food', 'full', 'full', 'EN')
]


# ----------------------------------------------
# accessing information on a hit
# ----------------------------------------------
@custom_code.route('/hit_info/<hitid>', methods=['GET'])
def get_hit_info(hitid):
    if hitid.startswith('debug'):
        publisher, article, excerpt, annotation_mode, lang = annotation_examples[-3]
        excerpt_data = get_excerpt_helper(publisher, article, excerpt)
        excerpt_data['annotation_mode'] = annotation_mode
        excerpt_data['article'] = article
        excerpt_data['excerpt'] = excerpt
        excerpt_data['publisher'] = publisher
        excerpt_data['lang'] = lang
        return jsonify(**excerpt_data)
    else:
        query = f"""
            SELECT annotation_mode, article, excerpt, publisher, lang
            FROM {hit_configs_table}
            WHERE hitid = :val
        """
        rows = db_session.execute(query, {'val': hitid}).fetchall()

        if len(rows) == 0:
            abort(404)
        else:
            annotation_mode, article, excerpt, publisher, lang = rows[0]
            excerpt_data = get_excerpt_helper(publisher, article, excerpt)

            if excerpt_data:
                excerpt_data['annotation_mode'] = annotation_mode
                excerpt_data['article'] = article
                excerpt_data['excerpt'] = excerpt
                excerpt_data['publisher'] = publisher
                excerpt_data['lang'] = lang
                return jsonify(**excerpt_data)
            else:
                current_app.logger.warn(f"/hit_info/{hitid} no resources found for publisher={publisher} article={article}, excerpt{excerpt}")


# ----------------------------------------------
# accessing article guidelines
# ----------------------------------------------
@custom_code.route('/guidelines/article')
def article_guidelines():
    try:
        return render_template('guidelines/article.html')
    except TemplateNotFound:
        abort(404)


# ----------------------------------------------
# accessing section guidelines
# ----------------------------------------------
@custom_code.route('/guidelines/section')
def section_guidelines():
    try:
        return render_template('guidelines/section.html')
    except TemplateNotFound:
        abort(404)


# ----------------------------------------------
# accessing full guidelines
# ----------------------------------------------
@custom_code.route('/guidelines/full')
def full_guidelines():
    try:
        return render_template('guidelines/full.html')
    except TemplateNotFound:
        abort(404)
