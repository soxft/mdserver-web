# coding:utf-8

import os
import sys


from flask import Flask
from flask import Blueprint, render_template
from flask import jsonify
from flask import request


sys.path.append("class/core")
import public
import file_api

files = Blueprint('files', __name__, template_folder='templates')


@files.route("/")
def index():
    return render_template('default/files.html')


@files.route('get_body', methods=['POST'])
def getBody():
    path = request.form.get('path', '').encode('utf-8')
    return file_api.file_api().getBody(path)


@files.route('save_body', methods=['POST'])
def saveBody():
    path = request.form.get('path', '').encode('utf-8')
    data = request.form.get('data', '').encode('utf-8')
    encoding = request.form.get('encoding', '').encode('utf-8')
    return file_api.file_api().saveBody(path, data, encoding)


@files.route('/get_dir', methods=['POST'])
def getDir():
    path = request.form.get('path', '').encode('utf-8')
    if not os.path.exists(path):
        path = public.getRootDir() + "/wwwroot"

    search = request.args.get('search', '').strip().lower()
    page = request.args.get('p', '1').strip().lower()
    row = request.args.get('showRow', '10')

    print path, int(page), int(row), search

    return file_api.file_api().getDir(path, int(page), int(row), search)
