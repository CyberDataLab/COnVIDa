from flask import Flask, jsonify, request
from flask_restful import Resource, Api, reqparse
import os, sys

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
    api.add_resource(Test, '/test')
    api.add_resource(Test2, '/test2')
    api.add_resource(TestPost, '/testpost')


class Test(Resource):
    def get(self):
        return {'test': 'enrique'}


parser = reqparse.RequestParser()
parser.add_argument('data', type=list, location='json')
parser.add_argument('regions', type=list, location='json')
parser.add_argument('start_date', type=str)
parser.add_argument('end_date', type=str)

class TestPost(Resource):
    def post(self):
        """JSON Example

        data -> ['Daily cases', 'Daily PCR cases']
        regions -> ['Murcia']
        start_date -> 2020-01-01
        end_date -> 2020-05-13

        Returns
        -------

        """
        datasources = COnVIDa.get_data_items_names(DataType.TEMPORAL, language='EN')
        all_data_items = []
        for data_items in datasources.values():
            all_data_items += data_items

        request.get_json(force=True)
        args = parser.parse_args()

        start_date = pd.to_datetime(str(args['start_date']), format='%Y-%m-%d')
        end_date = pd.to_datetime(str(args['end_date']), format='%Y-%m-%d')

        data = convida_server.get_data_items(data_items=args['data'],
                                             regions=args['regions'],
                                             start_date=start_date,
                                             end_date=end_date, language='EN')

        return data.to_json(orient='split', default_handler=dict)

class Test2(Resource):
    def get(self):
        all_regions = Regions.get_regions('ES')
        datasources = COnVIDa.get_data_items_names(DataType.TEMPORAL, language='EN')
        all_data_items = []
        for data_items in datasources.values():
            all_data_items += data_items
        start_date = pd.to_datetime('2020-01-01', format='%Y-%m-%d')
        end_date = pd.to_datetime('2020-05-13', format='%Y-%m-%d')

        data = convida_server.get_data_items(data_items=[all_data_items[0]],
                                             regions=[all_regions[5]],
                                             start_date=start_date,
                                             end_date=end_date, language='EN')

        return data.to_json(orient='split', default_handler=dict)