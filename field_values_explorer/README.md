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

## Common uses
### Understand a use case
To understand the use case of a pipeline & its associated UI, explore fields that define the content, such as:
- @source 
- @language
- @objecttype
- @contenttype
- @productname

This will tell you everything this pipeline returns. You can also compare it to the empty pipeline to see what is not returned by this pipeline.

### Create architecture diagrams
Follow the steps in “Understand a use case”, and set the output format to HTML. This generates diagrams that show the relationships between the fields and query pipelines.

### Decide whether a field should be a facet
Explore the values in one pipeline.
- Are there no values at all? If not, then this field should not be a facet.
- Are all the values very long or irrelevant? If so, then this field should not be a facet.
- Are there many values? If yes, ensure the facet has a facet search bar; or maybe make the field free-text-searchable rather than a facet. Eg @city or @author may have hundreds of values for some customers.

### Troubleshoot facet values
Explore the field’s values in the empty pipeline.
- Are there any invalid values? Examples could be empty strings, irrelevant text, or invalid dates. A mapping rule or IPE can remove these values.
- Do any values need formatting or normalization? Examples could be dates with multiple formats, or text that needs capitalization. An IPE can fix these values.
- Are there no values at all? This could be an indexing issue.
- Are there any expected values that are missing? This could be an indexing issue.

You can also explore the values in one pipeline.
- Does the field have more (or fewer) values than expected? That means this pipeline is returning the wrong content, and may have an issue with its filters. This is especially useful for content-defining fields like @source, @language or @productname.

### Compare values to past values
When you run the explorer, you can save the output (in JSON or HTML) so that you have a record of what this pipeline returns. At some later time (possibly months or years later), you can run it again, and compare the output with your saved record. This will tell you what has changed. An online diff tool like https://www.diffchecker.com/diff/ will make this comparison easier.

### Sample scenario: Create a facet for the author field
You are considering making a facet from the author field. You launch the field values explorer for @author, across all pipelines. You discover the following:
- The **empty** pipeline has over 100 values, so there is enough data for a facet, but that facet should have a facet search bar,
- The **empty** pipeline shows that most values follow a “LASTNAME, FIRSTNAME” format, but a few do not. You create a mapping rule to fix those few values and make them consistent.
- The **empty** pipeline has a few invalid values: either blank, or the text “SYSTEM”. You create a small IPE to replace those values with your company name.
- Your **internal** pipeline has no author values at all. You notice that the filter on that pipeline is wrong, so you fix the filters and re-run the tool. Now that pipeline returns a variety of authors, so you create an Author facet for your internal use case.
- In your **customer-facing** pipeline, the author is always either blank or “SYSTEM”. Even though you wrote an IPE in step 3 to fix those values, that means there will only be one author value in this use case, so you decide not to create an Author facet in your customer-facing use case.

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
