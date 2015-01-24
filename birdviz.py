#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import birdconfig
from collections import defaultdict
import pygraphviz as pgv

import argparse
parser = argparse.ArgumentParser(description="BIRD/BIRD6 config visualizer")
parser.add_argument("--compress", "-c", action="store_true", default=False, help="compress templated protocols into single nodes and approximate their imports/exports")
parser.add_argument("infile", metavar="FILE", help="config file to visualize")
args = parser.parse_args()


config = birdconfig.parse(open(args.infile))
graph = pgv.AGraph(layout="dot", rankdir="LR", fontname="Monospace", fontsize=22, label="<<b>Router {}</b>>".format(config["router"][-1][1]), labelloc="t", directed=True, strict=False)

graph.node_attr["fontname"] = "Monospace"
graph.edge_attr["fontname"] = "Monospace"
graph.edge_attr["fontsize"] = 8

def parse_filter(p):
    if p is None:
        return None

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
    res = dict(key=flt)
    if isinstance(flt, str):
        res.update(style="dashed")
        if flt != "(filter)":
            res.update(label="<<i>{}</i>>".format(flt))
    return res

def find_key(p, key, default=None):
    def recur(p):
        if key in p:
            return p[key]
        elif "_template" in p:
            return recur(templates[p["_template"]])
        else:
            return default
    return recur(p)

def find_option(p, default_template, *, use_default=True):
    option = birdconfig.parse(default_template)
    assert(len(option.keys()) == 1)
    default = next(iter(option.values())) if use_default else [None]
    option = find_key(p, next(iter(option.keys())), default=default)
    return option[-1]


# create table nodes

tables = set(table[0] for table in config["table"])
tables.add("master")

for table in tables:
    graph.add_node("table_{}".format(table), label="<<b>table {}</b>>".format(table), color="red", shape="oval")


# create template clusters/nodes

template_ids = defaultdict(lambda: 0)
templates = {}
for _t in config["template"]:
    protocol = _t[0]
    if len(_t) > 2:
        name = _t[1]
    else:
        template_ids[protocol] += 1
        name = protocol + str(template_ids[protocol])

    template = _t[-1]
    template["_protocol"] = protocol
    if len(_t) > 3 and _t[2] == "from":
        template["_template"] = _t[3]

    label = "<font point-size='16'><b>template {}</b></font>".format(name)

    if args.compress:
        template["_node"] = "template_" + name
        graph.add_node(template["_node"], label="<{}<br/>>".format(label), shape="box")
        if "_template" in template:
            # TODO: test this
            graph.add_edge(template["_node"], template["_template"]["_node"])
    else:
        subgraph = find_key(template, "_subgraph", default=graph)
        template["_subgraph"] = subgraph.add_subgraph(name="cluster_" + name, label="<{}>".format(label))
    templates[name] = template


# create instance nodes

instance_ids = defaultdict(lambda: 0)
instances = {}
for _p in config["protocol"]:
    protocol = _p[0]
    if len(_p) > 2:
        name = _p[1]
    else:
        instance_ids[protocol] += 1
        name = protocol + str(instance_ids[protocol])

    instance = _p[-1]
    instance["_protocol"] = protocol
    if len(_p) > 3 and _p[2] == "from":
        instance["_template"] = _p[3]
    instances[name] = instance

    if protocol != "pipe":
        if protocol == "static":
            label = "<br/>".join(" ".join(route) for route in find_key(instance, "route", default=set()))
        elif protocol == "device":
            label = ""
        elif protocol == "direct":
            label = "<br/>".join("<br/>".join(interfaces) for interfaces in find_key(instance, "interface", default=set()))
        elif protocol == "kernel":
            kernel_table = find_option(instance, "kernel table none;", use_default=False)
            if kernel_table:
                label = "kernel table " + kernel_table[1]
            else:
                label = ""
        elif protocol == "bgp":
            label = "neighbor " + " ".join(find_option(instance, "neighbor none;", use_default=False))
        elif protocol == "ospf":
            label = "<br/>".join(area + ": " + " ".join(interface for interface, interface_config in area_config["interface"])
                for area, area_config in find_key(instance, "area", default=set()))
        else:
            label = ""

        label = "<b>{} {}</b><br/>{}".format(protocol, name, label)

        if args.compress and "_template" in instance:
            node = graph.get_node(find_key(instance, "_node"))
            node.attr["label"] = "<{}<br/>{}>".format(node.attr["label"], label)
        else:
            instance["_node"] = "proto_" + name
            subgraph = find_key(instance, "_subgraph", default=graph)
            subgraph.add_node(instance["_node"], label="<{}>".format(label), color="blue", shape="box")


# create edges

for name, instance in instances.items():
    table = find_option(instance, "table master;", use_default=True)[0]

    import_mode = parse_filter(find_option(instance, "import all;", use_default=True))
    export_mode = parse_filter(find_option(instance, "export none;", use_default=True))

    if instance["_protocol"] == "pipe":
        peer_table = find_option(instance, "peer table master;", use_default=True)[1]

        if import_mode:
            graph.add_edge("table_" + peer_table, "table_" + table, **filter_edge(import_mode))
        if export_mode:
            graph.add_edge("table_" + table, "table_" + peer_table, **filter_edge(export_mode))
    else:
        if instance["_protocol"] == "device":
            # device protocol never exports or import routes
            export_mode = False
            import_mode = False

        if import_mode:
            graph.add_edge(find_key(instance, "_node"), "table_" + table, **filter_edge(import_mode))
        if export_mode:
            graph.add_edge("table_" + table, find_key(instance, "_node"), **filter_edge(export_mode))


print(graph.string())
