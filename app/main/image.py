# coding=utf-8

from hbase import HBaseDBConnection
import os
from flask import current_app
import base64


def insert_image(filename, _type=None, _file=None):
    if os.environ['use_hbase'] == True:
        image = base64.b64encode(_file.read()).decode('utf8')
        hbase = HBaseDBConnection()
        hbase.execute_insert('image', filename, ['image_type', 'image'], [_type, image])
        hbase.dbpool.close()
    else:
        _file.save(os.path.join(current_app.config['PAGE_UPLOAD_FOLDER'], filename))


def show_image(key):
    hbase = HBaseDBConnection()
    file_bytes = hbase.query_by_row('image', 'user_' + key)
    hbase.dbpool.close()
    if file_bytes:
        file_bytes = file_bytes[b'image:image']
        result = base64.b64decode(file_bytes.decode())
        return Response(result, mimetype='image/jpeg')
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], "-1.jpg")