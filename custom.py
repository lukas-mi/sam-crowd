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
# example custom route
# ----------------------------------------------
# @custom_code.route('/my_custom_view')
# def my_custom_view():
#     # Print message to server.log for debugging
#     current_app.logger.info("Reached /my_custom_view")
#     try:
#         return render_template('custom.html')
#     except TemplateNotFound:
#         abort(404)


# ----------------------------------------------
# example using HTTP authentication
# ----------------------------------------------
# @custom_code.route('/my_password_protected_route')
# @myauth.requires_auth
# def my_password_protected_route():
#    try:
#        return render_template('custom.html')
#    except TemplateNotFound:
#        abort(404)

# ----------------------------------------------
# example accessing data
# ----------------------------------------------
# @custom_code.route('/view_data')
# @myauth.requires_auth
# def list_my_data():
#    users = Participant.query.all()
#    try:
#        return render_template('list.html', participants=users)
#    except TemplateNotFound:
#        abort(404)


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


def get_excerpt_helper(article, excerpt):
    file_path = f'{articles_path}/{article}/{excerpt}.txt'
    meta_path = f'{articles_path}/{article}/meta.json'

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
@custom_code.route('/articles/<article>/<excerpt>', methods=['GET'])
def get_excerpt(article, excerpt):
    excerpt_data = get_excerpt_helper(article, excerpt)
    if excerpt_data:
        return jsonify(**excerpt_data)
    else:
        abort(404)


annotation_examples = [
    ('salmon-deaths-scotland-fish-farming', 'section_2', 'section'),
    ('salmon-deaths-scotland-fish-farming', 'full', 'full'),
    ('pbn/should-vegans-stop-replicating-meat-cheese', 'full', 'article'),
    ('pbn/should-vegans-stop-replicating-meat-cheese', 'section_1', 'section'),
]


# ----------------------------------------------
# accessing information on a hit
# ----------------------------------------------
@custom_code.route('/hit_info/<hitid>', methods=['GET'])
def get_hit_info(hitid):
    if hitid.startswith('debug'):
        article, excerpt, annotation_mode = annotation_examples[1]
        excerpt_data = get_excerpt_helper(article, excerpt)
        excerpt_data['annotation_mode'] = annotation_mode
        excerpt_data['article'] = article
        excerpt_data['excerpt'] = excerpt
        return jsonify(**excerpt_data)
    else:
        query = f"""
            SELECT annotation_mode, article, excerpt
            FROM {hit_configs_table}
            WHERE hitid = :val
        """
        rows = db_session.execute(query, {'val': hitid}).fetchall()

        if len(rows) == 0:
            abort(404)
        else:
            annotation_mode, article, excerpt = rows[0]
            excerpt_data = get_excerpt_helper(article, excerpt)

            if excerpt_data:
                excerpt_data['annotation_mode'] = annotation_mode
                excerpt_data['article'] = article
                excerpt_data['excerpt'] = excerpt
                return jsonify(**excerpt_data)
            else:
                current_app.logger.warn(f"/hit_info/{hitid} no resources found for article={article}, excerpt{excerpt}")


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


# ----------------------------------------------
# example computing bonus
# ----------------------------------------------
@custom_code.route('/compute_bonus', methods=['GET'])
def compute_bonus():
    # check that user provided the correct keys
    # errors will not be that gracefull here if being
    # accessed by the Javascript client
    if not 'uniqueId' in request.args:
        # i don't like returning HTML to JSON requests...  maybe should change this
        raise ExperimentError('improper_inputs')
    uniqueId = request.args['uniqueId']

    try:
        # lookup user in database
        user = Participant.query. \
            filter(Participant.uniqueid == uniqueId). \
            one()
        user_data = loads(user.datastring)  # load datastring from JSON
        bonus = 0

        for record in user_data['data']:  # for line in data file
            trial = record['trialdata']
            if trial['phase'] == 'TEST':
                if trial['hit'] == True:
                    bonus += 0.02
        user.bonus = bonus
        db_session.add(user)
        db_session.commit()
        resp = {"bonusComputed": "success"}
        return jsonify(**resp)
    except:
        abort(404)  # again, bad to display HTML, but...
