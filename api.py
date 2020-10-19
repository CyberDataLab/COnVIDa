from flask import request
from flask_restful import Resource, Api, reqparse
import os, sys
import json

## Add convida lib and convida server lib to path

convida_lib_path = os.getcwd()
lib = os.path.join(convida_lib_path, 'COnVIDa-lib')
lib_aux = os.path.join(lib, 'lib')
sys.path.append(lib_aux)

convida_server_path = os.getcwd()
server_path = os.path.join(convida_server_path, 'COnVIDa-lib')
server_aux = os.path.join(server_path, 'server')
sys.path.append(server_aux)

from convida import COnVIDa
from regions import Regions
from datatype import DataType
from convida_server import convida_server
import pandas as pd


def init_api(app):
    """Deploys API REST for queries.

    Parameters
    ----------
    app : Flask instance

    Returns
    -------

    """
    api = Api(app, prefix='/api', default_mediatype='application/json')
    api.add_resource(DefaultRequest, '')
    api.add_resource(TemporalRequest, '/temporal')
    api.add_resource(RegionalRequest, '/regional')


parser = reqparse.RequestParser()
parser.add_argument('data', type=list, location='json')
parser.add_argument('regions', type=list, location='json')
parser.add_argument('start_date', type=str)
parser.add_argument('end_date', type=str)


class DefaultRequest(Resource):
    def post(self):
        return 'Usage -> http://localhost:8899/api/[temporal|regional]', 400


class TemporalRequest(Resource):
    def post(self):

        request.get_json(force=True)
        args = parser.parse_args()

        datasources_temporal_es = COnVIDa.get_data_items_names(DataType.TEMPORAL, language='ES')
        datasources_temporal_es_indiv = []
        for i in datasources_temporal_es.values():
            for j in i:
                datasources_temporal_es_indiv.append(j)

        datasources_temporal_en = COnVIDa.get_data_items_names(DataType.TEMPORAL, language='EN')
        datasources_temporal_en_indiv = []
        for i in datasources_temporal_en.values():
            for j in i:
                datasources_temporal_en_indiv.append(j)

        if all(elem in datasources_temporal_es_indiv for elem in args['data']):
            lang = 'ES'
        elif all(elem in datasources_temporal_en_indiv for elem in args['data']):
            lang = 'EN'
        else:
            return "data_type error", 400

        start_date = pd.to_datetime(str(args['start_date']), format='%Y-%m-%d')
        end_date = pd.to_datetime(str(args['end_date']), format='%Y-%m-%d')

        data = convida_server.get_data_items(data_items=args['data'],
                                             regions=args['regions'],
                                             start_date=start_date,
                                             end_date=end_date, language=lang)

        data.index = data.index.astype(str)
        index = set(data.columns.get_level_values(0))
        json_out = {}

        for region in index:
            json_out[region] = json.dumps(json.loads(data[region].to_json(default_handler=dict)),
                                          sort_keys=True)
        return json_out


class RegionalRequest(Resource):
    def post(self):

        request.get_json(force=True)
        args = parser.parse_args()

        datasources_regional_es = COnVIDa.get_data_items_names(DataType.GEOGRAPHICAL, language='ES')
        datasources_regional_en = COnVIDa.get_data_items_names(DataType.GEOGRAPHICAL, language='EN')

        lang = ''
        if all(elem in list(datasources_regional_es.values())[0] for elem in args['data']):
            lang = 'ES'
        elif all(elem in list(datasources_regional_en.values())[0] for elem in args['data']):
            lang = 'EN'
        else:
            return "data_type error", 400

        data = convida_server.get_data_items(data_items=args['data'],
                                             regions=args['regions'],
                                             language=lang)

        index = set(data.columns.get_level_values(0))
        json_out = {}

        for region in index:
            json_out[region] = json.dumps(json.loads(data[region].to_json(default_handler=dict)),
                                          sort_keys=True)

        return json_out
