# General Imports
import collections
import json
import time
import copy
import StringIO

# Flask Imports
from flask import Flask
from flask import request
from flask import render_template
from flask import jsonify
from flask import abort
app = Flask(__name__)
boards = {}

# Mongo Imports
import pymongo
from pymongo import errors
from bson import json_util
from bson.objectid import ObjectId

# Connect to MongoDB
try:
    client = pymongo.MongoClient("cityfarm.media.mit.edu")
    client.admin.authenticate("admin", "cityfarm")
    board_collection = client['admin']['boards']  # Default DB and collection for storing board settings
    log_collection = client['admin']['log']  # Default DB and collection for storing logs
    # Note that logs and settings are stored with the same ObjectId, which also corresponds to the board's Id
except pymongo.errors.ConnectionFailure:
    sys.exit(0)


# Routes:

@app.route("/", methods=['GET'])
def board_selection():
    cursor = board_collection.find()
    if cursor.count() == 0:
        return render_template("selection.html", dbs={})
    db_names = {}
    for i in cursor:
        try:
            db_names[i['settings']['value']['db_name']['value']]
        except:
            # Create db entry if it does not exist
            db_names[i['settings']['value']['db_name']['value']] = {}
        # Contains board info, with id as keys for a certain db above
        ids = {}
        ids[i['_id']] = {
            "collection_name": i['settings']['value']['collection_name']['value'],
            "hostname": i['settings']['value']['hostname']['value'],
            "_id": i['_id']
        }
        db_names[i['settings']['value']['db_name']['value']].update(ids)
    # format: db_names = {db_1: {collection_1:{collection_1, hostname, _id}, ...}, ...}
    ordered_dbs = collections.OrderedDict()  # Empty OrderedDict
    for db in sorted(db_names):
        # Create empty OrderedDicts for each board in a specific db
        ordered_dbs[db] = collections.OrderedDict()
        for _id_ in sorted(db_names[db]):
            ordered_dbs[db].update({_id_: db_names[db][_id_]})
    #print json_util.dumps(ordered_dbs.iteritems())
    return render_template("selection.html", dbs=ordered_dbs)


@app.route("/boards/<Id>/", methods=['GET', 'POST'])
def board_menu(Id):
    board_info = findBoardById(Id)
    if board_info is None:
        return abort(404)

    if request.method == 'POST':
        new_settings = build_settings_board(request, board_info)
        #print new_settings
        # Save to database:
        print new_settings
        if updateBoardById(Id, new_settings):
            return "Success"
        else:
            return "Update Operation Failed"
    elif len(request.args.keys()):
        try:
            if request.args['DELETEBOARD'] == "True":
                # Remove board from server
                if removeBoardById(Id):
                    print "DELETEBOARD"
                    return "Removed board from DB"
        except:
            pass
    else:
        return render_template("dashboard.html",
                               collection_name=board_info['settings']['value']['collection_name']['value'],
                               hostname=board_info['settings']['value']['hostname']['value'],
                               ip=board_info['ip']['value'],
                               version=board_info['version']['value'],
                               change_date=board_info['changes']['date'],
                               _id=str(board_info['_id']),
                               status=board_info['status']['value'])


@app.route("/boards/<Id>/log/", methods=['GET'])
def board_log(Id):
    board_info = findLogById(Id)
    if board_info is None:
        return abort(404)
    log_str = board_info['contents'].replace('"', "'").replace('\n', '<br>')
    return render_template("logs.html",
                           log_file=log_str[:-1],
                           collection_name=board_info['settings']['value']['collection_name']['value'],
                           hostname=board_info['settings']['value']['hostname']['value'],
                           ip=board_info['ip']['value'],
                           version=board_info['version']['value'],
                           change_date=board_info['changes']['date'],
                           _id=str(board_info['_id']),
                           status=board_info['status']['value'])


# @app.route("/boards/<Id>/advanced/", methods=['GET', 'POST'])
# def board_menu_advanced(Id):
#     board_info = findBoardById(Id)
#     if board_info == None:
#         return abort(404)
#
#     if request.method == 'POST':
#         new_settings = build_settings_board(request, board_info)
#         print new_settings
#         #Save to database:
#         #collection.update({'settings.value.hostname.value': coll_name}, json.loads(new_settings))
#         return "Success"
#
#     elif len(request.args.keys()):
#         try:
#             if request.args['RESET'] == "True":
#                 board_info['changes'] = {
#                     "title": "Changes",
#                     "type": "info",
#                     "date": "",
#                     "changed": "True",
#                     "value": "RESET"
#                 }
#                 print "RESET"
#                 return "Success"
#         except:
#             pass
#
#     else:
#         return render_template("dashboard.html",
#                                collection_name=board_info['settings']['value']['collection_name']['value'],
#                                hostname=board_info['settings']['value']['hostname']['value'],
#                                ip=board_info['ip']['value'],
#                                version=board_info['version']['value'],
#                                change_date=board_info['changes']['date'],
#                                _id=str(board_info['_id']),
#                                status=board_info['status']['value'])


# JSON get requests:
@app.route('/boards/<Id>/schema/')
def board_schema_json(Id):
    board_info = findBoardById(Id)
    if board_info is None:
        return abort(404)
    board_info.pop("_id")
    return json.dumps(build_schema_board(board_info))


@app.route('/boards/<Id>/advanced/schema/')
def board_schema_json_adv(Id):
    board_info = findBoardById(Id)
    if board_info is None:
        return abort(404)
    board_info.pop("_id")
    return json.dumps(build_schema_board_adv(board_info))


# Helper functions
def build_schema_board(board_info):
    template = {}
    template['title'] = "Board Settings"
    template['type'] = "object"
    template['properties'] = {}
    string = {}
    string['value'] = {}
    for i in board_info:
        if isinstance(board_info[i]['value'], list):
            try:
                template['properties'][i]
            except:
                template['properties'][str(i)] = {}
            try:
                string['value'][i]
            except:
                string['value'][str(i)] = []
            template['properties'][i]['title'] = str(board_info[i]['title'])
            template['properties'][i]['type'] = str(board_info[i]['type'])
            arr = []
            for sensor in board_info[i]['value']:
                entry = {}
                sensor_value = {}
                entry['title'] = "Sensor"
                entry['type'] = "object"
                entry['properties'] = {}
                for key in sensor:
                    entry['properties'][str(key)] = {
                        "title": str(sensor[key]['title']),
                        "type": str(sensor[key]['type']),
                        "required": "true",
                        # "default": sensor[key]['value']
                    }
                    sensor_value[str(key)] = str(sensor[key]['value'])
                string['value'][str(i)].append(sensor_value)
                arr.append(entry)
                # only one entry needed for schema
            template['properties'][i]['items'] = arr

        elif isinstance(board_info[i]['value'], dict):
            try:
                template['properties'][i]
            except:
                template['properties'][str(i)] = {}
            try:
                template['properties'][i]['properties']
            except:
                template['properties'][str(i)]['properties'] = {}
            try:
                string['value'][i]
            except:
                string['value'][str(i)] = {}
            template['properties'][i]['title'] = str(board_info[i]['title'])
            template['properties'][i]['type'] = str(board_info[i]['type'])
            for sensor in board_info[i]['value']:
                template['properties'][i]['properties'][str(sensor)] = {
                    "title": str(board_info[i]['value'][sensor]['title']),
                    "type": str(board_info[i]['value'][sensor]['type']),
                    "required": "true",
                    # "default": board_info[i]['value'][sensor]['value']
                }
                string['value'][str(i)][str(sensor)] = str(board_info[i]['value'][sensor]['value'])
    string['schema'] = template
    string['form'] = [
        "settings",
        "sensors",
        {"type": "submit", "title": "Save"}
    ]
    return string

# def build_schema_board_adv(board_info):
#     template = {}
#     template['title'] = "Board Settings"
#     template['type'] = "object"
#     template['properties'] = {}
#     string = {}
#     string['value'] = {}
#     for i in board_info:
#         if not isinstance(board_info[i]['value'], list) and not isinstance(board_info[i]['value'], dict) and board_info[i]['type'] != "info":
#             template['properties'][str(i)] = {
#                 "title": str(board_info[i]['title']),
#                 "type": 'string',
#                 "required": "true",
#                 # "default": board_info[i]['value']
#             }
#             string['value'][str(i)] = str(board_info[i]['value'])
#     string['schema'] = template
#     string['form'] = [
#         "server",
#         "username",
#         "password",
#         "version",
#         {"type": "submit", "title": "Save"}
#     ]
#     return string


def build_schema_board_forlesscomplex(board_info):
    schema = json.load(open("./static/schema/jsonform_schema_template.json"))
    string = {}
    string['value'] = {}
    for i in board_info:
        if board_info[i]['type'] == "array":
            try:
                string['value'][i]
            except:
                string['value'][str(i)] = []
            arr = []
            for sensor in board_info[i]['value']:
                sensor_value = {}
                for key in sensor:
                    sensor_value[str(key)] = str(sensor[key]['value'])
                string['value'][str(i)].append(sensor_value)
        elif board_info[i]['type'] == "object":
            try:
                string['value'][i]
            except:
                string['value'][str(i)] = {}
            for sensor in board_info[i]['value']:
                string['value'][str(i)][str(sensor)] = str(board_info[i]['value'][sensor]['value'])
        elif board_info[i]['type'] == "info":
            pass
        else:
            string['value'][str(i)] = str(board_info[i]['value'])
    string['schema'] = schema['schema']
    string['form'] = schema['form']
    return string


def build_settings_board(request, board_info):
    # reset base dictionary:
    old_info = copy.deepcopy(board_info)  # Used to reapply title & type keys
    board_info['changes'] = {
        "title": "Changes",
        "type": "info",
        "date": time.strftime("%m/%d/%y %I:%M:%S%p"),
        "value": "Initialized"
    }
    board_info['settings']['value'] = {}
    board_info['sensors']['value'] = []
    # Behaviour example:
    # settings[db_name]  -->  a[b]
    # sensors[0][units]  -->  a[b][c]
    print request.form.items()
    for key in request.form.keys():
        a = key[:key.find('[')]  # Holds the key name ('settings' or 'sensors')
        b = key[key.find('[') + 1:key.find(']')]  # Holds the index, if 'sensor', or the content, if settings
        try:
            # Try and see if b is int, if so, key kind is 'sensor'
            int(b)
            c = key[key.find(b) + 3:-1]  # c is content in this case
            b = int(b)
            try:
                # Try to add on index b, except if out of range
                board_info[a]['value'][b][c] = {}  # e.g. board_info['sensors']['value'][0]['name'] = {}
            except:
                for x in xrange(0, b+1):
                    try:
                        board_info[a]['value'][b][c] = {}
                        break
                    except:
                        board_info[a]['value'].append({c: {}})
            board_info[a]['value'][b][c]['value'] = request.form[key].replace('\\r', '\r').replace('\\n', '\n')
            board_info[a]['value'][b][c]['title'] = old_info[a]['value'][0][c]['title']
            board_info[a]['value'][b][c]['type'] = old_info[a]['value'][0][c]['type']
        except:
            # if b is not int, it must be that kind is 'settings'
            board_info[a]['value'][b] = {}
            board_info[a]['value'][b]['value'] = request.form[key].replace('\\r', '\r').replace('\\n', '\n')
            board_info[a]['value'][b]['title'] = old_info[a]['value'][b]['title']
            board_info[a]['value'][b]['type'] = old_info[a]['value'][b]['type']
    return board_info


def findBoardById(Id):
    try:
        board_info = board_collection.find_one({'_id': ObjectId(Id)})
    except pymongo.errors.OperationFailure:
        return None
    if board_info is None:
        return None
    return board_info


def removeBoardById(Id):
    if Id is None:
        return False
    try:
        board_collection.remove({'_id': ObjectId(Id)})
        log_collection.remove({'_id': ObjectId(Id)})
        return True
    except pymongo.errors.OperationFailure:
        return False


def findLogById(Id):
    try:
        board_info = log_collection.find_one({'_id': ObjectId(Id)})
        board_info.update(board_collection.find_one({'_id': ObjectId(Id)}))  # Add some required info for the log page
    except pymongo.errors.OperationFailure:
        return None
    return board_info


def updateBoardById(Id, data):
    try:
        board_collection.update({'_id': ObjectId(Id)}, data)
    except pymongo.errors.OperationFailure:
        return False
    return True


if __name__ == '__main__':
    app.run(debug=True)
