#!/usr/bin/env python3

import argparse
import json
import uuid
import yaml


def get_args():
    parser = argparse.ArgumentParser(
        description="Tool to convert from grafana json to configmap"
    )

    parser.add_argument("-i", "--input", required=True, help="Grafana json file")
    parser.add_argument("-o", "--output", default="", help="Output yaml file")
    parser.add_argument("-n", "--name", default="", help="Configmap name")
    parser.add_argument("-f", "--folder", default="", help="Dashboard folder")
    parser.add_argument(
        "-N", "--namespace", default="monitoring", help="Namespace for configmap"
    )

    return parser.parse_args()


def _fix_name(name):
    valid_chrs_start = "abcdefghijklmnopqrstuvwxyz"
    valid_chrs_all = valid_chrs_start + "0123456789-"
    repl_chr = "-"

    name = name.lower()
    if name[0] not in valid_chrs_start:
        raise ValueError("Name starts with invalid character")

    result = ""
    for c in name:
        if c not in valid_chrs_all:
            c = repl_chr
        result += c

    while "--" in result:
        result = result.replace("--", "-")

    while result.endswith("-"):
        result = result[:-1]

    return result


def get_name(data):
    name = "none"
    if "title" in data:
        name = _fix_name(data["title"])

    elif "spec" in data:
        if "title" in data["spec"]:
            name = _fix_name(data["spec"]["title"])

    else:
        name = str(uuid.uuid4()).lower()

    return f"grafana-dashboard-{name}"


def multiline_representer(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def main():
    yaml.add_representer(str, multiline_representer)
    yaml.representer.SafeRepresenter.add_representer(str, multiline_representer)

    args = get_args()

    with open(args.input) as fp:
        data = json.load(fp)

    del_flds = [
        "annotations",
        "labels",
        "uid",
        "resourceVersion",
        "generation",
        "creationTimestamp",
    ]
    if "metadata" in data:
        for fld in del_flds:
            del data["metadata"][fld]

    name = args.name

    if not name:
        name = get_name(data)

    cm_file = f"{name}.json"

    result = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": name,
            "namespace": args.namespace,
            "labels": {
                "grafana_dashboard": "1",
            },
            "annotations": {},
        },
        "data": {
            cm_file: json.dumps(data, indent=2),
        },
    }

    if args.folder:
        result["metadata"]["annotations"]["grafana_folder"] = args.folder

    out_fn = args.output
    if not out_fn:
        out_fn = result["metadata"]["name"] + ".yaml"

    with open(out_fn, "w") as fp:
        yaml.safe_dump(result, fp, sort_keys=False)


if __name__ == "__main__":
    main()
