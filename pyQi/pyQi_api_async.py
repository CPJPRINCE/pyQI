"""
pyQi Async Module

This is a Python Module for asynchronously utilising Qi's API

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
import asyncio
import aiohttp


class QiAPI():
    
    def __init__(self,username: str = None, password: str = None, server: str = None,loop = None):
        self.username = username
        self.password = password
        self.server = server        
        self.rooturl = f"https://{self.server}/api"
        self.loop = loop

    def create_sem(self, limit: int = 10):
        self.sem = asyncio.Semaphore(limit)
        self.task_list = []

    def create_session(self, tcp_limit: int = 100):
        connector = aiohttp.TCPConnector(limit=tcp_limit)
        if self.loop:
            self.session = aiohttp.ClientSession(loop=self.loop,connector=connector)
        else:
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session
    
    def close_session(self):
        if self.session is not None:
            return self.session.close()

    def base64_encode(self, x):
        if x:
            x = x.encode('ascii')
            x = base64.b64encode(x)
            x = "base64:" + x.decode('ascii').replace("=","~").replace("+","-").replace("/","_")
        return x

    def parse_data(self, d: str|dict):
        j = json.dumps(d)
        return j
    
    async def get_types(self):
        url = self.rooturl + "/get/types"
        r = requests.get(url,auth=(self.username,self.password))
        self.types_data = r.text
        return self.types_data
        
    async def lookup_table_id(self,table: str = None):
        await self.get_types()
        self.table_fields = json.loads(self.types_data)[table]
        self.table_id = self.table_fields['id']
        return self.table_id
        
    async def get_request(self,table: str = None, fieldstosearch: set = {"id"}, searchterm: str = None, print_response: bool = False, sem=asyncio.Semaphore(10),**kwargs):
        async with sem:
            self.table = table
            self.method = "get"
            self.print_response = print_response
            if fieldstosearch is None: self.fieldstosearchurl = ""
            if len(fieldstosearch) > 1: self.fieldstosearchurl = self.base64_encode(",".join(x for x in fieldstosearch))
            else: self.fieldstosearchurl = ",".join(x for x in fieldstosearch)
            if searchterm: self.searchterm = self.base64_encode(searchterm)
            else: self.searchterm = None
            params = []
            if "per_page" in kwargs: params.append(f"_per_page/{kwargs.get('per_page')}")
            if "sort_by" in kwargs: params.append(f"_sort_by/{kwargs.get('sort_by')}")
            if "sort_direction" in kwargs: params.append(f"_sort_direction/{kwargs.get('sort_direction')}")
            if "skip_relationship" in kwargs: params.append(f"_skip_relationship/{kwargs.get('sort_direction')}")
            if "approve" in kwargs: params.append(f"_approve/{kwargs.get('approve')}")
            if "facet_field" in kwargs: params.append(f"_facet_field/{kwargs.get('facet_field')}")
            if "since" in kwargs: params.append(f"_since/{kwargs.get('since')}")
            if "version_id" in kwargs: params.append(f"_version_id/{kwargs.get('version_id')}")
            if "translation_id" in kwargs:
                params.append(f"_translation_id/{kwargs.get('translation_id')}")
            if "offset" in kwargs:
                params.append(f"_offset/{kwargs.get('offset')}")
                self.offset = kwargs.get('offset')
            else: self.offset = 0
            if self.fieldstosearchurl and "fields" in kwargs: params.append(f"_fields/{self.base64_encode(self.fieldstosearchurl + ',' + kwargs.get('fields'))}")
            elif "fields" in kwargs: params.append(f"_fields/{self.base64_encode(kwargs.get('fields'))}")
            elif self.fieldstosearchurl: params.append(f"_fields/{self.base64_encode(self.fieldstosearchurl)}")
            if params: self.paramsurl = '/'.join(x for x in params)
            if self.searchterm is not None:
                if params: url = "/".join([self.rooturl, self.method, self.table,self.fieldstosearchurl,self.searchterm,self.paramsurl])
                else: url = "/".join([self.rooturl, self.method, self.table,self.fieldstosearchurl,self.searchterm])
            else:
                if params: url = "/".join([self.rooturl, self.method, self.table,self.paramsurl])
                else: url = "/".join([self.rooturl, self.method, self.table])
            self.create_session()
            await self.call_url_iter(url)
            #await self.close_session()
            return self.json_data
    
    async def put_request(self,table: str = None, data: str = None, auto_approve: bool = False, print_response: bool = False, sem = asyncio.Semaphore(10)):
        async with sem:
            self.table = table
            self.method = "put"
            self.print_response = print_response
            self.data = self.parse_data(data)
            if auto_approve: "/".join([self.rooturl, self.method, self.table,"_approve/yes"])
            else: url = "/".join([self.rooturl, self.method, self.table])
            self.create_session()
            await self.call_url(url)
            #await self.close_session()

    async def post_request(self,table: str = None, data: str = None, auto_approve: bool = False, print_response: bool = False, sem=asyncio.Semaphore(10)):
        async with sem:
            self.table = table
            self.method = "post"
            self.print_response = print_response
            self.data = self.parse_data(data)
            if auto_approve: url = "/".join([self.rooturl, self.method, self.table,"_approve/yes"])
            else: url = "/".join([self.rooturl, self.method, self.table])
            self.create_session()
            await self.call_url(url)
            #await self.close_session()

    async def delete_request(self, table: str = None, id_to_delete: int = None, auto_approve: bool = False, print_response: bool = False, sem=asyncio.Semaphore):
        async with sem:
            self.table = table
            self.method = "delete"
            self.fieldurl = "id"
            self.print_response = print_response
            self.id_to_delete = str(id_to_delete)
            if auto_approve: url = "/".join([self.rooturl, self.method, self.table,self.fieldurl,self.id_to_delete,"_approve/yes"])
            else: url = "/".join([self.rooturl, self.method, self.table, self.fieldurl, self.id_to_delete])
            self.create_session()
            await self.call_url(url)
            #await self.close_session()

    async def call_url(self, url):
        async with self.session as s:
            print(f'Calling to: {url}')
            if self.method == "get": 
                r = await s.get(url=url,auth=aiohttp.BasicAuth(self.username,self.password))
                self.status_code = r.status
                self.response_text = await r.text()
                self.json_data = json.loads(self.response_text)
                return self.json_data
            if self.method == "put":
                r = await s.put(url=url,auth=aiohttp.BasicAuth(self.username,self.password),data=self.data)
                self.response_text = await r.text()   
                self.status_code = r.status                 
            if self.method == "post": 
                r = await s.post(url=url,auth=aiohttp.BasicAuth(self.username,self.password),data=self.data)
                self.response_text = await r.text()      
                self.status_code = r.status              
            if self.method == "delete":
                r = s.delete(url=url,auth=aiohttp.BasicAuth(self.username,self.password))
                self.response_text = await r.text()      
                self.status_code = r.status
            if self.print_response:
                print(f"Status Code: {self.status_code}, Response Text: {self.response_text}")

    async def call_url_iter(self,url):
        try:
            root_url = url 
            await self.call_url(url)
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
                            await self.call_url(url)
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

    async def relationship_lookup(self):
        self.relationships_set = set()
        for header in self.column_headers:
            if "relationships:" in header:
                self.relationships_set.add(header.split(":")[1])
        self.relations_lookup_dict = dict()
        for relationship in self.relationships_set:
            table_id = await self.lookup_table_id(relationship)
            self.relations_lookup_dict.update({'Header': relationship, "TableId": table_id})

    async def import_from_spread(self, file: str, table: str, auto_approve: bool = False, print_response: bool = False, rate_limit: int = 10):
        if file.endswith('csv'):
            df = pd.read_csv(file)
        elif file.endswith('xlsx'):
            df = pd.read_excel(file)
        node_id = self.lookup_table_id(table)
        self.column_headers = list(df.columns.values)
        self.relationship_lookup()
        xl_records = df.to_dict('records')
        self.create_sem(rate_limit)
        for row in xl_records:
            record_dict = JsonBuilder(row).records_dict
            record_dict['record'].update({"node_id": node_id})
            if record_dict.get('relationships'):
                for relation in record_dict.get('relationships'):
                    table_id = self.relations_lookup_dict(relation)
                    record_dict[relation] = record_dict[table_id]
            self.task_list.append(asyncio.create_task(self.post_request(data = record_dict, table = table, auto_approve = auto_approve, print_response = print_response, sem = self.sem)))
        await asyncio.gather(*self.task_list)

    async def update_from_spread(self, file: str, table: str, auto_approve: bool = False, lookup_field: str = None, print_response: bool = False, rate_limit: int = 10):
        if file.endswith('csv'):
            df = pd.read_csv(file)
        elif file.endswith('xlsx'):
            df = pd.read_excel(file)
        node_id = self.lookup_table_id(table)
        self.column_headers = list(df.columns.values)
        self.relationship_lookup()
        xl_records = df.to_dict('records')
        self.create_sem(limit = rate_limit)
        for row in xl_records:
            record_dict = JsonBuilder(row).records_dict
            id = record_dict.get('id')
            if id is None:
                if lookup_field is not None:
                    lookup_term = record_dict.get(lookup_field)
                    #Simple await?
                    await self.get_request(table = table, fieldstosearch = {lookup_field}, searchterm = lookup_term, print_response = print_response, sem = self.sem)
                    j = json.loads(self.response_text)
                    id = j['records'][0]['id']
                else:
                    print('No id data has been detected in spreadsheet and lookup_field has not been set. Ending Program')
                    time.sleep(5)
                    raise SystemExit()
            record_dict.update({'id':id,'node_id': node_id})
            record_dict['record'].update({'id': id})
            if record_dict.get('relationships'):
                for relation in record_dict.get('relationships'):
                    table_id = self.relations_lookup_dict(relation)
                    record_dict[relation] = record_dict[table_id]
            self.task_list.append(asyncio.create_task(self.put_request(data = record_dict, table = table, auto_approve = auto_approve, print_response = print_response, sem = self.sem)))
        await asyncio.gather(*self.task_list)
   
    async def delete_from_spread(self, file: str, table: str, auto_approve: bool = False, lookup_field: str = None, print_response: bool = False, rate_limit: int = 10):
        if file.endswith('csv'):
            df = pd.read_csv(file)
        elif file.endswith('xlsx'):
            df = pd.read_excel(file)
        xl_records = df.to_dict('records')
        self.create_sem(limit = rate_limit)
        for row in xl_records:
            id = row.get('id')
            if id is None:
                if lookup_field is not None:
                    lookup_term = row.get(lookup_field)
                    #Simple Await?
                    await self.get_request(table = table, fieldstosearch = {lookup_field}, searchterm = lookup_term, print_response = print_response, sem = self.sem)
                    j = json.loads(self.response_text)
                    id = j['records'][0]['id']
                else:
                    print('No id data has been detected in spreadsheet and lookup_field has not been set. Ending Program')
                    time.sleep(5)
                    raise SystemExit()
            self.task_list.append(asyncio.create_task(self.delete_request(table = table, id_to_delete = id, auto_approve = auto_approve, print_response = print_response, sem = self.sem)))
        await asyncio.gather(*self.task_list)

    async def delete_from_search(self, table: str, fieldstosearch: set, searchterm: str, auto_approve: bool = False, print_response: bool = False, rate_limit: int = 10):
        search = await self.get_request(table = table, fieldstosearch = fieldstosearch, searchterm = searchterm, print_response = print_response)
        self.create_sem(limit = rate_limit)        
        for hit in search.get('records'):
            if hit.get('deleted') is None:
                self.task_list.append(asyncio.create_task(self.delete_request(table = table, id_to_delete = hit.get('id'), auto_approve = auto_approve, print_response = print_response, sem = self.sem)))
        await asyncio.gather(*self.task_list)

    async def update_from_search(self, table: str, fieldstoupdate: dict, fieldstosearch: set, searchterm: str, auto_approve: bool = False, print_response: bool = False, rate_limit: int = 10):
        await self.get_types()
        type_j = json.loads(self.types_data)
        returnfields = set()
        for field in type_j[table]['fields']:
            if field.get('validation_rules') == "required":
                returnfields.add(field.get('name'))
        updatekeys = set(fieldstoupdate.keys())
        returnfields = {"fields": ",".join(x for x in updatekeys.union(returnfields))}
        search = await self.get_request(table = table, fieldstosearch = fieldstosearch, searchterm = searchterm, **returnfields, print_response = print_response)
        self.create_sem(limit = rate_limit)
        for hit in search.get('records'):
            hit.update(fieldstoupdate)
            put_json = {"node_id": hit.get('node_id'), "id": hit.get('id'),"record": ""}
            hit.pop('media', None)
            put_json['record'] = hit
            self.task_list.append(asyncio.create_task(self.put_request(data = put_json, table = table, auto_approve = auto_approve, print_response = print_response, sem = self.sem)))
        await asyncio.gather(*self.task_list)

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