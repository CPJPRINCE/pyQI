"""
pyQi Async Module

This is a Python Module for asynchronously utilising Qi's API

author: Christopher Prince
license: Apache License 2.0"
"""

import json, os, logging
from .json_builder import JsonBuilder
from .common import QiRecord, QiRecords, QiAuthentication, _response_exception_handler, base64_encode, parse_data
import asyncio, aiohttp

logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    pd = None
    logger.warning("Pandas library not found. Install with: pip install pandas to enable DataFrame functionality. Some functions may not work without pandas.")

class QiAPIAsync(QiAuthentication):
    
    def __init__(self, username: str, server: str, password: str|None = None, protocol: str = "https", credentials_file: str|None = None, **kwargs):
        super().__init__(username, server, password, protocol, credentials_file, **kwargs)
        self.root_url = f"{protocol}://{self.server}/api"
        if "types_data" in kwargs:
            self.types_data: str|None = kwargs.get("types_data", None)
        else:
            self.types_data = None

        self.create_sem()
        self.create_session()

    def create_sem(self, limit: int = 10):
        self.sem = asyncio.Semaphore(limit)
        self.task_list = []

    def create_session(self, tcp_limit: int = 100):
        connector = aiohttp.TCPConnector(limit=tcp_limit)
        self.session = aiohttp.ClientSession(connector=connector)
        return self.session
    
    async def close_session(self):
        if self.session is not None:
            await self.session.close()

    async def get_types(self):
        async with self.sem:
            url = self.root_url + "/get/types"
            async with self.session.get(url, auth=aiohttp.BasicAuth(str(self.auth.username), str(self.auth.password))) as r:
                types_data = await r.text()
            return types_data
        
    async def lookup_table_id(self, table: str):
        if self.types_data is None:
            self.types_data = await self.get_types()
        self.table_fields = json.loads(str(self.types_data))[table]
        self.table_id = self.table_fields['id']
        return self.table_id

    async def lookup_relationship(self):
        self.relationships_set = set()
        for header in self.column_headers:
            if "relationship:" in header:
                relation = header.split(":")[1]
                split_fields = header.split(":")[0::2]
                await self.lookup_table_id(relation)
                split_fields.insert(1,self.table_id)
                new_name = ":".join(split_fields)
                self.df = self.df.rename(columns={header: new_name})
    
    # Old Version - Double check 
    # async def relationship_lookup(self):
    #     self.relationships_set = set()
    #     for header in self.column_headers:
    #         if "relationships:" in header:
    #             self.relationships_set.add(header.split(":")[1])
    #     self.relations_lookup_dict = dict()
    #     for relationship in self.relationships_set:
    #         table_id = await self.lookup_table_id(relationship)
    #         self.relations_lookup_dict.update({'Header': relationship, "TableId": table_id})

    async def get_list(self, list_name: str):
        async with self.sem:
            url = self.root_url + f"/get/{list_name}"
            async with self.session.get(url, auth=aiohttp.BasicAuth(str(self.auth.username), str(self.auth.password))) as r:
                self.list_data = await r.text()
            return self.list_data
    
    async def lookup_list(self, table: str, field_name: str):
        self.list_dict = dict()
        j = json.loads(str(self.types_data))[table]['fields']
        for field in j:
            if field.get('name') == field_name and field.get('source_table') is not None:
                await self.get_list(list_name = field.get('source_table'))
                self.list_fields = json.loads(str(self.list_data))['records']
                for f in self.list_fields:
                    self.list_dict.update({str(f.get('name')).lower(): f.get('id')})

    async def lookup_lists(self, table: str):
        if self.types_data is None:
            self.types_data = await self.get_types()
        for header in self.column_headers:
            if "list:" in header:
                list_name = header.split(":")[1]
                await self.lookup_list(table = table, field_name = list_name)
                list_values = self.df[header].values.tolist()
                id_list = [self.list_dict.get(str(item).lower()) for item in list_values]      
                if None in id_list:
                    log_msg = f'One or more values in column "{header}" do not match any entries in the corresponding Qi list. This will cause an invalidation of rule. Halting program.'
                    logger.error(log_msg)
                    raise ValueError(log_msg)
                self.df = self.df.rename(columns={header:list_name})
                self.df[list_name] = id_list

    async def get_request(self, table: str, fields_to_search: list[str]|str|None = None, search_term: list[str]|str|None = None, print_response: bool = False, **kwargs):
        async with self.sem:
            method = "get"
            self.print_response = print_response

            if search_term is not None and fields_to_search is None:
                logger.info('No fields to search provided. Will default to a search of the entire Database.')
            # Handle fields_to_search and search_term for get request. Can be string or list. If both are lists, they will be combined into field/search term pairs.
            if fields_to_search:
                if isinstance(fields_to_search, str):
                    self.fields_to_search = list(dict.fromkeys(fields_to_search.split(",")))
                else:
                    self.fields_to_search = list(dict.fromkeys(fields_to_search))
            else:
                self.fields_to_search = None

            if search_term:
                if isinstance(search_term, str):
                    self.search_term = list(dict.fromkeys(search_term.split(",")))
                else:
                    self.search_term = list(dict.fromkeys(search_term))
            else:
                self.search_term = None
                
            if self.fields_to_search is not None and self.search_term is not None:
                if len(self.fields_to_search) > 1 and len(self.search_term) > 1:
                    self.fields_to_search = "/".join([x + "/" + base64_encode(y) for x,y in zip(self.fields_to_search,self.search_term)])
                    self.search_term = None
                else:
                    self.fields_to_search = ",".join(x for x in self.fields_to_search)
                    self.search_term = base64_encode(",".join(x for x in self.search_term))
            elif self.fields_to_search is not None or self.search_term is not None:
                if self.fields_to_search is not None:
                    self.fields_to_search = ",".join(x for x in self.fields_to_search)
                if self.search_term is not None:
                    self.search_term = base64_encode(",".join(x for x in self.search_term))

            # Handle kwargs for get request. Setting Params.
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
                params.append(f"_skip_relationship/{kwargs.get('skip_relationship')}")
            if "approve" in kwargs:
                params.append(f"_approve/{kwargs.get('approve')}")
            if "facet_field" in kwargs:
                params.append(f"_facet_field/{kwargs.get('facet_field')}")
            if "since" in kwargs:
                params.append(f"_since/{kwargs.get('since')}")
            if "version_id" in kwargs:
                params.append(f"_version_id/{kwargs.get('version_id')}")
            if "translation_id" in kwargs:
                params.append(f"_translation_id/{kwargs.get('translation_id')}")
            if "offset" in kwargs: 
                params.append(f"_offset/{kwargs.get('offset')}")
                self.offset: int = kwargs.get('offset', 0)
            else:
                self.offset = 0

            # Field Parameter - this is a bit more complex as it can be set by kwargs or by the fields_to_search variable.
            # If both are set, they will be combined. This is because some get requests may require fields to search but also need to specify additional fields to return.
            if "fields" in kwargs or "fields_to_return" in kwargs:
                fields_to_return: str|list|None = kwargs.get('fields', None) or kwargs.get('fields_to_return', None)
                if fields_to_return is not None:
                    if isinstance(fields_to_return, str):
                        pass
                    elif isinstance(fields_to_return, list):
                        fields_to_return = ",".join(x for x in fields_to_return)
                    if self.fields_to_search:
                        params.append(f"_fields/{base64_encode(self.fields_to_search + ',' + fields_to_return)}")
                    else:
                        params.append(f"_fields/{base64_encode(fields_to_return)}")
            elif self.fields_to_search is not None:
                if self.fields_to_search == "id":
                    # Ignore Fields if ID is set, All fields are returned by default when searching by ID, and including the fields parameter causes an error. This is a quirk of the API.
                    pass
                else:
                    params.append(f"_fields/{base64_encode(self.fields_to_search)}")

            if params:
                self.params = '/'.join(x for x in params)

            # Construct URL based on parameters provided
            if self.search_term is not None and self.fields_to_search is not None:
                if params:
                    url = "/".join([self.root_url, method, table, self.fields_to_search, self.search_term, self.params])
                else:
                    url = "/".join([self.root_url, method, table, self.fields_to_search, self.search_term])
            elif self.fields_to_search is not None:
                if params:
                    url = "/".join([self.root_url, method, table, self.fields_to_search, self.params])
                else:
                    url = "/".join([self.root_url, method, table, self.fields_to_search])
            else:
                if params:
                    url = "/".join([self.root_url, method, table, self.params])
                else:
                    url = "/".join([self.root_url, method, table])
            await self._call_url_iter(url, method, data=None)
            return self.json_data
    
    async def put_request(self, data: str|dict, table: str, auto_approve: bool = False, print_response: bool = False):
        async with self.sem:
            self.print_response = print_response
            data = parse_data(data)
            method = "put"
            if auto_approve:
                url = "/".join([self.root_url, method, table, "_approve/yes"])
            else:
                url = "/".join([self.root_url, method, table])
            await self._call_url(url, method=method, data=data)

    async def post_request(self, data: str|dict, table: str, auto_approve: bool = False, print_response: bool = False):
        async with self.sem:
            self.print_response = print_response
            data = parse_data(data)
            method = "post"
            if auto_approve:
                url = "/".join([self.root_url, method, table, "_approve/yes"])
            else:
                url = "/".join([self.root_url, method, table])
            await self._call_url(url, method=method, data=data)

    async def delete_request(self, table: str, id_to_delete: int|str, auto_approve: bool = False, print_response: bool = False):
        async with self.sem:
            field_url = "id"
            self.print_response = print_response
            id_to_delete = str(id_to_delete)
            method = "delete"
            if auto_approve:
                url = "/".join([self.root_url, method, table, field_url, id_to_delete,"_approve/yes"])
            else:
                url = "/".join([self.root_url, method, table, field_url, id_to_delete])
            await self._call_url(url, method=method, data=None)

    async def _call_url(self, url: str, method: str, data: dict|str|None = None):
        if not self.session:
            self.create_session()
        logger.info(f'Calling to: {url}')
        try:
            if method == "get":
                async with self.session.get(url=url,auth=aiohttp.BasicAuth(str(self.auth.username),str(self.auth.password))) as r:
                    self.status_code = r.status
                    _response_exception_handler(self.status_code, url)
                    self.response_text = await r.text()
                    self.json_data = json.loads(self.response_text)
            elif method == "put":
                async with self.session.put(url=url,auth=aiohttp.BasicAuth(str(self.auth.username),str(self.auth.password)), data = data) as r:
                    self.status_code = r.status
                    _response_exception_handler(self.status_code, url)
                    self.response_text = await r.text()
            elif method == "post":
                async with self.session.post(url=url,auth=aiohttp.BasicAuth(str(self.auth.username),str(self.auth.password)), data = data) as r:
                    self.status_code = r.status
                    _response_exception_handler(self.status_code, url)
                    self.response_text = await r.text()
            elif method == "delete":
                async with self.session.delete(url=url,auth=aiohttp.BasicAuth(str(self.auth.username),str(self.auth.password))) as r:
                    self.status_code = r.status
                    _response_exception_handler(self.status_code, url)
                    self.response_text = await r.text()
            else:
                logger.error(f"Invalid HTTP method: {method}")
                raise ValueError(f"Invalid HTTP method: {method}")
            if self.print_response:
                logger.info(f"Status Code: {self.status_code}, Response Text: {self.response_text}")
        except KeyboardInterrupt:
            logger.warning('Process interrupted by user.')
            raise SystemExit()
        except Exception as e:
            logger.error(f"An error occurred: {e} calling to URL: {url}, Status Code: {self.status_code}")


    async def _call_url_iter(self, url: str, method: str = "get", data: dict|str|None = None):
        try:
            root_url = url 
            await self._call_url(url, method=method, data=data)
            add_json_data = self.json_data
            init_count = add_json_data['count']
            logger.info(f'Total Results: {init_count}')        
            if init_count >= 500:
                logger.info(f'Iterating over results...')
                while True:
                    count = init_count - self.offset 
                    if count >= 500:
                        self.offset += 500     
                        url = "/".join([root_url, "_offset",str(self.offset)])
                        await self._call_url(url, method=method, data=data)
                        new_json_data = self.json_data
                        add_json_data['records'].extend(new_json_data['records'])
                    else:
                        break
            self.json_data = add_json_data
            return self.json_data
        except KeyboardInterrupt:
            logger.warning('Process interrupted by user. Returning data retrieved so far...')
            return self.json_data
        except Exception as e:
            log_msg = f"An error occurred during iterative retrieval: {e}."
            logger.exception(log_msg)
            raise SystemError()

    async def find_record(self, table: str, fields_to_search: str, search_term: str, fields_to_return: str|None = None, print_response: bool = False):
        await self.get_request(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, fields = fields_to_return)
        return QiRecord(**self.json_data['records'][0])
    
    async def find_record_by_id(self, table: str, id: str|int, fields_to_return: str|None = None, print_response: bool = False):
        await self.get_request(table = table, fields_to_search = "id", search_term = str(id), print_response = print_response, fields = fields_to_return)
        return QiRecord(**self.json_data['records'][0])

    async def search_to_excel(self, output_file: str, table: str, fields_to_search: str, search_term: str|None = None, print_response: bool = False, **kwargs):
        if pd is None:
            log_msg = "Pandas library is required for this function. Install with: pip install pandas"
            logger.error(log_msg)
            raise ImportError(log_msg)
        await self.search_to_records(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **kwargs)
        df = pd.DataFrame([vars(s) for s in self.qi_records.records])
        df.to_excel(output_file, index = False)

    async def search_to_csv(self, output_file: str, table: str, fields_to_search: str, search_term: str|None = None, print_response: bool = False, **kwargs):
        if pd is None:
            log_msg = "Pandas library is required for this function. Install with: pip install pandas"
            logger.error(log_msg)
            raise ImportError(log_msg)
        await self.search_to_records(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **kwargs)
        df = pd.DataFrame([vars(s) for s in self.qi_records.records])
        df.to_csv(output_file, index = False)

    async def search_to_json_df(self, output_file: str, table: str, fields_to_search: str, search_term: str|None = None, print_response: bool = False, **kwargs):
        if pd is None:
            log_msg = "Pandas library is required for this function. Install with: pip install pandas"
            logger.error(log_msg)
            raise ImportError(log_msg)
        await self.search_to_records(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **kwargs)
        df = pd.DataFrame([vars(s) for s in self.qi_records.records])
        df.to_json(output_file, orient = "records", lines = True)

    async def search_to_json(self, output_file: str, table: str, fields_to_search: str, search_term: str|None = None, print_response: bool = False, **kwargs):
        await self.search_to_records(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **kwargs)
        self.qi_records.json_to_file(output_file)

    async def search_to_json_string(self, table: str, fields_to_search: str, search_term: str|None = None, print_response: bool = False, **kwargs) -> str:
        await self.search_to_records(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **kwargs)
        json_string = self.qi_records.json_tostring()
        return json_string

    async def search_to_xml(self, output_file: str, table: str, fields_to_search: str, search_term: str|None = None, print_response: bool = False, **kwargs):
        if pd is None:
            log_msg = "Pandas library is required for this function. Install with: pip install pandas"
            logger.error(log_msg)
            raise ImportError(log_msg)
        await self.search_to_records(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **kwargs)
        df = pd.DataFrame([vars(s) for s in self.qi_records.records])
        df.to_xml(output_file, index = False)

    async def search_to_df(self, table: str, fields_to_search: str, search_term: str|None = None, print_response: bool = False, **kwargs):
        if pd is None:
            log_msg = "Pandas library is required for this function. Install with: pip install pandas"
            logger.error(log_msg)
            raise ImportError(log_msg)
        await self.search_to_records(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **kwargs)
        df = pd.DataFrame([vars(s) for s in self.qi_records.records])
        return df
    
    async def search_to_dict(self, table: str, fields_to_search: str, search_term: str|None = None, print_response: bool = False, **kwargs):
        await self.search_to_records(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **kwargs)
        dict_list = [vars(s) for s in self.qi_records.records]
        return dict_list

    async def search_to_records(self, table: str, fields_to_search: str, search_term: str|None = None, print_response: bool = False, **kwargs):
        json_data = await self.get_request(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **kwargs)
        self.qi_records = QiRecords(json_data)
        return self.qi_records.records

    def _read_source(self, file: str, delim: str|None = None):
        if pd is None:
            log_msg = "Pandas library is required for this function. Install with: pip install pandas"
            logger.error(log_msg)
            raise ImportError(log_msg)
        path = os.path.abspath(file)
        if path.endswith(('csv', 'txt', 'tsv')):
            if delim is None:
                delim = '\t' if path.endswith('tsv') else ','
            self.df = pd.read_csv(path, sep = delim)
        elif path.endswith(('xlsx', 'xls', 'xlsm')):
            self.df = pd.read_excel(path, engine='openpyxl')
        elif path.endswith(('ods', 'odt', 'ots')):
            self.df = pd.read_excel(path, engine='odf')
        elif path.endswith('xml'):
            self.df = pd.read_xml(path) 

    async def import_from_file(self, file: str, table: str, auto_approve: bool = False, print_response: bool = False):
        self._read_source(file)
        node_id = await self.lookup_table_id(table)
        self.column_headers = list(self.df.columns.values)
        if any("relationship:" in x for x in self.column_headers):
            await self.lookup_relationship()
        if any("list:" in x for x in self.column_headers):
            await self.lookup_lists(table = table)
        records = self.df.to_dict('records')
        for row in records:
            record_dict = JsonBuilder(row).records_dict
            record_dict['record'].update({"node_id": node_id})
            self.task_list.append(asyncio.create_task(self.post_request(data = record_dict, table = table, auto_approve = auto_approve, print_response = print_response)))
        await asyncio.gather(*self.task_list)

    async def update_from_file(self, file: str, table: str, auto_approve: bool = False, lookup_field: str|None = None, print_response: bool = False):
        self._read_source(file)
        node_id = await self.lookup_table_id(table)
        self.column_headers = list(self.df.columns.values)
        if any("relationship:" in x for x in self.column_headers):
            await self.lookup_relationship()
        if any("list:" in x for x in self.column_headers):
            await self.lookup_lists(table = table)
        records = self.df.to_dict('records')
        for row in records:
            record_dict = JsonBuilder(row).records_dict
            id = record_dict['record'].get('id')
            if id is None:
                if lookup_field is not None:
                    lookup_term = record_dict.get(lookup_field, None)
                    if lookup_term is None:
                        log_msg = f"Lookup field '{lookup_field}' not found in record. Cannot perform lookup. Ending Program."
                        logger.error(log_msg)
                        raise ValueError(log_msg)
                    await self.get_request(table = table, fields_to_search = lookup_field, search_term = str(lookup_term), print_response = print_response)
                    j = json.loads(self.response_text)
                    id = j['records'][0]['id']
                else:
                    log_msg = 'No id data has been detected in spreadsheet and lookup_field has not been set. Ending Program'
                    logger.error(log_msg)
                    raise ValueError(log_msg)
            record_dict.update({'id': id, 'node_id': node_id})
            record_dict['record'].update({'id': id})
            self.task_list.append(asyncio.create_task(self.put_request(data = record_dict, table = table, auto_approve = auto_approve, print_response = print_response)))
        await asyncio.gather(*self.task_list)

    async def update_from_search(self, table: str, fields_to_update: dict, fields_to_search: str, search_term: str, auto_approve: bool = False, print_response: bool = False):
        if self.types_data is None:
            await self.get_types()
        type_j = json.loads(str(self.types_data))
        return_fields = set()
        for field in type_j[table]['fields']:
            if field.get('validation_rules') == "required":
                return_fields.add(field.get('name'))
        update_keys = set(fields_to_update.keys())
        return_fields = {"fields": ",".join(x for x in update_keys.union(return_fields))}
        search = await self.get_request(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response, **return_fields)
        for hit in search.get('records'):
            hit.update(fields_to_update)
            put_json = {"node_id": hit.get('node_id'), "id": hit.get('id'),"record": ""}
            hit.pop('media', None)
            put_json['record'] = hit
            self.task_list.append(asyncio.create_task(self.put_request(data = put_json, table = table, auto_approve = auto_approve, print_response = print_response)))
        await asyncio.gather(*self.task_list)

    async def delete_from_file(self, file: str, table: str, auto_approve: bool = False, lookup_field: str|None = None, print_response: bool = False):
        self._read_source(file)
        records = self.df.to_dict('records')
        for row in records:
            id = row.get('id')
            if id is None:
                if lookup_field is not None:
                    lookup_term = row.get(lookup_field)
                    await self.get_request(table = table, fields_to_search = lookup_field, search_term = lookup_term, print_response = print_response)
                    j = json.loads(self.response_text)
                    id = j['records'][0]['id']

                    # Old Version - Double Check
                    # Possibly to add a check here to see if multiple records are returned and handle accordingly.
                    # For now, it just takes the first record returned. This is a potential area for improvement.
                    # if len(j['records']) > 1:
                    #     input(f'Multiple matches have been found for {lookup_term}...')
                    #     id = j['records'][0]['id']
                    # else:
                    #     id = j['records'][0]['id']
                else:
                    log_msg = 'No id data has been detected in spreadsheet and lookup_field has not been set. Ending Program'
                    logger.error(log_msg)
                    raise ValueError(log_msg)
            self.task_list.append(asyncio.create_task(self.delete_request(table = table, id_to_delete = id, auto_approve = auto_approve, print_response = print_response)))
        await asyncio.gather(*self.task_list)

    async def delete_from_search(self, table: str, fields_to_search: str, search_term: str, auto_approve: bool = False, print_response: bool = False):
        search = await self.get_request(table = table, fields_to_search = fields_to_search, search_term = search_term, print_response = print_response)
        for hit in search.get('records'):
            if hit.get('deleted') is None:
                self.task_list.append(asyncio.create_task(self.delete_request(table = table, id_to_delete = hit.get('id'), auto_approve = auto_approve, print_response = print_response)))
        await asyncio.gather(*self.task_list)