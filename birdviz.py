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


config = birdconfig.parse(open(args.infile))
graph = pgv.AGraph(layout="dot", rankdir="LR", fontname="Monospace", fontsize=22, label="<<b>Router {}</b>>".format(config["router"][-1][1]), labelloc="t", directed=True, strict=False)

graph.node_attr["fontname"] = "Monospace"
graph.edge_attr["fontname"] = "Monospace"
graph.edge_attr["fontsize"] = 8

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
graph.add_node("table_master", label="<<b>table master</b>>", color="red", shape="oval")
if "table" in config:
    for table, in config["table"]:
        graph.add_node("table_" + table, label="<<b>table {}</b>>".format(table), color="red", shape="oval")

template_ids = defaultdict(lambda: 0)
templates = {}
if "template" in config:
    for _t in config["template"]:
        protocol = _t[0]
        if len(_t) > 2:
            name = _t[1]
        else:
            template_ids[protocol] += 1
            name = protocol + str(template_ids[protocol])

        templates[name] = dict()
        if len(_t) > 3 and _t[2] == "from":
            templates[name].update(templates[_t[3]])
        templates[name].update(_t[-1])

instance_ids = defaultdict(lambda: 0)
for _p in config["protocol"]:
    protocol = _p[0]
    if len(_p) > 2:
        name = _p[1]
    else:
        instance_ids[protocol] += 1
        name = protocol + str(instance_ids[protocol])

    instance = dict()
    if len(_p) > 3 and _p[2] == "from":
        instance.update(templates[_p[3]])
    instance.update(_p[-1])

    table = "master"
    if "table" in instance:
        table, = instance["table"][-1]

    import_mode = parse_filter(instance["import"][-1] if "import" in instance else ("all",))
    export_mode = parse_filter(instance["export"][-1] if "export" in instance else ("none",))

    if protocol == "pipe":
        dummy, peer_table = instance["peer"][-1]
        if import_mode:
            graph.add_edge("table_" + peer_table, "table_" + table, **filter_edge(import_mode))
        if export_mode:
            graph.add_edge("table_" + table, "table_" + peer_table, **filter_edge(export_mode))
    else:
        if protocol == "static":
            # Static protocols never export a route
            export_mode = False
            label = "<br/>".join(" ".join(route) for route in instance["route"])
        elif protocol == "device":
            # device protocol never exports or import routes
            export_mode = False
            import_mode = False
            label = ""
        elif protocol == "direct":
            label = "<br/>".join("<br/>".join(interfaces) for interfaces in instance["interface"])
        elif protocol == "kernel":
            if "kernel" in instance:
                label = "kernel table " + instance["kernel"][-1][1]
            else:
                label = ""
        elif protocol == "bgp":
            label = "neighbor " + " ".join(instance["neighbor"][-1])
        elif protocol == "ospf":
            label = "<br/>".join(area + ": " + " ".join(interface for interface, interface_config in area_config["interface"]) for area, area_config in instance["area"])
        else:
            label = ""

        graph.add_node("proto_" + name, label="<<b>{} {}</b><br/>{}>".format(protocol, name, label), color="blue", shape="box")
        if import_mode:
            graph.add_edge("proto_" + name, "table_" + table, **filter_edge(import_mode))
        if export_mode:
            graph.add_edge("table_" + table, "proto_" + name, **filter_edge(export_mode))

print(graph.string())
