# Org Health Check

This repository contains the Org Health Check tool. It's a CLI to check various resources (Sources, IPEs etc) for errors or warnings.

### Prerequisites

- Clone the Product Intelligence Tools repository
- Python >= 3.10
  - To download latest Python version: https://www.python.org/downloads/
- Pip
  - To download pip: https://pip.pypa.io/en/stable/installation/
- Access to the Coveo Cloud Platform

## Getting Started

- Make sure you have pre-requisites installed
- Go the the org_health_check repository from the product-intelligence-tools main folder

```
    cd org_health_check
```

- Install Python requirements listed in requirements.txt

```
    pip install -r requirements.txt
```

- Launch org_health_check.py in a terminal

```
    py org_health_check.py
```

- The script will ask for a Bearer token; It is to authentify yourself to the calls made to the Platform. To get one, connect to platform.cloud.coveo.com with SSO and open you network calls through developer tools on Chrome (or any other familiar browser). For status calls or any other made to the Platform backend, you have a token beginning by "x" in the Authorization parameter of the request headers. This is what you need.
- Follow the instructions displayed in the terminal and enjoy!

## Common uses
### Basic
The most basic use is self-explanatory: the tool provides warnings about various resources. The tool is aggressive and reports any warning, no matter how small. The tool outputs its warnings in CSV file(s).

### Compare warnings to past warnings
When you run the tool, you can save the output so that you have a record of these warnings. At some later time (possibly months or years later), you can run it again, and compare the output with your saved record. This will tell you what warnings are new. An online diff tool like https://www.diffchecker.com/diff/ will make this comparison easier.

This comparison is also useful if you have identified some warnings as not important. Save the CSV file of those warnings, and then compare any new output with that saved file. This will tell you which warnings are different from those unimportant warnings. Again, an online diff tool like https://www.diffchecker.com/diff/ will make this easier.

### Recommendations

- Bash shell to launch the script

## Authors

**Thomas "Thom" Camire** - Software Developer - _email: tcamire@coveo.com_ - _slack: tcamire_

**Ricky "Ricky" Donato** - Program Architect - _email: rdonato@coveo.com_ - _slack: rdonato_
