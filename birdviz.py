#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import birdconfig
from collections import defaultdict
import pygraphviz as pgv

import argparse
parser = argparse.ArgumentParser(description="BIRD/BIRD6 config visualizer")
parser.add_argument("infile", metavar="FILE", help="config file to visualize")
args = parser.parse_args()

DEFAULT_TABLE_NAME = "master"

config = birdconfig.parse(open(args.infile))
graph = pgv.AGraph(layout="dot", fontname="Monospace", fontsize=22, label="<<b>Router {}</b>>".format(config["router"][-1][1]), labelloc="t", directed=True, strict=False)

graph.node_attr['fontname'] = "Monospace"
graph.edge_attr['fontname'] = "Monospace"
graph.edge_attr['fontsize'] = 8

def parse_filter(p):
    if p[0] == "all":
        return True
    if p[0] == "none":
        return False
    if p[0] == "filter":
        if isinstance(p[1], str):
            return p[1]
        else:
            return "(filter)"
    if p[0] == "where":
        return "(filter)"

def filter_edge(flt):
    res = dict()
    if isinstance(flt, str):
        res.update(style="dashed")
        if flt != "(filter)":
            res.update(label="<<i>{}</i>>".format(flt))
    return res

# Tables
graph.add_node("table_" + DEFAULT_TABLE_NAME, label="<<b>table {}</b>>".format(DEFAULT_TABLE_NAME), color="red", shape="oval")
if "table" in config:
    for table, in config["table"]:
        graph.add_node("table_" + table, label="<<b>table {}</b>>".format(table), color="red", shape="oval")

template_counter = defaultdict(lambda: 0)
templates = {}
if "template" in config:
    for _t in config["template"]:
        type = _t[0]
        if len(_t) > 2:
            name = _t[1]
        else:
            template_counter[type] += 1
            name = type + str(template_counter[type])

        templates[name] = dict()
        if len(_t) > 3 and _t[2] == "from":
            templates[name].update(templates[_t[3]])
        templates[name].update(_t[-1])

protocol_counter = defaultdict(lambda: 0)
for _p in config["protocol"]:
    type = _p[0]
    if len(_p) > 2:
        name = _p[1]
    else:
        protocol_counter[type] += 1
        name = type + str(protocol_counter[type])

    protocol = dict()
    if len(_p) > 3 and _p[2] == "from":
        protocol.update(templates[_p[3]])
    protocol.update(_p[-1])

    table = DEFAULT_TABLE_NAME
    if "table" in protocol:
        table, = protocol["table"][-1]

    import_mode = parse_filter(protocol["import"][-1] if "import" in protocol else ("all",))
    export_mode = parse_filter(protocol["export"][-1] if "export" in protocol else ("none",))

    if type == "pipe":
        dummy, peer_table = protocol["peer"][-1]
        if import_mode:
            graph.add_edge("table_" + peer_table, "table_" + table, **filter_edge(import_mode))
        if export_mode:
            graph.add_edge("table_" + table, "table_" + peer_table, **filter_edge(export_mode))
    else:
        if type == "static":
            # Static protocols never export a route
            export_mode = False
            label = "<br/>".join(" ".join(route) for route in protocol["route"])
        elif type == "device":
            # device protocol never exports or import routes
            export_mode = False
            import_mode = False
            label = ""
        elif type == "direct":
            label = "<br/>".join("<br/>".join(interfaces) for interfaces in protocol["interface"])
        elif type == "kernel":
            if "kernel" in protocol:
                label = "kernel table " + protocol["kernel"][-1][1]
            else:
                label = ""
        elif type == "bgp":
            label = "neighbor " + " ".join(protocol["neighbor"][-1])
        elif type == "ospf":
            label = "<br/>".join(area + ": " + " ".join(interface for interface, interface_config in area_config["interface"]) for area, area_config in protocol["area"])
        else:
            label = ""

        graph.add_node("proto_" + name, label="<<b>{} {}</b><br/>{}>".format(type, name, label), color="blue", shape="box")
        if import_mode:
            graph.add_edge("proto_" + name, "table_" + table, **filter_edge(import_mode))
        if export_mode:
            graph.add_edge("table_" + table, "proto_" + name, **filter_edge(export_mode))
#    else:
#        print(type)

print(graph.string())
