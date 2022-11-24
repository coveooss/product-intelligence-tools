'''
Main file of the field values explorer. It's a CLI to parse through field values of an organization for specific fields and pipelines. It can print or save in JSON format the information about pipelines, fields or field values.
Author: Thomas Camiré (tcamire@coveo.com)
'''

# IMPORTS

# External
import inquirer
from inquirer import errors
import requests
import json
import copy

# Internal
import globalTools
import html_templater


# PROMPTS

'''
Prompts the user to give a field name. Validates that the field name is valid by comparing it to a list of fields for an organization ID specified earlier in the flow.

Parameters:
    fields(str): The list of fields for an organization ID specified earlier in the flow.

Returns:
    field(str): The field name that was asked for.
'''


def getField(fields):
    question = inquirer.Text('field',
                             message="Enter a Facet or Multivalue field (with the @)",
                             validate=lambda _, field: validateField(field, fields))
    field = inquirer.prompt([question]).get("field")
    return field


'''
Prompts the user to enable viewAllContent parameter or not.

Returns:
    true(str): If the user decided to enable viewAllContent.
    false(str): If the user refused to enable viewAllContent.
'''


def enableViewAllContent():
    question = inquirer.Confirm('viewAllContent',
                                message="Enable viewAllContent? If yes, your bearer token must have Search - View all content privilege",
                                default=False)
    if(inquirer.prompt([question]).get("viewAllContent")):
        return 'true'
    return 'false'


'''
Prompts the user to give a pipeline name. Validates that the pipeline name is valid by comparing it to a list of pipelines for an organization ID specified earlier in the flow.

Parameters:
    pipelines(str): The list of pipelines for an organization ID specified earlier in the flow.

Returns:
    pipeline(str): The pipeline name that was asked for.
'''


def getPipeline(pipelines):
    question = inquirer.Text('pipeline',
                             message="Enter a query pipeline",
                             validate=lambda _, pipeline: validatePipeline(pipeline, pipelines))
    pipeline = inquirer.prompt([question]).get("pipeline")
    pipeline = list(filter(lambda x: x["name"] == pipeline, pipelines))[0]
    return pipeline


'''
Prints to console or saves to JSON or saves to HTML a passed dictionary of field values. Can also skip.

Parameters:
    fileTitle(str): The name of the JSON file if we save to JSON.
    fieldValues(dict): The dictionary containing the field values we want to print or save.
'''


def printOrSaveToJSONOrSaveToHTMLOrSkip(isSinglePipeline, organization, field, maxFieldValues, isViewAllContent, fieldValues):
    question = inquirer.List('printOrSaveToJSONOrSaveToHTMLOrSkip',
                             message="Success! What do you want to do with the results?",
                             choices=["Save to JSON",
                                      "Save to HTML", "Print", "Skip"],
                             default="Save to JSON")
    decision = inquirer.prompt([question]).get(
        "printOrSaveToJSONOrSaveToHTMLOrSkip")
    if(decision == "Save to JSON"):
        with open('fieldValues-{}-{}-{}-{}.json'.format(
                organization,
                field,
                list(fieldValues.keys())[0] if(isSinglePipeline) else "all",
                globalTools.getTimeFilenameSlug()),
                'w') as f:
            json.dump(fieldValues, f, indent=4)
    elif(decision == "Save to HTML"):
        html_templater.saveToHTML(organization,
            field, maxFieldValues, isViewAllContent, fieldValues)
    elif(decision == "Print"):
        print(json.dumps(fieldValues, indent=4, sort_keys=True))


'''
After one full loop of the process is done, ask if we want to go back to certain steps with saved parameters.

Parameters:
    platformURL(str): The right Coveo Cloud URL depending on the platform region (US, EU, AU).
    field(str): A field name.
    organization(str): An organization ID.
    token(str): A Coveo Cloud Platform bearer token.
'''


def selectNextStep(platformURL, field, organization, token):
    question = inquirer.List('nextStep',
                             message="What do you want to do next?",
                             choices=["Go back to organization selection",
                                      "Go back to field selection", "Go back to pipeline selection", "Exit"],
                             default="Exit")
    decision = inquirer.prompt([question]).get("nextStep")
    if(decision == "Go back to organization selection"):
        platformURL, organization = globalTools.goToOrganizationSelection(token)
        field = fieldSelection(platformURL, organization, token)
        pipelineSelection(platformURL, field, organization, token)
    elif(decision == "Go back to field selection"):
        print("Going back to field selection with organization {}".format(organization))
        goToFieldSelection(platformURL, organization, token)
    elif(decision == "Go back to pipeline selection"):
        print("Going back to pipeline selection with organization {} and field {}".format(
            organization, field))
        goToPipelineSelection(platformURL, field, organization, token)
    elif(decision == "Exit"):
        exit()


'''
Prompts the user if he/she wants to get field values for a single pipeline or all pipelines.

Returns:
    decision: Whether the user decided to get field values for a single pipeline or all pipelines.
'''


def fieldValuesForSingleOrAllPipelines():
    question = inquirer.List('fieldValuesForSingleOrAllPipelines',
                             message="You want field values for a single pipeline or all pipelines?",
                             choices=["All pipelines", "Single pipeline"],
                             default="All pipelines")
    decision = inquirer.prompt([question]).get(
        "fieldValuesForSingleOrAllPipelines")
    return decision


'''
Prompts the user to give the maximum number of field values to retrieve. Validates that it is an integer greater than 0 and lower than 10000.

Returns:
    maxValues(int): The max number of field values that was asked for.
'''


def getMaxValues():
    question = inquirer.Text('maxValues',
                             message="Enter the maximum number of field values you want to get per pipeline",
                             validate=lambda _, maxValues: validateMaxValues(
                                 maxValues))
    maxValues = inquirer.prompt([question]).get("maxValues")
    return maxValues


# VALIDATORS

'''
Validates that a field name is valid by comparing it to a list of fields the user has access to for a specific organization ID.

Parameters:
    field(str): A field name.
    fields(str): A list of fields the user has access to.

Returns:
    True(boolean): If the field name is valid.
'''


def validateField(field, fields):
    matchingFields = list(filter(lambda x: x == field, fields))
    if(len(matchingFields) > 0):
        return True
    else:
        raise errors.ValidationError("", "This field does not exist or is not Facet or Multivalue Facet")


'''
Validates that a pipeline name is valid by comparing it to a list of pipelines the user has access to for a specific organization ID.

Parameters:
    pipeline(str): A pipeline name.
    pipelines(str): A list of pipelines the user has access to.

Returns:
    True(boolean): If the pipeline name is valid.
'''


def validatePipeline(pipeline, pipelines):
    matchingPipelines = list(
        filter(lambda x: x["name"] == pipeline, pipelines))
    if(len(matchingPipelines) > 0):
        return True
    else:
        raise errors.ValidationError("", "This pipeline does not exist")


'''
Validates that the field values maxValues input it is an integer greater than 0 and lower than 10000.

Parameters:
    maxValues(str): The input for the maxValues parameter in the field values call.

Returns:
    True(boolean): If the pipeline name is valid.
'''


def validateMaxValues(maxValues):
    try:
        maxValues = int(maxValues)
    except:
        raise errors.ValidationError("", "Your input is not a number")
    if(maxValues < 1 or maxValues > 10000):
        raise errors.ValidationError(
            "", "Max values should be between 1 and 10000")
    return True


# API CALLS

'''
Gets fields tied to an organization ID from the Coveo Cloud Platform.

Parameters:
    platformURL(str): The right Coveo Cloud URL depending on the platform region (US, EU, AU).
    organization(str): An organization ID.
    token(str): A Coveo Cloud Platform bearer token.

Returns:
    fields(list): The list of fields for that organization ID.
    False(bool): If the fields fetch was unsucessful.
'''


def getOrganizationFields(platformURL, organization, token):
    response = requests.get("{}rest/search/v2/fields?organizationId={}".format(
        platformURL, organization), headers={"Authorization": "Bearer {}".format(token)})
    if(response.status_code == 200):
        rawFields = json.loads(response.text).get("fields", False)
        if(rawFields):
            # filter() only includes Facet or Multivalue Facet fields
            fields = list(map(lambda x: x["name"], filter(lambda x: x['groupByField'] or x['splitGroupByField'], rawFields)))
            return fields
    return False


'''
Gets pipelines tied to an organization ID from the Coveo Cloud Platform.

Parameters:
    platformURL(str): The right Coveo Cloud URL depending on the platform region (US, EU, AU).
    organization(str): An organization ID.
    token(str): A Coveo Cloud Platform bearer token.

Returns:
    pipelines(list): The list of pipelines for that organization ID.
    False(bool): If the pipelines fetch was unsucessful.
'''


def getOrganizationPipelines(platformURL, organization, token):
    response = requests.get("{}rest/search/v1/admin/pipelines?organizationId={}".format(
        platformURL, organization), headers={"Authorization": "Bearer {}".format(token)})
    if(response.status_code == 200):
        rawPipelines = json.loads(response.text)
        pipelines = list(
            map(lambda x: {"name": x["name"], "id": x["id"]}, rawPipelines))
        return pipelines
    return False


'''
Gets field values and their occurences across items for a specific field, pipeline(s) and organization ID.

Parameters:
    platformURL(str): The right Coveo Cloud URL depending on the platform region (US, EU, AU).
    field(str): A field name.
    organization(str): An organization ID.
    pipelines(list): A list of pipeline names.
    maxFieldValues(int): The max number of field values for a pieline.
    isViewAllContent(str): true or false in string, if the user decided to enabled the viewAllContent parameter or not.
    token(str): A Coveo Cloud Platform bearer token.

Returns:
    fieldValues(dict): Field values for a specific field, pipeline and organization ID.
'''


def getFieldValues(platformURL, field, organization, pipelines, maxFieldValues, isViewAllContent, token):
    print("Getting field values (adding empty pipeline as a reference for all values)...")
    fieldValues = {}
    pipelines.append({"name": "", "id": ""})
    for pipeline in pipelines:
        fieldValues[pipeline["name"]] = {}

        # R&D recommends the API /search/v2/values to get all field values, but it does not always respect the pipeline.
        # Instead, use search/v2/facet
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Search-V2/operation/facetSearch
        response = requests.post("{}rest/search/v2/facet?organizationId={}&viewAllContent={}".format(
            platformURL, organization, isViewAllContent),
            headers={"Authorization": "Bearer " + token,
                     "Content-Type": "application/json"},
            data=json.dumps({"field": field.replace('@', ''), # This API call cannot have the @ in the field name
                             "numberOfValues": int(maxFieldValues), # This API call needs the value as int not str
                             "searchContext": {"pipeline": pipeline["id"]}}))
        body = json.loads(response.text)
        if(response.status_code == 200):
            for value in body["values"]:
                fieldValues[pipeline["name"]][value["displayValue"]
                                              ] = value["count"]
        else:
            print(
                "There was a problem with the request. Here's the message: " + body["message"])
            return False
    for pipelineName in fieldValues.keys():
        if(fieldValues[pipelineName] != {}):
            return fieldValues
    return False


# MAIN SECTIONS

'''
Runs the field selection section, where you get a validated field name for a specific organization ID.

Parameters:
    platformURL(str): The right Coveo Cloud URL depending on the platform region (US, EU, AU).
    organization(str): An organization ID.
    token(str): A Coveo Cloud Platform bearer token.

Returns:
    field(str): A field name.
'''


def fieldSelection(platformURL, organization, token):
    fields = getOrganizationFields(platformURL, organization, token)
    if(not fields):
        raise errors.ValidationError(
            "", "You do not have access to this organization's fields or there's none")    
    globalTools.printOrSkip("Found {} fields in this organization that are Facet or Multivalue Facet.".format(
        len(fields)), fields)
    field = getField(fields)
    return field


'''
Runs the pipeline selection section, where you get a validated pipeline name for a specific organization ID and ultimately get the field values for a specific field, organization and pipeline.

Parameters:
    platformURL(str): The right Coveo Cloud URL depending on the platform region (US, EU, AU).
    field(str): A field name.
    organization(str): An organization ID.
    token(str): A Coveo Cloud Platform bearer token.
'''


def pipelineSelection(platformURL, field, organization, token):
    pipelines = getOrganizationPipelines(platformURL, organization, token)
    if(not pipelines):
        raise errors.ValidationError(
            "", "You do not have access to this organization's pipelines")    
    globalTools.printOrSkip("Found {} pipelines in this organization.".format(
        len(pipelines)), list(map(lambda x: x["name"], pipelines)))
    isSinglePipeline = fieldValuesForSingleOrAllPipelines() == "Single pipeline"
    if(isSinglePipeline):
        pipelines = [getPipeline(pipelines)]
    maxFieldValues = getMaxValues()
    isViewAllContent = enableViewAllContent()
    fieldValues = getFieldValues(
        platformURL, field, organization, copy.deepcopy(pipelines), maxFieldValues, isViewAllContent, token)
    if not fieldValues or any([not valList for valList in fieldValues.values()]):
        msg = '''
WARNING: At least one pipeline returned no values. If you believe this is an error, please open your Coveo admin console and check the following:
  * The query pipeline's filters
  * The query pipeline is not overriding the query parameters Q, AQ or CQ
        '''
        print(msg)
        question = inquirer.List('Ok, I understand',
            message='Ok, I understand',
            choices=["Continue"],
            default="Continue")
        decision = inquirer.prompt([question]).get("Ok, I understand")
        
    printOrSaveToJSONOrSaveToHTMLOrSkip(
        isSinglePipeline, organization, field, maxFieldValues, isViewAllContent, fieldValues)
    selectNextStep(platformURL, field, organization, token)


# STEPS

'''
Restarts the field values explorer, but starting at the field section.

Parameters:
    platformURL(str): The right Coveo Cloud URL depending on the platform region (US, EU, AU).
    organization(str): An organization ID.
    token(str): A Coveo Cloud Platform bearer token.
'''


def goToFieldSelection(platformURL, organization, token):
    field = fieldSelection(platformURL, organization, token)
    pipelineSelection(platformURL, field, organization, token)


'''
Restarts the field values explorer, but starting at the pipeline section.

Parameters:
    platformURL(str): The right Coveo Cloud URL depending on the platform region (US, EU, AU).
    field(str): A field name.
    organization(str): An organization ID.
    token(str): A Coveo Cloud Platform bearer token.
'''


def goToPipelineSelection(platformURL, field, organization, token):
    pipelineSelection(platformURL, field, organization, token)


'''
Starting point of the tool.
'''


def start():
    token, platformURL, organization = globalTools.start()
    goToFieldSelection(platformURL, organization, token)

# Start the process by default when running py field_values_explorer.py

start()
