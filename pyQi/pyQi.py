"""
pyQi Module

This is a Python Module for utilising Qi's API

author: Christopher Prince
license: Apache License 2.0"
"""

import base64
import requests
import json
from pyQi.xltojson import JsonBuilder
try:
    import pandas as pd
except:
    print('Pandas is not installed, excel import function will not function properly')
import time

class QiAPI():
    
    def __init__(self,username: str = None, password: str = None, server: str = None):
        self.username = username
        self.password = password
        self.server = server        
        self.rooturl = f"https://{self.server}/api"
    
    def base64_encode(self, x):
        if x:
            x = x.encode('ascii')
            x = base64.b64encode(x)
            x = "base64:" + x.decode('ascii').replace("=","~").replace("+","-").replace("/","_")
        return x
    
    def get_types(self):
        url = self.rooturl + "/get/types"
        r = requests.get(url,auth=(self.username,self.password))
        self.types_data = r.text
        return self.types_data
        
    def lookup_table_id(self,table: str = None):
        self.get_types()
        self.table_fields = json.loads(self.types_data)[table]
        self.table_id = self.table_fields['id']
        return self.table_id
        
    def get_request(self,table: str = None, method: str = "get", fieldstosearch: set = {"id"}, searchterm: str = None,**kwargs):
        self.table = table
        self.method = method
        if fieldstosearch is None: self.fieldstosearchurl = ""
        if len(fieldstosearch) > 1: self.fieldstosearchurl = self.base64_encode(",".join(x for x in fieldstosearch))
        else: self.fieldstosearchurl = ",".join(x for x in fieldstosearch)
        if searchterm: self.searchterm = self.base64_encode(searchterm)
        else: self.searchterm = None
        params = []
        if "offset" in kwargs: params.append(f"_offset/{kwargs.get('offset')}")
        if "per_page" in kwargs: params.append(f"_per_page/{kwargs.get('per_page')}")
        if "sort_by" in kwargs: params.append(f"_sort_by/{kwargs.get('sort_by')}")
        if "sort_direction" in kwargs: params.append(f"_sort_direction/{kwargs.get('sort_direction')}")
        if "skip_relationship" in kwargs: params.append(f"_skip_relationship/{kwargs.get('sort_direction')}")
        if "approve" in kwargs: params.append(f"_approve/{kwargs.get('approve')}")
        if "facet_field" in kwargs: params.append(f"_facet_field/{kwargs.get('facet_field')}")
        if "since" in kwargs: params.append(f"_since/{kwargs.get('since')}")
        if "version_id" in kwargs: params.append(f"_version_id/{kwargs.get('version_id')}")
        if "translation_id" in kwargs: params.append(f"_translation_id/{kwargs.get('translation_id')}")
        if "offset" in kwargs: 
            params.append(f"_offset/{kwargs.get('offset')}")
            self.offset = kwargs.get('offset')
        else: self.offset = 0
        if self.fieldstosearchurl and "fields" in kwargs: params.append(f"_fields/{self.base64_encode(self.fieldstosearchurl + ',' + kwargs.get('fields'))}")
        elif "fields" in kwargs: params.append(f"_fields/{self.base64_encode(kwargs.get('fields'))}")
        elif self.fieldstosearchurl: params.append(f"_fields/{self.base64_encode(self.fieldstosearchurl)}")
        if params: self.paramsurl = '/'.join(x for x in params)
        if self.searchterm is not None:
            if params: url = "/".join([self.rooturl, self.method, self.table,self.fieldstosearchurl,self.searchterm,self.paramsurl]);print(url)
            else: url = "/".join([self.rooturl, self.method, self.table,self.fieldstosearchurl,self.searchterm])
        else:
            if params: url = "/".join([self.rooturl, self.method, self.table,self.paramsurl])
            else: url = "/".join([self.rooturl, self.method, self.table])
        self.call_url_iter(url)
        return self.json_data
    
    def put_request(self,data: str,table: str = None, method: str = "put", auto_approve: bool = False):
        self.table = table
        self.method = method
        self.data = data
        if auto_approve: "/".join([self.rooturl, self.method, self.table,"_approve/yes"])
        else: url = "/".join([self.rooturl, self.method, self.table])
        self.call_url(url)

    def post_request(self,data: str,table: str = None, method: str = "post", auto_approve: bool = False):
        self.table = table
        self.method = method
        self.data = data
        if auto_approve: url = "/".join([self.rooturl, self.method, self.table,"_approve/yes"])
        else: url = "/".join([self.rooturl, self.method, self.table])
        self.call_url(url)

    def delete_request(self, table: str = None, method: str = "delete", id_to_delete: int = None, auto_approve: bool = False):
        self.table = table
        self.method = method
        self.fieldurl = "id"
        self.id_to_delete = id_to_delete
        if auto_approve: url = "/".join([self.rooturl, self.method, self.table,self.fieldurl,self.id_to_delete,"_approve/yes"])
        else: url = "/".join([self.rooturl, self.method, self.table,self.fieldurl, self.id_to_delete])
        self.call_url(url)

    def call_url(self,url):
        print(f'Calling to: {url}')
        try:
            if self.method == "get": r = requests.get(url,auth=(self.username,self.password))
            if self.method == "put": r = requests.put(url,auth=(self.username,self.password),data=self.data)
            if self.method == "post": r = requests.post(url,auth=(self.username,self.password),data=self.data)
            if self.method == "delete": r = requests.delete(url,auth=(self.username,self.password))
            self.status_code = r.status_code
            if r.status_code == 404:
                pass
            elif r.status_code == 401:
                pass
            elif r.status_code == 501:
                pass
            elif r.status_code == 500:
                print(r.status_code)
                print(r.text)
        except Exception as e:
            print(self.status_code)
            print(e)
        self.response = r
        if self.method == "get":
            self.response_text = r.text
            self.json_data = json.loads(r.text)
        else:
            self.response_text = r.text

    def call_url_iter(self,url):
        try:
            root_url = url 
            self.call_url(url)
            ljson_data = self.json_data
            init_count = ljson_data['count']
            print(f'Total Results: {init_count}')        
            if init_count >= 500:
                print(f'Iterating over results...')
                while True:
                    try:
                        count = init_count - self.offset 
                        if count >= 500:
                            self.offset += 500     
                            url = "/".join([root_url, "_offset",str(self.offset)])
                            self.call_url(url)
                            new_json_data = self.json_data
                            ljson_data['records'].extend(new_json_data['records'])
                        else: break
                    except Exception as e:
                        print(e)
                        raise SystemError()
            self.json_data = ljson_data
            return self.json_data
        except Exception as e:
            print(e)
            raise SystemError()
        
    def import_from_csv(file):
        pass

    def import_from_excel(self,file):
        df = pd.read_excel(file)
        xl_records = df.to_dict('records')
        for n,row in enumerate(xl_records,1):
            table = row.get('table')
            if table is None: print('Please ensure a \'table\' header is present with the specified table'); time.sleep(5);raise SystemExit()
            record_json = JsonBuilder(table,row)
            if record_json.get('relationships'):
                if n < 1: #Temp to not repeat lookup...
                    for old_key in record_json.get('relationships'):
                        new_key = self.lookup_table_id(old_key)
                        record_json[old_key] = record_json[new_key]
                        
class QiRecords():
    def __init__(self,json_data):
        self.json_data = json_data
        self.total = len(self.json_data['records'])
        self.records_list = []        
        if self.json_data is None:
            print('No results found')
        else:
            for x in self.json_data['records']:
                record_dict = {}
                for y in x:
                    key = y
                    value = x[key]
                    record_dict[key] = value
                self.records_list.append(record_dict)
            self.records = self._records_dict_to_obj()

    def _records_dict_to_obj(self):
        record_list = []
        for record in self.records_list:
            rec = QiRecord(**record)
            record_list.append(rec)
        return record_list
    
    def load_json(self,json_data):
        json.loads(json_data)
        self.total = json_data['count']
        self.json_data = json_data['records']
        
    def json_tostring(self,json_string):
        self.json_data = json.dumps(json_string)
        return self.json_data

class QiRecord():
    def __init__(self,**kwargs):
        for arg in kwargs.items():
            setattr(self,arg[0],arg[1])            

def modify_from_csv(file):
    pass
        
__author__ = "Christopher Prince"
__version__ = "1.0.0"
__licence__ = "Apache Licence Version 2.0"