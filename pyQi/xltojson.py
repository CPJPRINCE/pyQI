"""
Module for parsing Excel Spreadsheets to Json.

author: Christopher Prince
license: Apache License 2.0"
"""


class JsonBuilder():
    def __init__(self, table: str, data: dict):
        self.table = table
#        self.table_id = self.lookup_table_id(table)
        self.data = data
        self.relationships_dict = {"relationships": None}
        self.records_dict = dict()
        self.relationships_list = list()
        self.parse_data_init()
        if self.relations_set: self.parse_data_relationships()
        self.parse_data_final()
        
    def parse_data_init(self):
        self.record_info_dict = dict()
        self.relations_set = set()        
        for record in self.data:
            if ":" in record:
                self.relations_set.add(record.split(":")[1])
            else: self.record_info_dict.update({record:self.data.get(record)})
        self.relations_set = sorted(self.relations_set)
    
    def parse_data_relationships(self):
        relations_dict = {}        
        for relation in sorted(self.relations_set):
            relation_dict = {}
            filter_list = [entry for entry in self.data if relation in entry]
            relations_list = []
            for rel in filter_list:
                relation_field = rel.split(":")
                r = self.data.get(rel)
                relation_dict.update({relation_field[2]:r})
                relations_list.append(relation_dict)
            relations_dict.update({relation:relations_list})
        self.relationships_dict.update({"relationships": relations_dict})
    
    def parse_data_final(self):
        self.records_dict = {"record": self.record_info_dict}
        if self.relationships_dict.get('relationships') is None: self.final_dict = self.records_dict
        else: self.final_dict = {**self.records_dict, **self.relationships_dict}