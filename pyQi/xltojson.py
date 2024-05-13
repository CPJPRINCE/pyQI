"""
Module for parsing Excel Spreadsheets to Json.

author: Christopher Prince
license: Apache License 2.0"
"""


class JsonBuilder():
    def __init__(self,table,data: dict):
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
        self.records_dict = {"record":self.record_info_dict}
        if self.relationships_dict.get('relationships') is None: self.final_dict = self.records_dict
        else: self.final_dict = {**self.records_dict, **self.relationships_dict}
                
        
#Post Request
json_data = { 
    "record" : {
            "node_id" : "1",
            "name" : "Test",
            "collection_id" : "1",
            "medium": "oil on canvas",
            "accession_number" : "test-aabbcc", "copyright_notes" : "Test"
        },
    "relationships" : {
        "4" : [
            {
                "target_id" : "1245",
                "object_attribution_id" : "70",
                "qualifier" : "19 century"
            }
        ],
        "16" : [ 
            {
                "name" : "76.2 x 60.5",
                "height" : "76.2",
                "width" : "60.5"
            }
        ]
    }
}

#Put Request
{
    "node_id" : "1",
    "id" : "231213",
    "record" : {
        "id" : "231213",
        "name" : "Test (updated)",
        "collection_id" : "1",
        "medium" : "oil on canvas",
        "source_accession_number" : "TEST 1.2.3",
        "pcf_accession_number" : "TEST_123_123",
        "source_accession_number_normalised" : "TEST_1_2_3",
        "copyright_notes" : "Test note"
    },
    "relationships" : {
        "4" : [
            {
                "id" : "251525",
                "target_id" : "1245",
                "work_attribution_id" : "70",
                "qualifier" : "19 Century (updated)",
                "online" : "0"
            }
        ],
        "16" : [
            {
                "id" : "254133",
                "name": "76.2 x 63.4 (updated)",
                "height": "76.2",
                "width": "63.4",
                "type": None,
                "estimated": None,
                "deleted" : "1"
            }
        ]
    }
}