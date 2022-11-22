# Field Values Explorer

This repository contains the Field Values Explorer tool. It's a CLI to parse through field values of an organization for specific fields and pipelines. It can print or save in JSON format the information about pipelines, fields or field values.

### Prerequisites

- Clone the Product Intelligence Tools repository
- Python >= 3.0
  - To download latest Python version: https://www.python.org/downloads/
- Pip
  - To download pip: https://pip.pypa.io/en/stable/installation/
- Access to the Coveo Cloud Platform

## Getting Started

- Make sure you have prequisites installed
- Go the the field_values_explorer repository from the product-intelligence-tools main folder

```
    cd field_values_explorer
```

- Install Python requirements listed in requirements.txt

```
    pip install -r requirements.txt
```

- Launch field_values_explorer.py in a terminal

```
    py field_values_explorer.py
```

- The script will ask for a Bearer token; It is to authentify yourself to the calls made to the Platform. To get one, connect to platform.cloud.coveo.com with SSO and open you network calls through developer tools on Chrome (or any other familiar browser). For status calls or any other made to the Platform backend, you have a token beginning by "x" in the Authorization parameter of the request headers. This is what you need.
- Follow the instructions displayed in the terminal and enjoy!

### Notes

- If you select the save to JSON option during your operations, they'll be saved in the directory the file is executed in. If you want to save them or avoid overrides by multiple operations in a row, you should move the saved files elsewhere.
- Depending on what is saved, the files follow a certain syntax:
  - field values for all pipelines separately: fieldValues-{organizationID}-{field}-all.json
  - field values for a specific pipeline: fieldValues-{organizationID}-{field}-{pipeline}.json
  - field values for an empty pipeline (like all pipelines, but together): fieldValues-{organizationID}-{field}-empty.json

### Recommendations

- Bash shell to launch the script

## Authors

**Thomas "Thom" Camire** - Software Developer - _email: tcamire@coveo.com_ - _slack: tcamire_

**Ricky "Ricky" Donato** - Program Architect - _email: rdonato@coveo.com_ - _slack: rdonato_
