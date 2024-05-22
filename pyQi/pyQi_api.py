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
import os

try:
    import pandas as pd
except:
    print('Pandas is not installed, excel import function will not function properly')
import time

class QiAPI():
    
    def __init__(self, username: str = None, password: str = None, server: str = None):
        self.username = username
        self.password = password
        self.server = server        
        self.rooturl = f"https://{self.server}/api"
        self.types_data = None 
    def base64_encode(self, x: str):
        if x:
            x = x.encode('ascii')
            x = base64.b64encode(x)
            x = "base64:" + x.decode('ascii').replace("=","~").replace("+","-").replace("/","_")
        return x

    def parse_data(self, d: str|dict):
        j = json.dumps(d)
        return j
    
    def get_types(self):
        url = self.rooturl + "/get/types"
        r = requests.get(url,auth=(self.username,self.password))
        self.types_data = r.text
        return self.types_data
        
    def lookup_table_id(self, table: str = None):
        if self.types_data is None:
            self.get_types()
        self.table_fields = json.loads(self.types_data)[table]
        self.table_id = self.table_fields['id']
        return self.table_id
    
    def lookup_relationship(self):
        self.relationships_set = set()
        for header in self.column_headers:
            if "relationship:" in header:
                relation = header.split(":")[1]
                split_fields = header.split(":")[0::2]
                self.lookup_table_id(relation)
                split_fields.insert(1,self.table_id)
                new_name = ":".join(split_fields)
                self.df = self.df.rename(columns={header: new_name})

    def get_list(self, list_name: str = None):
        url = self.rooturl + f"/get/{list_name}"
        r = requests.get(url,auth=(self.username,self.password))
        self.list_data = r.text
        return self.list_data
    
    def lookup_list(self, table: str = None, field_name: str = None):
        self.list_dict = dict()
        j = json.loads(self.types_data)[table]['fields']
        for field in j:
            if field.get('name') == field_name and field.get('source_table') is not None:
                self.get_list(list_name = field.get('source_table'))
                self.list_fields = json.loads(self.list_data)['records']
                for f in self.list_fields:
                    self.list_dict.update({str(f.get('name')).lower(): f.get('id')})

    def lookup_lists(self, table: str = None):
        if self.types_data is None:
            self.get_types()
        for header in self.column_headers:
            if "list:" in header:
                list_name = header.split(":")[1]
                self.lookup_list(table = table, field_name = list_name)
                list_values = self.df[header].values.tolist()
                id_list = [self.list_dict.get(str(item).lower()) for item in list_values]      
                if None in id_list:
                    print('A value does not match; this will cause an invalidation of rule. Halting program')
                    time.sleep(5)
                    raise SystemExit()
                self.df = self.df.rename(columns={header:list_name})
                self.df[list_name] = id_list

    def get_request(self,  table: str = None, fieldstosearch: set = {"id"}, searchterm: str = None, print_response: bool = False, **kwargs):
        self.table = table
        self.method = "get"
        self.print_response = print_response
        if fieldstosearch is None:
            self.fieldstosearchurl = ""
        if len(fieldstosearch) > 1:
            self.fieldstosearchurl = self.base64_encode(",".join(x for x in fieldstosearch))
        else:
            self.fieldstosearchurl = ",".join(x for x in fieldstosearch)
        if searchterm:
            self.searchterm = self.base64_encode(searchterm)
        else:
            self.searchterm = None
        params = []
        if "offset" in kwargs:
            params.append(f"_offset/{kwargs.get('offset')}")
        if "per_page" in kwargs:
            params.append(f"_per_page/{kwargs.get('per_page')}")
        if "sort_by" in kwargs:
            params.append(f"_sort_by/{kwargs.get('sort_by')}")
        if "sort_direction" in kwargs:
            params.append(f"_sort_direction/{kwargs.get('sort_direction')}")
        if "skip_relationship" in kwargs:
            params.append(f"_skip_relationship/{kwargs.get('sort_direction')}")
        if "approve" in kwargs:
            params.append(f"_approve/{kwargs.get('approve')}")
        if "facet_field" in kwargs:
            params.append(f"_facet_field/{kwargs.get('facet_field')}")
        if "since" in kwargs: params.append(f"_since/{kwargs.get('since')}")
        if "version_id" in kwargs:
            params.append(f"_version_id/{kwargs.get('version_id')}")
        if "translation_id" in kwargs:
            params.append(f"_translation_id/{kwargs.get('translation_id')}")
        if "offset" in kwargs: 
            params.append(f"_offset/{kwargs.get('offset')}")
            self.offset = kwargs.get('offset')
        else:
            self.offset = 0
        if self.fieldstosearchurl and "fields" in kwargs:
            params.append(f"_fields/{self.base64_encode(self.fieldstosearchurl + ',' + kwargs.get('fields'))}")
        elif "fields" in kwargs:
            params.append(f"_fields/{self.base64_encode(kwargs.get('fields'))}")
        elif self.fieldstosearchurl:
            params.append(f"_fields/{self.base64_encode(self.fieldstosearchurl)}")
        if params:
            self.paramsurl = '/'.join(x for x in params)
        if self.searchterm is not None:
            if params:
                url = "/".join([self.rooturl, self.method, self.table,self.fieldstosearchurl,self.searchterm,self.paramsurl])
            else:
                url = "/".join([self.rooturl, self.method, self.table,self.fieldstosearchurl,self.searchterm])
        else:
            if params:
                url = "/".join([self.rooturl, self.method, self.table,self.paramsurl])
            else:
                url = "/".join([self.rooturl, self.method, self.table])
        self.call_url_iter(url)
        return self.json_data
    
    def put_request(self, data: str|dict, table: str = None, auto_approve: bool = False, print_response: bool = False):
        self.table = table
        self.method = "put"
        self.print_response = print_response
        self.data = self.parse_data(data)
        if auto_approve: "/".join([self.rooturl, self.method, self.table,"_approve/yes"])
        else: url = "/".join([self.rooturl, self.method, self.table])
        self.call_url(url)

    def post_request(self, data: str|dict, table: str = None, auto_approve: bool = False, print_response: bool = False):
        self.table = table
        self.method = "post"
        self.print_response = print_response
        self.data = self.parse_data(data)
        if auto_approve: url = "/".join([self.rooturl, self.method, self.table,"_approve/yes"])
        else: url = "/".join([self.rooturl, self.method, self.table])
        self.call_url(url)

    def delete_request(self, table: str = None, id_to_delete: int = None, auto_approve: bool = False, print_response: bool = False):
        self.table = table
        self.method = "delete"
        self.fieldurl = "id"
        self.print_response = print_response
        self.id_to_delete = id_to_delete
        if auto_approve: url = "/".join([self.rooturl, self.method, self.table,self.fieldurl,self.id_to_delete,"_approve/yes"])
        else: url = "/".join([self.rooturl, self.method, self.table,self.fieldurl, self.id_to_delete])
        self.call_url(url)
    
    def call_url(self, url: str):
        print(f'Calling to: {url}')
        try:
            if self.method == "get":
                self.response = requests.get(url,auth=(self.username,self.password))
            if self.method == "put":
                self.response = requests.put(url,auth=(self.username,self.password),data=self.data)
            if self.method == "post":
                self.response = requests.post(url,auth=(self.username,self.password),data=self.data)
            if self.method == "delete":
                self.response = requests.delete(url,auth=(self.username,self.password))
            self.status_code = self.response.status_code
            if self.response.status_code == 200:
                pass
            elif self.response.status_code == 415:
                pass
            elif self.response.status_code == 403:
                pass
            elif self.response.status_code == 404:
                pass
            elif self.response.status_code == 401:
                pass
            elif self.response.status_code == 501:
                pass
            elif self.response.status_code == 500:
                pass
        except Exception as e:
            print(self.status_code)
            print(e)
        if self.method == "get":
            self.response_text = self.response.text
            self.json_data = json.loads(self.response.text)
        else:
            self.response_text = self.response.text
        if self.print_response:
            print(f"Status Code: {self.status_code}, Response Text: {self.response_text}")

    def call_url_iter(self, url: str):
        try:
            root_url = url 
            self.call_url(url)
            add_json_data = self.json_data
            init_count = add_json_data['count']
            print(f'Total Results: {init_count}')        
            if init_count >= 500:
                print(f'Iterating over results...')
                while True:
                    count = init_count - self.offset 
                    if count >= 500:
                        self.offset += 500     
                        url = "/".join([root_url, "_offset",str(self.offset)])
                        self.call_url(url)
                        new_json_data = self.json_data
                        add_json_data['records'].extend(new_json_data['records'])
                    else:
                        break
            self.json_data = add_json_data
            return self.json_data
        except Exception as e:
            print(e)
            raise SystemError()

    def search_to_spread():
        pass

    def read_spreadsheet(self, file: str, delim: str = None):
        path = os.path.abspath(file)
        if path.endswith('csv'):
            self.df = pd.read_csv(path, sep = delim)
        elif path.endswith(('xlsx','xls','xlsm')):
            self.df = pd.read_excel(path, engine='openpyxl')
        elif path.endswith('ods'):
            self.df = pd.read_excel(path, engine='odf')
        elif path.endswith('xml'):
            self.df = pd.read_xml(path) 
        
    def import_from_spread(self, file: str, table: str, auto_approve: bool = False, print_response: bool = False):
        self.read_spreadsheet(file)
        node_id = self.lookup_table_id(table)
        self.column_headers = list(self.df.columns.values)
        if any("relationship:" in x for x in self.column_headers):
            self.lookup_relationship()
        if any("list:" in x for x in self.column_headers):
            self.lookup_lists(table = table)
        xl_records = self.df.to_dict('records')
        for row in xl_records:
            record_dict = JsonBuilder(row).records_dict
            record_dict['record'].update({"node_id": node_id})
            self.post_request(data = record_dict, table = table, auto_approve = auto_approve, print_response = print_response)

    def update_from_spread(self, file: str, table: str, auto_approve: bool = False, lookup_field: str = None, print_response: bool = False):
        self.read_spreadsheet(file)
        node_id = self.lookup_table_id(table)
        self.column_headers = list(self.df.columns.values)
        if any("relationship:" in x for x in self.column_headers):
            self.lookup_relationship()
        if any("list:" in x for x in self.column_headers):
            self.lookup_lists(table = table)
        xl_records = self.df.to_dict('records')
        for row in  xl_records:
            record_dict = JsonBuilder(row).records_dict
            id = record_dict.get('id')
            if id is None:
                if lookup_field is not None:
                    lookup_term = record_dict.get(lookup_field)
                    self.get_request(table = table, fieldstosearch = {lookup_field}, searchterm = lookup_term, print_response = print_response)
                    j = json.loads(self.response_text)
                    id = j['records'][0]['id']
                else:
                    print('No id data has been detected in spreadsheet and lookup_field has not been set. Ending Program')
                    time.sleep(5)
                    raise SystemExit()
            record_dict.update({'id':id,'node_id': node_id})
            record_dict['record'].update({'id': id})
            self.put_request(data = record_dict, table = table, auto_approve = auto_approve, print_response = print_response)

    def delete_from_spread(self, file: str, table: str, auto_approve: bool = False, lookup_field: str = None, print_response: bool = False):
        self.read_spreadsheet(file)
        xl_records = self.df.to_dict('records')
        for row in xl_records:
            id = row.get('id')
            if id is None:
                if lookup_field is not None:
                    lookup_term = row.get(lookup_field)
                    self.get_request(table = table, fieldstosearch = {lookup_field}, searchterm = lookup_term, print_response = print_response)
                    j = json.loads(self.response_text)
                    if len(j['records']) > 1:
                        input(f'Multiple matches have been forund for {lookup_term}...')
                        id = j['records'][0]['id']
                    else:
                        id = j['records'][0]['id']
                else:
                    print('No id data has been detected in spreadsheet and lookup_field has not been set. Ending Program')
                    time.sleep(5)
                    raise SystemExit()
            self.delete_request(table = table, id_to_delete = id, auto_approve = auto_approve, print_response = print_response)

    def delete_from_search(self, table: str, fieldstosearch: set, searchterm: str, auto_approve: bool = False, print_response: bool = False):
        search = self.get_request(table = table, fieldstosearch = fieldstosearch, searchterm = searchterm, print_response = print_response)
        for hit in search.get('records'):
            if hit.get('deleted') is None:
                self.delete_request(table = table, id_to_delete = hit.get('id'), auto_approve = auto_approve, print_response = print_response)

    def update_from_search(self, table: str, fieldstoupdate: dict, fieldstosearch: set, searchterm: str, auto_approve: bool = False, print_response: bool = False):
        if self.types_data is None:
            self.get_types()
        type_j = json.loads(self.types_data)
        returnfields = set()
        for field in type_j[table]['fields']:
            if field.get('validation_rules') == "required":
                returnfields.add(field.get('name'))
        updatekeys = set(fieldstoupdate.keys())
        returnfields = {"fields": ",".join(x for x in updatekeys.union(returnfields))}
        search = self.get_request(table = table, fieldstosearch = fieldstosearch, searchterm = searchterm, **returnfields, print_response = print_response)
        for hit in search.get('records'):
            hit.update(fieldstoupdate)
            put_json = {"node_id": hit.get('node_id'), "id": hit.get('id'),"record": ""}
            hit.pop('media', None)
            put_json['record'] = hit
            self.put_request(data = put_json, table = table, auto_approve = auto_approve, print_response = print_response)

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
        for arg in kwargs.items():
            setattr(self,arg[0],arg[1])