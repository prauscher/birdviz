#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from parser import parse
import pygraphviz as pgv

if len(sys.argv) != 2:
    raise Exception("Usage: birdviz.py <FILE>")

DEFAULT_TABLE_NAME = "default"

config = parse(open(sys.argv[1]))
graph = pgv.AGraph(layout="dot", label="Router " + config["router"][-1][1], directed=True, strict=False)

# http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-in-a-single-expression
def merge_dicts(a, b):
    return dict(list(a.items()) + list(b.items()))

def parse_filter(p):
    if p[0] in ["all", "none"]:
        return p[0]
    if p[0] == "filter":
        if isinstance(p[1], str):
            return "filter " + p[1]
        else:
            return "filtered"
    if p[0] == "where":
        return "filtered"

# Tables
graph.add_node("table_" + DEFAULT_TABLE_NAME, color="red")
if "table" in config:
    for table, in config["table"]:
        graph.add_node("table_" + table, color="red")

template_counter = {}
templates = {}
if "template" in config:
    for _t in config["template"]:
        type = _t[0]
        if len(_t) > 2:
            name = _t[1]
        else:
            template_counter[type] = template_counter[type] + 1 if type in template_counter else 1
            name = type + str(template_counter[type])

        templates[name] = _t[-1]
        if len(_t) > 3 and _t[2] == "from":
            templates[name] = merge_dicts(templates[_t[3]], templates[name])

protocol_counter = {}
for _p in config["protocol"]:
    type = _p[0]
    if len(_p) > 2:
        name = _p[1]
    else:
        protocol_counter[type] = protocol_counter[type] + 1 if type in protocol_counter else 1
        name = type + str(protocol_counter[type])

    protocol = _p[-1]
    if len(_p) > 3 and _p[2] == "from":
        protocol = merge_dicts(templates[_p[3]], _p[-1])

    table = DEFAULT_TABLE_NAME
    if "table" in protocol:
        table, = protocol["table"][-1]

    import_mode = parse_filter(protocol["import"][-1]) if "import" in protocol else "all"
    export_mode = parse_filter(protocol["export"][-1]) if "export" in protocol else "none"

    if type == "pipe":
        dummy, peer_table = protocol["peer"][-1];
        if import_mode != "none":
            graph.add_edge("table_" + peer_table, "table_" + table, label=import_mode if import_mode != "all" else "")
        if export_mode != "none":
            graph.add_edge("table_" + table, "table_" + peer_table, label=export_mode if export_mode != "all" else "")
    else:
        label = type + "_" + name
        if type == "static":
            # Static protocols never export a route
            export_mode = "none"
            label = label + "\n" + "\n".join(" ".join(route) for route in protocol["route"])
        elif type == "device":
            # device protocol never exports or import routes
            export_mode = "none"
            import_mode = "none"
        elif type == "direct":
            label = label + "\n" + "\n".join("\n".join(interfaces) for interfaces in protocol["interface"])
        elif type == "kernel":
            if "kernel" in protocol:
                label = label + "\n" + "table " + protocol["kernel"][-1][0]
        elif type == "bgp":
            label = label + "\n" + "neighbor " + " ".join(protocol["neighbor"][-1])
        elif type == "ospf":
            label = label + "\n" + "\n".join(area + ": " + " ".join(interface for interface, interface_config in area_config["interface"]) for area, area_config in protocol["area"])

        graph.add_node(label, color="blue")
        if import_mode != "none":
            graph.add_edge(label, "table_" + table, label=import_mode if import_mode != "all" else "")
        if export_mode != "none":
            graph.add_edge("table_" + table, label, label=export_mode if export_mode != "all" else "")
#    else:
#        print(type)

print(graph.string())
